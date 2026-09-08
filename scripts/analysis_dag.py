"""One explicit rebuild graph shared by reproduction and observatory updates.

Catalog and lifecycle annotations are frozen public inputs. All network-dependent
outputs are rebuilt. A relocated root is only for synthetic sandbox data.
"""
import importlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DAG = (
    ('T7', ('snapshots',), 'analyze_temporal_communities', 'run_temporal_community_analysis'),
    ('T7_transitions', ('T7', 'canonical'), 'analyze_audience_transitions', 'run_audience_transition_analysis'),
    ('T11', ('T7',), 'build_community_lineage_v2', 'build_community_lineage_v2'),
    ('T12', ('canonical',), 'analyze_audience_cohorts', 'run_audience_cohort_analysis'),
    ('T13', ('T7', 'snapshots'), 'analyze_centrality_evolution', 'run_centrality_evolution_analysis'),
    ('T14', ('T7', 'snapshots'), 'analyze_ecosystem_evolution', 'run_ecosystem_evolution_analysis'),
    ('T9', ('canonical', 'lifecycle'), 'analyze_event_impact', 'main'),
    ('T10', ('canonical', 'snapshots'), 'validate_temporal_robustness', 'main'),
    ('T15', ('T10', 'T7', 'canonical'), 'analyze_evidence_quality', 'run_evidence_quality_analysis'),
    ('T17', ('T7_transitions', 'T9', 'T10', 'T11', 'T12', 'T13', 'T14', 'T15'), 'build_research_dashboard_data', 'main'),
    ('T18', ('T17',), 'build_dataset_release', 'main'),
    ('T19', ('T18',), 'build_technical_report', 'main'),
    # Report is generated after the release description, then included in its final checksums.
    ('release_finalize', ('T19',), 'build_dataset_release', 'main'),
    ('validate', ('release_finalize',), 'validate_dataset_release', 'validate_release'),
)
OUTPUT_DIRS = ('analysis', 'cohorts', 'centrality', 'ecosystem', 'event_analysis', 'robustness', 'quality', 'release', 'report')


def public_artifact_paths(root):
    root = Path(root)
    directories = [root / 'data/temporal' / name for name in (*OUTPUT_DIRS, 'snapshots')]
    directories.append(root / 'web/research')
    files = [p for folder in directories for p in folder.rglob('*') if p.is_file()
             and not any(part.startswith('.') for part in p.relative_to(folder).parts)]
    web_communities = root / 'web/data/temporal_communities.json'
    if web_communities.exists():
        files.append(web_communities)
    return sorted(files)


@contextmanager
def analysis_context(root, epoch='2026-09-08T00:00:00+00:00', canonical_table=None):
    """Bind legacy analysis modules to one explicit root and deterministic build clock.

    No input fallback into the checkout. Restores bindings on failure as well.
    Run under a single writer or in an isolated reproduction process.
    """
    root = Path(root).resolve()
    if root != ROOT:
        from core.storage_boundary import require_synthetic_local_path
        require_synthetic_local_path(root)
    names = {step[2] for step in DAG} | {'build_duckdb_temporal_snapshots', 'build_historical_lifecycle'}
    modules = [importlib.import_module('scripts.' + name) for name in sorted(names)]
    changes = []
    class BuildClock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime.fromisoformat(epoch)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    def bind(module, key, value):
        changes.append((module, key, getattr(module, key)))
        setattr(module, key, value)
    from scripts import build_duckdb_temporal_snapshots as snapshots
    original_raw = snapshots.build_unified_raw_view
    import storage.private_sheet_analytics as private
    original_sheet_raw = private.build_sheet_unified_raw
    table_cache = [canonical_table]
    def raw(con, sources_by_prov=None):
        if sources_by_prov is not None:
            return original_raw(con, sources_by_prov)
        if root == ROOT and table_cache[0] is None:
            original_sheet_raw(con)
            table_cache[0] = con.execute('SELECT * FROM unified_raw').to_arrow_table()
        if table_cache[0] is not None:
            con.execute("SET temp_directory = ''")
            con.register('_frozen_private_input', table_cache[0])
            con.execute('CREATE OR REPLACE VIEW unified_raw AS SELECT * FROM _frozen_private_input')
            return
        original_raw(con, snapshots.get_sources_by_provenance(base_dir=root))
        cols = [r[0] for r in con.execute('DESCRIBE unified_raw').fetchall()]
        if 'partial_capture' not in cols:
            con.execute('CREATE TEMP TABLE sandbox_raw AS SELECT *, NULL::BOOLEAN AS partial_capture FROM unified_raw')
            con.execute('CREATE OR REPLACE VIEW unified_raw AS SELECT * FROM sandbox_raw')
    try:
        for module in modules:
            for key, value in list(vars(module).items()):
                if isinstance(value, Path) and value.is_absolute() and value.is_relative_to(ROOT):
                    bind(module, key, root / value.relative_to(ROOT))
                elif key == 'datetime':
                    bind(module, key, BuildClock)
            if hasattr(module, 'build_unified_raw_view'):
                bind(module, 'build_unified_raw_view', raw)
        # T10's depth comparator must use the same canonical input provider.
        bind(private, 'build_sheet_unified_raw', raw)
        for directory in OUTPUT_DIRS:
            (root / 'data/temporal' / directory).mkdir(parents=True, exist_ok=True)
        yield
    finally:
        for module, key, value in reversed(changes):
            setattr(module, key, value)


