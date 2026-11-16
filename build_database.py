"""Build the pinned CMS Medicaid/CHIP enrollment release without publication.

The download is capped at 32 MiB of decoded CSV; the build uses one DuckDB
thread, 256 MiB memory and no disk spill. Existing artifacts are never replaced.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb
import requests
from datapond_build import ensure_metadata, build_columns_table, export_dictionary

ROOT = Path(__file__).resolve().parent
CAP = 32 * 1024**2
DATA_TABLES = ['enrollment', 'field_definitions']
STATES = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
METHOD = 'https://www.medicaid.gov/medicaid/national-medicaid-chip-program-information/medicaid-chip-enrollment-data/methodology-about-medicaid-chip-enrollment-report'


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify(path, expected):
    if Path(path).stat().st_size != expected['bytes'] or sha256(path) != expected['sha256']:
        raise ValueError(f'Source identity mismatch: {Path(path).name}')


def download(lock, destination):
    """Fetch only the locked HTTPS URL; fail closed on changed or oversized data."""
    destination = Path(destination)
    if destination.exists():
        verify(destination, lock)
        return
    if not lock['url'].startswith('https://download.medicaid.gov/data/'):
        raise ValueError('Unexpected source host')
    if lock['bytes'] > CAP:
        raise ValueError('Locked source exceeds download cap')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < 256 * 1024**2:
        raise RuntimeError('Less than 256 MiB disk reserve')
    partial = destination.with_suffix(destination.suffix + '.partial')
    start, total = time.monotonic(), 0
    with requests.get(lock['url'], stream=True, timeout=(15, 30),
                      headers={'User-Agent': 'datapond-research/1.0', 'Accept-Encoding': 'identity'}) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Expected complete HTTP response')
        if int(response.headers.get('Content-Length', 0)) > CAP:
            raise ValueError('HTTP response exceeds cap')
        with partial.open('xb') as f:
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > min(CAP, lock['bytes']) or time.monotonic() - start > 90:
                    raise RuntimeError('Download byte/time cap exceeded')
                f.write(chunk)
    verify(partial, lock)
    partial.rename(destination)


def q(value):
    return '"' + value.replace('"', '""') + '"'


def sql_type(field):
    if field['name'] == 'reporting_period':
        return 'VARCHAR'
    return {'string': 'VARCHAR', 'integer': 'BIGINT', 'number': 'DECIMAL(12,6)'}[field['type']]


def parse_rows(path, fields):
    """Strict conversion: empty cells are NULL; numeric zeros and footnotes survive."""
    if Path(path).stat().st_size > CAP:
        raise ValueError('CSV exceeds cap')
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, strict=True)
        headers = next(reader)
        if [h.strip().casefold() for h in headers] != [f['title'].strip().casefold() for f in fields]:
            raise ValueError('CSV header differs from pinned dictionary')
        rows = []
        keys = set()
        for row_number, raw in enumerate(reader, 1):
            if row_number > 100000 or len(raw) != len(fields):
                raise ValueError(f'Invalid CSV row shape or row cap: {row_number}')
            row = []
            for field, value in zip(fields, raw):
                typ = sql_type(field)
                if value == '':
                    row.append(None)
                elif typ == 'BIGINT':
                    if not re.fullmatch(r'[0-9]+', value) or int(value) > 2**63 - 1:
                        raise ValueError(f'Invalid integer at row {row_number}: {field["name"]}')
                    row.append(int(value))
                elif typ.startswith('DECIMAL'):
                    if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,6})?', value):
                        raise ValueError(f'Invalid rate at row {row_number}')
                    rate = Decimal(value)
                    if not 0 <= rate <= 1:
                        raise ValueError(f'Rate outside [0,1] at row {row_number}')
                    row.append(rate)
                else:
                    row.append(value)
            values = dict(zip([f['name'] for f in fields], row))
            state, period, report = (values[k] for k in ['state_abbreviation', 'reporting_period', 'preliminary_updated'])
            if state not in STATES or not values['state_name']:
                raise ValueError(f'Invalid state at row {row_number}')
            if not period or not re.fullmatch(r'[0-9]{6}', period):
                raise ValueError(f'Invalid reporting period at row {row_number}')
            month = date(int(period[:4]), int(period[4:]), 1)
            baseline = period == '201309'
            if report not in ('P', 'U') or values['final_report'] not in ('Y', 'N') or values['state_expanded_medicaid'] not in ('Y', 'N'):
                raise ValueError(f'Unknown report flag at row {row_number}')
            key = state, period, report
            if key in keys:
                raise ValueError(f'Duplicate state/period/report key: {key}')
            keys.add(key)
            rows.append(tuple(row + [row_number, None if baseline else month, baseline]))
    if not rows:
        raise ValueError('Empty source')
    return headers, rows


def validate(con, *, full_release=False):
    checks = []
    def check(name, sql, expected):
        actual = con.execute(sql).fetchone()[0]
        checks.append({'name': name, 'actual': actual, 'expected': expected, 'passed': actual == expected})
    check('unique source rows', 'SELECT count(*)-count(DISTINCT source_row_number) FROM enrollment', 0)
    check('unique grain', 'SELECT count(*)-count(DISTINCT (state_abbreviation,reporting_period,preliminary_updated)) FROM enrollment', 0)
    check('baseline excluded from monthly views', 'SELECT (SELECT count(*) FROM monthly_updated WHERE is_baseline)+(SELECT count(*) FROM monthly_preliminary WHERE is_baseline)', 0)
    check('baseline has no monthly date', 'SELECT count(*) FROM enrollment WHERE is_baseline AND reporting_month IS NOT NULL', 0)
    check('monthly rows have a date', 'SELECT count(*) FROM enrollment WHERE NOT is_baseline AND reporting_month IS NULL', 0)
    check('enrollment component reconciliation', 'SELECT count(*) FROM enrollment WHERE total_medicaid_and_chip_enrollment <> total_medicaid_enrollment + total_chip_enrollment', 0)
    check('final flag consistent with report type', "SELECT count(*) FROM enrollment WHERE final_report <> CASE preliminary_updated WHEN 'U' THEN 'Y' ELSE 'N' END", 0)
    check('nonnegative enrollment', 'SELECT count(*) FROM enrollment WHERE total_medicaid_and_chip_enrollment < 0', 0)
    if full_release:
        check('source records', 'SELECT count(*) FROM enrollment', 11220)
        check('dictionary fields', 'SELECT count(*) FROM field_definitions', 44)
        check('national state coverage', 'SELECT count(DISTINCT state_abbreviation) FROM enrollment', 51)
        check('baseline rows', 'SELECT count(*) FROM baseline_enrollment', 51)
        check('updated monthly rows', 'SELECT count(*) FROM monthly_updated', 5559)
        check('preliminary monthly rows', 'SELECT count(*) FROM monthly_preliminary', 5610)
        check('latest preliminary period', 'SELECT max(reporting_period) FROM monthly_preliminary', '202607')
        check('latest updated period', 'SELECT max(reporting_period) FROM monthly_updated', '202606')
        check('July enrollment matches CMS published total', "SELECT sum(total_medicaid_and_chip_enrollment) FROM monthly_preliminary WHERE reporting_period='202607'", 72946510)
        check('July Medicaid matches CMS published total', "SELECT sum(total_medicaid_enrollment) FROM monthly_preliminary WHERE reporting_period='202607'", 65742057)
        check('July CHIP matches CMS published total', "SELECT sum(total_chip_enrollment) FROM monthly_preliminary WHERE reporting_period='202607'", 7204453)
        check('two missing baseline counts retained', 'SELECT count(*) FROM baseline_enrollment WHERE total_medicaid_and_chip_enrollment IS NULL', 2)
        check('complete monthly state/report grid', 'SELECT count(*) FROM (SELECT reporting_period,preliminary_updated,count(*) n FROM enrollment GROUP BY ALL HAVING n<>51)', 0)
    if not all(c['passed'] for c in checks):
        raise ValueError('Validation failed: ' + json.dumps([c for c in checks if not c['passed']]))
    return checks


def build(source, out, fields, lock, *, full_release=True):
    verify(source, lock)
    headers, rows = parse_rows(source, fields)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(out).free < 256 * 1024**2:
        raise RuntimeError('Less than 256 MiB disk reserve')
    partial = out / 'medicaid-enrollment.duckdb.partial'
    con = duckdb.connect(str(partial), config={'threads': '1', 'memory_limit': '256MiB', 'max_temp_directory_size': '0B'})
    try:
        definition = ','.join(q(f['name']) + ' ' + sql_type(f) for f in fields)
        con.execute(f'CREATE TABLE enrollment ({definition},source_row_number BIGINT UNIQUE NOT NULL,reporting_month DATE,is_baseline BOOLEAN NOT NULL,PRIMARY KEY(state_abbreviation,reporting_period,preliminary_updated))')
        # One bounded bulk insert avoids thousands of parameterized statements.
        # Python validation above still rejects malformed values and duplicate
        # keys before DuckDB sees the CSV; read_csv is deliberately serial.
        expressions = ['CAST('+q(h)+' AS '+sql_type(f)+')' for f,h in zip(fields,headers)]
        period = q(headers[[f['name'] for f in fields].index('reporting_period')])
        expressions += ['row_number() OVER ()',
                        f"CASE WHEN {period}='201309' THEN NULL ELSE strptime({period},'%Y%m')::DATE END",
                        f"{period}='201309'"]
        con.execute('INSERT INTO enrollment SELECT '+','.join(expressions)+
                    " FROM read_csv(?, header=true, all_varchar=true, parallel=false, strict_mode=true, nullstr='')", [str(source)])
        con.execute('CREATE TABLE field_definitions (ordinal INTEGER PRIMARY KEY, column_name VARCHAR UNIQUE, source_header VARCHAR, source_type VARCHAR, duckdb_type VARCHAR, description VARCHAR)')
        con.executemany('INSERT INTO field_definitions VALUES (?,?,?,?,?,?)', [(i+1, f['name'], h, f['type'], sql_type(f), f['description']) for i,(f,h) in enumerate(zip(fields,headers))])
        con.execute("CREATE VIEW monthly_updated AS SELECT * FROM enrollment WHERE NOT is_baseline AND preliminary_updated='U'")
        con.execute("CREATE VIEW monthly_preliminary AS SELECT * FROM enrollment WHERE NOT is_baseline AND preliminary_updated='P'")
        con.execute('CREATE VIEW baseline_enrollment AS SELECT * FROM enrollment WHERE is_baseline')
        checks = validate(con, full_release=full_release)
        descriptions = {
            'enrollment': 'State/reporting-period/report-type records. 201309 is a Jul-Sep 2013 baseline average; preliminary and updated observations must not be pooled.',
            'field_definitions': 'Pinned CMS definitions and exact source headers for the 44 source fields; descriptive rows, not enrollment observations.',
        }
        ensure_metadata(con, tables=DATA_TABLES, descriptions=descriptions, source_url=lock['url'], license='Public domain')
        for name in ['source_file','source_sha256','source_version','source_dataset_id']:
            con.execute(f'ALTER TABLE _metadata ADD COLUMN {name} VARCHAR')
        con.execute('UPDATE _metadata SET source_file=?,source_sha256=?,source_version=?,source_dataset_id=?', [lock['file'],lock['sha256'],lock['source_version'],lock['dataset_id']])
        # Dictionary provenance differs from the enrollment source.
        dictionary_lock = lock.get('source-dictionary.json', {})
        con.execute("UPDATE _metadata SET source_file='source-dictionary.json',source_sha256=?,source_url=? WHERE table_name='field_definitions'", [dictionary_lock.get('sha256'), 'https://data.medicaid.gov/api/1/metastore/schemas/data-dictionary/items/7d80cfd8-3266-4c55-8436-948b7c55b9dd'])
        build_columns_table(con, tables=DATA_TABLES, join_hints={'state_abbreviation':'US postal abbreviation; combine with period and report type for source grain', 'reporting_period':'YYYYMM source code; 201309 means Jul-Sep 2013 baseline average', 'reporting_month':'Month start for monthly rows only; NULL for baseline'}, quiet=True)
        export_dictionary(con, out/'DICTIONARY.md', intro=['Source: CMS Medicaid/CHIP Performance Indicator dataset.', 'Use monthly_updated or monthly_preliminary consistently; baseline_enrollment contains July-September 2013 averages.', f'Methodology: {METHOD}'], style='registry')
        # _columns percentages are intentionally rounded for display. Exact
        # null counts must come from the data, never reconstructed percentages.
        names = [f['name'] for f in fields] + ['source_row_number','reporting_month','is_baseline']
        exact = con.execute('SELECT '+','.join('count(*) FILTER (WHERE '+q(n)+' IS NULL)' for n in names)+' FROM enrollment').fetchone()
        nulls = dict(zip(names,exact))
        footprint = con.execute("SELECT count(*),min(reporting_month),max(reporting_month) FROM enrollment").fetchone()
        con.execute('CHECKPOINT')
    finally:
        con.close()
    final = out/'medicaid-enrollment.duckdb'
    partial.rename(final)
    manifest = {'built_at_utc':datetime.now(timezone.utc).isoformat(), 'dataset_id':'medicaid-enrollment','status':'local candidate; not published','source':lock,'duckdb_version':duckdb.__version__, 'resources':{'threads':1,'memory_limit':'256MiB','max_temp_directory_size':'0B'}, 'artifact':{'file':final.name,'bytes':final.stat().st_size,'sha256':sha256(final)}, 'data_tables':{'enrollment':len(rows),'field_definitions':len(fields)}, 'monthly_range':[str(footprint[1]),str(footprint[2])], 'baseline':'July-September 2013 average, source code 201309', 'checks':checks, 'null_counts':nulls}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'artifact':manifest['artifact'],'tables':manifest['data_tables'],'checks_passed':len(checks)}))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT/'data')
    parser.add_argument('--out',type=Path,default=ROOT/'artifacts')
    parser.add_argument('--download',action='store_true',help='Fetch only the pinned source when absent')
    args = parser.parse_args()
    lock = json.loads((ROOT/'source-lock.json').read_text())
    for name in ['source-metadata.json','source-dictionary.json']:
        verify(ROOT/name, lock[name])
    source = args.source_dir/lock['file']
    if args.download:
        download(lock,source)
    fields = json.loads((ROOT/'source-dictionary.json').read_text())['data']['fields']
    build(source,args.out,fields,lock)


if __name__ == '__main__':
    main()
