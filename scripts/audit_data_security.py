"""Destination-aware audit of Git artifacts, history and authorized Google Sheets."""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.data_security import inspect_blob, Classification
from scripts.audit_private_data_plane import local_secret_values, audit_private_sheet
from storage.private_sheet_store import PrivateSheetStore


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def audit_git(ref='HEAD', history=False):
    secrets = local_secret_values()
    findings, inventory = [], []
    for line in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
        if not line: continue
        metadata, path_bytes = line.split(b'\t',1)
        mode, kind, oid = metadata.decode().split()
        if kind != 'blob': continue
        path = path_bytes.decode('utf-8')
        classification, reason = inspect_blob(path, git('cat-file','blob',oid), secrets)
        row = {'path':path, 'classification':classification,'reason':reason}
        inventory.append(row)
        if classification != Classification.PUBLIC_RESEARCH_DATA.value:
            findings.append(row)
        elif reason.startswith('UNREADABLE'):
            findings.append({**row, 'status':'WARNING'})
    historic=[]
    if history:
        for line in git('rev-list','--objects','--all').decode().splitlines():
            oid, _, path = line.partition(' ')
            if not path or git('cat-file','-t',oid).strip()!=b'blob': continue
            classification, reason = inspect_blob(path, git('cat-file','blob',oid), secrets)
            if classification != Classification.PUBLIC_RESEARCH_DATA.value:
                commits = git('log','--all','--format=%H','--find-object='+oid,'--',path).decode().splitlines()
                historic.append({'path':path,'blob':oid,'classification':classification,
                                 'commits':commits,'reason':reason,
                                 'credential_status':'COMPROMISED' if classification=='SECRET_CREDENTIAL' else None})
    ignored={}
    for path in ('config/secret.key','credentials.json','.env','data/private_recovery/probe.csv'):
        result=subprocess.run(['git','check-ignore','-q','--no-index',path],cwd=ROOT)
        ignored[path]=result.returncode==0
    failures=[r for r in findings if r.get('status')!='WARNING']
    return {'status':'FAIL' if failures or not all(ignored.values()) else 'WARNING' if findings else 'PASS',
            'ref':ref,'classification_counts':dict(collections.Counter(r['classification'] for r in inventory)),
            'inventory':inventory,'findings':findings,'ignore_checks':ignored,'history_findings':historic,
            'scope':'All Git blobs at ref; optional all reachable historical blobs decoded by format; no history rewrite'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--history',action='store_true')
    parser.add_argument('--git-only',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report={'git':audit_git(history=args.history)}
    if not args.git_only:
        report['sheet']=audit_private_sheet(PrivateSheetStore().spreadsheet,local_secret_values())
    statuses=[v['status'] for v in report.values()]
    report['status']='FAIL' if 'FAIL' in statuses else 'WARNING' if 'WARNING' in statuses else 'PASS'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='git'} | {'git':{k:v for k,v in report['git'].items() if k!='inventory'}},indent=2))
    return int(report['status']=='FAIL')


if __name__=='__main__': sys.exit(main())
