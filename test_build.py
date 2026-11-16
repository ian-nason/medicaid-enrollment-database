import csv
import json
from pathlib import Path

import duckdb
import pytest

from build_database import ROOT, build, download, parse_rows, sha256

FIELDS = json.loads((ROOT/'source-dictionary.json').read_text())['data']['fields']


def fixture(tmp_path, records):
    path = tmp_path/'source.csv'
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([x['title'].strip() for x in FIELDS])
        for record in records:
            values = dict(state_abbreviation='AL', state_name='Alabama', reporting_period='202607',
                          state_expanded_medicaid='N', preliminary_updated='P', final_report='N',
                          total_medicaid_and_chip_enrollment='100', total_medicaid_enrollment='90', total_chip_enrollment='10')
            values.update(record)
            writer.writerow([values.get(x['name'],'') for x in FIELDS])
    return path


def lock_for(path):
    lock=json.loads((ROOT/'source-lock.json').read_text())
    lock.update(bytes=path.stat().st_size,sha256=sha256(path),file=path.name)
    return lock


def test_baseline_versions_nulls_zero_and_footnotes_end_to_end(tmp_path):
    source=fixture(tmp_path,[
        {'reporting_period':'201309','preliminary_updated':'U','final_report':'Y','total_medicaid_and_chip_enrollment':'','total_medicaid_enrollment':'','total_chip_enrollment':''},
        {'reporting_period':'202606','total_medicaid_and_chip_enrollment':'90','total_medicaid_enrollment':'80'},
        {'reporting_period':'202606','preliminary_updated':'U','final_report':'Y','total_medicaid_and_chip_enrollment':'110','total_medicaid_enrollment':'100'},
        {'medicaid_and_chip_child_enrollment':'0','medicaid_and_chip_child_enrollment_footnotes':'Unable to provide data due to system limitations','average_call_center_abandonment_rate':'0.005'},
    ])
    out=tmp_path/'build'
    manifest=build(source,out,FIELDS,lock_for(source),full_release=False)
    con=duckdb.connect(str(out/'medicaid-enrollment.duckdb'),read_only=True,config={'threads':1,'memory_limit':'128MiB'})
    assert con.execute('SELECT reporting_month,total_medicaid_and_chip_enrollment FROM baseline_enrollment').fetchone()==(None,None)
    assert con.execute('SELECT total_medicaid_and_chip_enrollment FROM monthly_updated').fetchone()[0]==110
    assert con.execute('SELECT count(*) FROM monthly_preliminary').fetchone()[0]==2
    row=con.execute("SELECT medicaid_and_chip_child_enrollment,medicaid_and_chip_child_enrollment_footnotes,average_call_center_abandonment_rate FROM enrollment WHERE reporting_period='202607'").fetchone()
    assert row[0]==0 and 'system limitations' in row[1] and str(row[2])=='0.005000'
    assert con.execute('SELECT sum(row_count) FROM _metadata').fetchone()[0]==48
    assert con.execute("SELECT count(*) FROM _columns WHERE table_name='enrollment'").fetchone()[0]==47
    assert manifest['artifact']['sha256']==sha256(out/'medicaid-enrollment.duckdb')
    assert manifest['null_counts']['reporting_month']==1
    assert manifest['null_counts']['total_medicaid_and_chip_enrollment']==1
    con.close()


@pytest.mark.parametrize('change',[
    {'total_medicaid_enrollment':'1.2'},
    {'total_chip_enrollment':'-1'},
    {'average_call_center_abandonment_rate':'12'},
    {'average_call_center_abandonment_rate':'0.1234567'},
    {'reporting_period':'202613'},
    {'state_abbreviation':'XX'},
    {'preliminary_updated':'X'},
])
def test_bad_source_values_fail_closed(tmp_path,change):
    source=fixture(tmp_path,[change])
    with pytest.raises(ValueError):parse_rows(source,FIELDS)


def test_duplicate_source_key_rejected(tmp_path):
    source=fixture(tmp_path,[{},{}])
    with pytest.raises(ValueError,match='Duplicate'):parse_rows(source,FIELDS)


def test_schema_drift_rejected(tmp_path):
    source=fixture(tmp_path,[{}])
    source.write_text(source.read_text().replace('State Abbreviation','Unknown State',1))
    with pytest.raises(ValueError,match='header'):parse_rows(source,FIELDS)


def test_hash_mismatch_does_not_create_candidate(tmp_path):
    source=fixture(tmp_path,[{}]);lock=lock_for(source)
    source.write_text(source.read_text()+'\n')
    with pytest.raises(ValueError,match='identity'):build(source,tmp_path/'bad',FIELDS,lock)
    assert not (tmp_path/'bad').exists()


def test_existing_artifact_directory_preserved(tmp_path):
    source=fixture(tmp_path,[{}]);out=tmp_path/'existing';out.mkdir()
    marker=out/'important.txt';marker.write_text('keep')
    with pytest.raises(FileExistsError):build(source,out,FIELDS,lock_for(source),full_release=False)
    assert marker.read_text()=='keep'


def test_component_mismatch_prevents_completed_artifact(tmp_path):
    source=fixture(tmp_path,[{'total_medicaid_and_chip_enrollment':'200'}]);out=tmp_path/'bad'
    with pytest.raises(ValueError,match='reconciliation'):build(source,out,FIELDS,lock_for(source),full_release=False)
    assert not (out/'manifest.json').exists()
    assert not (out/'medicaid-enrollment.duckdb').exists()


def test_download_uses_verified_cache_without_network(tmp_path,monkeypatch):
    source=fixture(tmp_path,[{}])
    monkeypatch.setattr('requests.get',lambda *a,**k:pytest.fail('Unexpected network'))
    download(lock_for(source),source)


def test_oversized_download_lock_rejected_before_network(tmp_path):
    lock=json.loads((ROOT/'source-lock.json').read_text());lock['bytes']=33*1024**2
    with pytest.raises(ValueError,match='cap'):download(lock,tmp_path/'new.csv')
