#!/usr/bin/env python3
"""Rebuild all analyses from frozen canonical evidence and public annotations.

Real viewer evidence is read once from the private Sheet and remains in RAM.
No committed upstream analytical outputs are copied into reproduction roots.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from scripts.analysis_dag import DAG, ROOT, analysis_context, run_dag, public_artifact_paths

PIPELINE_STEPS = [(name, [sys.executable, 'scripts/' + module + '.py']) for name, _, module, _ in DAG]
VOLATILE_JSON_KEYS = {'generated_at'}


def normalized(value):
    if isinstance(value, dict):
        return {k:normalized(v) for k,v in sorted(value.items()) if k not in VOLATILE_JSON_KEYS}
    if isinstance(value, list):
        return [normalized(v) for v in value]
    return value


def semantic_hashes(root):
    results = {}
    for path in public_artifact_paths(root):
        if path.name == 'reproducibility_evidence.json':
            continue
        if path.suffix == '.parquet':
            df = pd.read_parquet(path).drop(columns=['calculated_at'], errors='ignore')
            rows = sorted(json.dumps(normalized(row), sort_keys=True, default=str) for row in df.to_dict('records'))
            data = json.dumps({'columns':list(df.columns), 'rows':rows},sort_keys=True).encode()
        elif path.suffix == '.json':
            data = json.dumps(normalized(json.loads(path.read_text(encoding='utf-8'))),sort_keys=True).encode()
        else:
            data = path.read_bytes().replace(b'\r\n',b'\n')
        results[path.relative_to(root).as_posix()] = 'sha256_' + hashlib.sha256(data).hexdigest()
    return results


def code_fingerprint():
    paths = sorted(p for directory in ('scripts','core','storage') for p in (ROOT/directory).glob('*.py'))
    payload = b''.join(p.relative_to(ROOT).as_posix().encode() + p.read_bytes().replace(b'\r\n',b'\n') for p in paths)
    return 'sha256_' + hashlib.sha256(payload).hexdigest()


def reproduce_twice(source=ROOT):
    source = Path(source).resolve()
    from scripts import build_duckdb_temporal_snapshots as snapshots
    with analysis_context(source), duckdb.connect(':memory:') as con:
        snapshots.build_unified_raw_view(con)
        table = con.execute('SELECT * FROM unified_raw').to_arrow_table()
    canonical_rows = sorted(json.dumps(row, sort_keys=True, default=str) for row in table.to_pylist())
    canonical_digest = hashlib.sha256('\n'.join(canonical_rows).encode()).hexdigest()
    del canonical_rows
    inputs = {}
    for folder in ('catalog','lifecycle'):
        for path in sorted((source/'data/temporal'/folder).rglob('*')):
            if path.is_file():
                inputs[path.relative_to(source).as_posix()] = path.read_bytes()
    windows = pd.read_parquet(source/'data/temporal/snapshots/network_snapshots.parquet')
    window_meta = windows[['window_type','window_start','window_end','calculated_at']].drop_duplicates()
    input_digest = hashlib.sha256(canonical_digest.encode() + window_meta.to_json(orient='records').encode() +
                                  b''.join(k.encode()+v for k,v in sorted(inputs.items()))).hexdigest()
    builds = []
    with tempfile.TemporaryDirectory(prefix='thai-sna-reproduce-') as temp:
        for name in ('A','B'):
            root = Path(temp)/name
            for rel, data in inputs.items():
                target = root/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            path = root/'data/temporal/snapshots/network_snapshots.parquet'
            path.parent.mkdir(parents=True,exist_ok=True)
            window_meta.to_parquet(path,index=False)
            run_dag(root, canonical_table=table)
            builds.append(semantic_hashes(root))
    differences = sorted(k for k in set(builds[0]) | set(builds[1]) if builds[0].get(k) != builds[1].get(k))
    return dict(status='REPRODUCIBLE_FROM_INPUTS' if not differences else 'NOT_REPRODUCIBLE',
                input_fingerprint='sha256_'+input_digest, code_fingerprint=code_fingerprint(),
                pipeline_steps=[step[0] for step in DAG],
                normalization={'json_keys':sorted(VOLATILE_JSON_KEYS),'parquet_columns':['calculated_at'],
                               'parquet_row_order':'unordered records','text_newlines':'LF',
                               'build_reference_clock':'2026-09-08T00:00:00+00:00'},
                artifact_hashes=builds[0], differences=differences)


def run_pipeline(dry_run=False):
    if dry_run:
        for name, command in PIPELINE_STEPS:
            print(name, ' '.join(command))
        return True
    run_dag(ROOT)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify-reproducibility',action='store_true')
    args = parser.parse_args()
    if args.verify_reproducibility:
        evidence = reproduce_twice()
        path = ROOT/'data/temporal/release/reproducibility_evidence.json'
        path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print(evidence['status'], evidence['differences'])
        sys.exit(0 if evidence['status'] == 'REPRODUCIBLE_FROM_INPUTS' else 1)
    sys.exit(0 if run_pipeline(args.dry_run) else 1)
