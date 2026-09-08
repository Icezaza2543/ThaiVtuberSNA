"""Destination-aware audit of Git artifacts, history and authorized Google Sheets."""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.data_security import inspect_blob, inspect_database, Classification
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
    return {'status':'FAIL' if failures or not all(ignored.values()) else 'WARNING' if findings or historic else 'PASS',
            'ref':ref,'classification_counts':dict(collections.Counter(r['classification'] for r in inventory)),
            'inventory':inventory,'findings':findings,'ignore_checks':ignored,'history_findings':historic,
            'scope':'All Git blobs at ref; optional all reachable historical blobs decoded by format; no history rewrite'}


def audit_local():
    """Inventory ignored project data and independently inspect public output trees."""
    roots = [ROOT/p for p in ('data','logs','web','releases','dist','config')]
    if (ROOT/'.worktrees').exists():
        roots += [p/'data' for p in (ROOT/'.worktrees').iterdir() if p.is_dir()]
    paths = {p for root in roots if root.exists() for p in root.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/p for p in ('credentials.json','.env') if (ROOT/p).exists())
    secrets = local_secret_values()
    inventory, findings = [], []
    for p in sorted(paths):
        relative = p.relative_to(ROOT).as_posix()
        if p.suffix in ('.sqlite','.sqlite3','.db','.duckdb'):
            try: classification,reason = inspect_database(p,secrets)
            except Exception:
                classification,reason = 'PUBLIC_RESEARCH_DATA','UNREADABLE: database manual review required'
        else: classification,reason = inspect_blob(relative,p.read_bytes(),secrets)
        if p.name == '.env' or p.name == 'credentials.json' or p.suffix == '.key':
            classification,reason = 'SECRET_CREDENTIAL','Local credential/configuration; values withheld'
        row={'path':relative,'classification':classification,'reason':reason}
        inventory.append(row)
        ignored = subprocess.run(['git','check-ignore','-q','--no-index',relative],cwd=ROOT).returncode == 0 if classification=='SECRET_CREDENTIAL' else False
        public = relative.split('/')[0] in ('web','releases','dist')
        if classification=='PRIVATE_DATA' or (classification=='SECRET_CREDENTIAL' and (public or not ignored)):
            findings.append({**row,'status':'FAIL'})
        elif reason.startswith('UNREADABLE'):
            findings.append({**row,'status':'WARNING'})
    return {'status':'FAIL' if any(x['status']=='FAIL' for x in findings) else 'WARNING' if findings else 'PASS',
            'classification_counts':dict(collections.Counter(x['classification'] for x in inventory)),
            'inventory':inventory,'findings':findings,
            'scope':'Working public outputs and project data including ignored worktree data; local credentials permitted only if ignored. Git object store is covered separately. No OS backup/swap inspection.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--history',action='store_true')
    parser.add_argument('--git-only',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report={'git':audit_git(history=args.history), 'local':audit_local()}
    if not args.git_only:
        report['sheet']=audit_private_sheet(PrivateSheetStore().spreadsheet,local_secret_values())
    statuses=[v['status'] for v in report.values()]
    report['status']='FAIL' if 'FAIL' in statuses else 'WARNING' if 'WARNING' in statuses else 'PASS'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:({a:b for a,b in v.items() if a!='inventory'} if isinstance(v,dict) else v) for k,v in report.items()},indent=2))
    return int(report['status']=='FAIL')


if __name__=='__main__': sys.exit(main())
