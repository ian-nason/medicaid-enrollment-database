"""Serve exactly the candidate and a local registry; test both real clients."""
import argparse
import hashlib
import http.server
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--db',type=Path,default=ROOT/'artifacts-release/medicaid-enrollment.duckdb')
parser.add_argument('--rscript',required=True)
parser.add_argument('--r-client-library',required=True)
parser.add_argument('--r-dependency-library',required=True)
parser.add_argument('--out',type=Path,default=ROOT/'evidence/consumer')
args=parser.parse_args()
args.out.mkdir(parents=True,exist_ok=False)
DB=args.db.resolve()
counts={'requests':0,'ranges':0,'bytes_sent':0}
digest=hashlib.sha256(DB.read_bytes()).hexdigest()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):self.serve(True)
    def do_HEAD(self):self.serve(False)
    def serve(self,body):
        counts['requests']+=1
        if self.path=='/registry.json':
            data=json.dumps({'databases':[{'id':'medicaid-enrollment','name':'CMS Medicaid/CHIP enrollment local candidate','size_gb':DB.stat().st_size/1024**3,'attach_url':f'http://127.0.0.1:{self.server.server_port}/medicaid-enrollment.duckdb'}]}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers()
            if body:self.wfile.write(data)
            return
        if self.path!='/medicaid-enrollment.duckdb':self.send_error(404);return
        size=DB.stat().st_size;start=0;end=size-1
        requested=self.headers.get('Range')
        if requested:
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',requested)
            if not match:self.send_error(416);return
            start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
            if start>end:self.send_error(416);return
            counts['ranges']+=1
        self.send_response(206 if requested else 200)
        self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('ETag','"'+digest+'"')
        if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        if body:
            with DB.open('rb') as f:
                f.seek(start);left=end-start+1
                while left:
                    block=f.read(min(left,65536));self.wfile.write(block);left-=len(block);counts['bytes_sent']+=len(block)

server=http.server.HTTPServer(('127.0.0.1',0),Handler)
worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
base=f'http://127.0.0.1:{server.server_port}/registry.json'
commands={
    'python':[sys.executable,str(ROOT/'smoke_python.py'),base,str(args.out/'python-cache')],
    'r':[args.rscript,str(ROOT/'smoke_r.R'),base,str(args.out/'r-cache'),args.r_client_library,args.r_dependency_library],
}
results={'started_at_utc':datetime.now(timezone.utc).isoformat(),'artifact_sha256':digest,'artifact_bytes':DB.stat().st_size}
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
try:
    for name,command in commands.items():
        p=subprocess.run(command,capture_output=True,text=True,timeout=150,env=env)
        results[name]={'command':command,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        (args.out/(name+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
        print(name,p.returncode,p.stdout[-1600:],p.stderr[-1000:],flush=True)
finally:
    server.shutdown();server.server_close();worker.join(timeout=5)
results['http']=counts
results['completed_at_utc']=datetime.now(timezone.utc).isoformat()
(args.out/'consumer-smoke.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if all(results.get(k,{}).get('exit_code')==0 for k in commands) and counts['ranges']>0 else 1)
