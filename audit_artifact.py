"""Independent cell-by-cell CSV reconciliation and execution of shipped examples."""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import duckdb

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'artifacts-release/manifest.json').read_text())
source=ROOT/'data'/manifest['source']['file']
db=ROOT/'artifacts-release/medicaid-enrollment.duckdb'
con=duckdb.connect(str(db),read_only=True,config={'threads':'1','memory_limit':'128MiB','max_temp_directory_size':'0B'})
fields=con.execute('SELECT column_name,duckdb_type FROM field_definitions ORDER BY ordinal').fetchall()
cursor=con.execute('SELECT '+','.join('"'+x[0]+'"' for x in fields)+' FROM enrollment ORDER BY source_row_number')
rows=cursor.fetchall()
cells=0
with source.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.reader(f);next(reader)
    n=0
    for n,source_row in enumerate(reader,1):
        assert n<=len(rows)
        for i,(name,typ) in enumerate(fields):
            raw=source_row[i];actual=rows[n-1][i]
            expected=None if raw=='' else int(raw) if typ=='BIGINT' else Decimal(raw) if typ.startswith('DECIMAL') else raw
            assert actual==expected,(n,name,raw,actual)
            cells+=1
    assert n==len(rows)==11220
examples=[]
for sql in (ROOT/'examples.sql').read_text().split(';'):
    if sql.strip():
        result=con.execute(sql).fetchall()
        examples.append({'sql':sql.strip(),'rows':len(result),'first_row':[str(x) if x is not None else None for x in result[0]]})
assert [x['rows'] for x in examples]==[12,5,51]
nulls={}
for name in manifest['null_counts']:
    nulls[name]=con.execute('SELECT count(*) FROM enrollment WHERE "'+name+'" IS NULL').fetchone()[0]
assert nulls==manifest['null_counts']
con.close()
with db.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==manifest['artifact']['sha256']
report={'passed':True,'source_rows_compared':n,'source_cells_compared':cells,'cell_mismatches':0,'null_count_columns_reconciled':len(nulls),'examples':examples,'artifact_sha256':digest}
(OUT/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
