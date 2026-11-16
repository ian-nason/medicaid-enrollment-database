"""Exercise released Python client with real HTTP range attachment.

0.1.5 has no startup config argument. The adapter below supplies only resource
and extension-cache settings to its real DuckDB connection; no data/query or
HTTP operation is mocked.
"""
import importlib.metadata
import json
import sys
from pathlib import Path

import duckdb
import datapond
import datapond.registry as registry

url, cache = sys.argv[1:]
cache = Path(cache); cache.mkdir(parents=True, exist_ok=False)
registry.REGISTRY_URL = url
registry.CACHE_DIR = cache
registry.CACHE_FILE = cache/'registry.json'
connect = duckdb.connect
def limited_connect(*args, **kwargs):
    config = dict(kwargs.pop('config', {}))
    config.update(threads='1', memory_limit='128MiB', max_temp_directory_size='0B', extension_directory=str(cache/'extensions'))
    return connect(*args,config=config,**kwargs)
duckdb.connect = limited_connect
assert datapond.list()==['medicaid-enrollment']
con = datapond.connect('medicaid-enrollment',quiet=True)
try:
    assert con.execute('SELECT count(*) FROM enrollment').fetchone()[0]==11220
    assert con.execute('SELECT count(*) FROM monthly_updated').fetchone()[0]==5559
    assert con.execute('SELECT count(*) FROM monthly_preliminary').fetchone()[0]==5610
    assert con.execute('SELECT count(*) FROM baseline_enrollment WHERE reporting_month IS NULL').fetchone()[0]==51
    assert con.execute("SELECT sum(total_medicaid_and_chip_enrollment) FROM monthly_preliminary WHERE reporting_period='202607'").fetchone()[0]==72946510
    assert con.execute('SELECT count(*) FROM _metadata').fetchone()[0]==2
    datapond.describe('medicaid-enrollment')
    datapond.describe('medicaid-enrollment',table='enrollment')
    try: con.execute('DELETE FROM enrollment'); raise AssertionError('Write unexpectedly allowed')
    except duckdb.InvalidInputException: pass
    example=con.execute("SELECT state_abbreviation,total_medicaid_enrollment,total_chip_enrollment FROM monthly_preliminary WHERE reporting_period='202607' ORDER BY state_abbreviation LIMIT 3").fetchall()
    print(json.dumps({'passed':True,'client':'Python datapond','version':importlib.metadata.version('datapond'),'duckdb':duckdb.__version__,'rows':11220,'july_total':72946510,'example':example,'connection_adapter':'resource limits and workspace extension cache only'}))
finally:
    con.close()