def rebuild_canonical_snapshots(root):
    """Recompute edges from canonical inputs; retain only window/cutoff metadata."""
    from scripts import build_duckdb_temporal_snapshots as s
    path = Path(root) / 'data/temporal/snapshots/network_snapshots.parquet'
    previous = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    with duckdb.connect(':memory:') as con:
        s.build_unified_raw_view(con)
        s.build_canonical_events_view(con)
        years = [r[0] for r in con.execute('SELECT DISTINCT year(interaction_time) FROM canonical_events WHERE interaction_time IS NOT NULL ORDER BY 1').fetchall()]
        windows = {}
        if not previous.empty:
            for row in previous[['window_type','window_start','window_end','calculated_at']].drop_duplicates().itertuples(index=False):
                windows[tuple(row[:3])] = row[3]
        for year in years:
            end = f'{year}-12-31 23:59:59' if year != 2026 else '2026-09-08 23:59:59'
            if not any(k[0] == 'yearly' and k[1].startswith(str(year)) for k in windows):
                windows[('yearly',f'{year}-01-01',end)] = '2026-09-08 00:00:00 UTC'
            if not any(k[0] == 'cumulative' and k[2].startswith(str(year)) for k in windows):
                windows[('cumulative',f'{min(years)}-01-01',end)] = '2026-09-08 00:00:00 UTC'
        if not any(k[0] == 'all_time' for k in windows):
            windows[('all_time',f'{min(years)}-01-01',f'{max(years)}-12-31 23:59:59')] = '2026-09-08 00:00:00 UTC'
        rows = []
        coverage = s.load_channel_coverage_records(base_dir=Path(root))
        for (kind,start,end), calculated in sorted(windows.items()):
            rows.extend(s.compute_window_snapshots(con,dict(type=kind,start=start,end=end),coverage,calculated_at=calculated))
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=s.NETWORK_SNAPSHOT_SCHEMA),path)


def run_dag(root=ROOT, rebuild_snapshots=True, canonical_table=None):
    done = {'canonical', 'lifecycle', 'snapshots'}
    with analysis_context(root, canonical_table=canonical_table):
        if rebuild_snapshots:
            rebuild_canonical_snapshots(root)
        for name, parents, module, function in DAG:
            if not set(parents) <= done:
                raise RuntimeError(f'Unmet dependencies for {name}')
            print(f'Rebuilding {name}', flush=True)
            result = getattr(importlib.import_module('scripts.' + module), function)()
            if (name == 'validate' and result is not True) or (type(result) is int and result != 0):
                raise RuntimeError(f'Analysis step failed: {name}')
            if name not in ('T18', 'T19', 'release_finalize', 'validate'):
                # Unordered SQL aggregates must not make release byte checksums vary.
                for directory in OUTPUT_DIRS:
                    for path in (Path(root) / 'data/temporal' / directory).glob('*.parquet'):
                        table = pq.read_table(path)
                        rows = sorted(table.to_pylist(), key=lambda row: json.dumps(row,sort_keys=True,default=str))
                        pq.write_table(pa.Table.from_pylist(rows,schema=table.schema),path)
            done.add(name)
    return [step[0] for step in DAG]
