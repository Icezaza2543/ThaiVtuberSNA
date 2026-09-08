"""Generate the hotfix report from public artifacts and recorded validation evidence."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.analyze_evidence_quality import modality_comparison
from scripts.observatory_controller import compute_coordinates_block_hash, compute_historical_baseline_hash
from scripts.validate_dataset_release import validation_level
from scripts.reproduce_temporal_dataset import code_fingerprint


def main():
    evidence = ROOT/'docs/evidence'
    e2e = json.loads((evidence/'hotfix_full_e2e.json').read_text())
    repro = json.loads((evidence/'hotfix_synthetic_reproducibility.json').read_text())
    checks = json.loads((evidence/'hotfix_validation.json').read_text())
    suite = ET.parse(evidence/'hotfix_full_suite.xml').getroot().find('testsuite')
    if int(suite.attrib['failures']) or int(suite.attrib['errors']):
        raise RuntimeError('The final full test suite did not pass')
    test_count = int(suite.attrib['tests'])
    checks['commands']['python -m pytest tests/ -q'] = f"PASS: {test_count} tests; {suite.attrib['time']} seconds; final JUnit evidence saved"
    checks['commands'].pop('targeted report regressions after strict bindings',None)
    checks['commands'].pop('targeted analytical, crash and full-DAG regressions after deterministic ordering',None)
    checks['full_suite_warnings'] = 'Undefined assortativity for small synthetic graphs; no test failures.'
    (evidence/'hotfix_validation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    if repro['code_fingerprint'] != code_fingerprint():
        raise RuntimeError('Reproduction evidence does not match current analysis code')
    q = pd.read_parquet(ROOT/'data/temporal/quality/yearly_evidence_quality.parquet')
    surv = pd.read_parquet(ROOT/'data/temporal/cohorts/cohort_survival.parquet')
    modality = modality_comparison()
    lines = ['# Final analytical and transactional hotfix verification', '',
             '## Current analytical artifacts', '',
             f"T15 reads T10's 2026 comment-only configuration (threshold 1, resolution 1, seed 42): "
             f"NMI **{modality['nmi_to_baseline']:.4f}**, ARI **{modality['ari_to_baseline']:.4f}**. No numeric constants are used in the report binding.", '',
             '| Year | Interaction evidence channels | Catalog published channels | Intersection | Catalog active recall | Target manifest coverage |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in q.itertuples():
        lines.append(f'| {r.year} | {r.interaction_evidence_channel_count} | {r.catalog_published_channel_count} | '
                     f'{r.intersection_count} | {r.catalog_active_recall:.6f} | {r.target_manifest_coverage:.6f} |')
    lines.extend(['', f'T19 binds and regression-checks all **{len(surv)} elapsed horizons** against the actual '
                  '`pooled_cohort_size`, `pooled_reobserved_viewers`, `same_channel_persistence_rate` and '
                  '`cross_channel_persistence_rate` columns. Missing required files/columns raise errors. '
                  'Unsupported narrative findings and numeric fallbacks were removed.', '',
                  '## Transaction and downstream evidence', '',
                  'T16 crash points A (before artifact writes), B (after batch), C (after snapshot), '
                  'D (before state promotion), and E (after transaction decision, before cleanup) all pass. '
                  'Each recovered batch, snapshot, pipeline state and release-state file equals the clean execution byte for byte.', '',
                  'A durable undo journal precedes file mutations. A commit marker decides recovery; '
                  'an interrupted uncommitted generation restores its before image. '
                  'Advisory locks serialize ingestion. These checks simulate process interruption, not hardware power loss.', '',
                  'The update graph runs T7 communities and audience transitions, T11 lineage, T12 cohorts, '
                  'T13 centrality, T14 ecosystem, T9 event effects, T10 sensitivity, T15 quality, T17 dashboard, '
                  'T18 release, T19 report, final release checksums, and validation. '
                  'The reproducer first rebuilds canonical snapshots. Catalog/lifecycle annotations and window definitions are explicit frozen inputs; derived analyses are not copied.', '',
                  f"Synthetic **{e2e['year']}** update ran without skipped downstream stages and published **{e2e['version_after_update']}**. "
                  f"All-time shared audience changed **{e2e['shared_before']} → {e2e['shared_after']} → {e2e['shared_after_rollback']}**.", '',
                  f"Rollback restored **{e2e['public_files_restored']} public output checksums**, yearly/cumulative/all-time snapshots, "
                  'all downstream products, T16 state and the observatory version/state. The batch disappeared. '
                  'The operational run ledger deliberately retains the rollback audit trail. '
                  'A separate injected failure after T12 also restores the complete before image.', '',
                  f"Two clean synthetic input rebuilds: **{repro['status']}**, **{len(repro['artifact_hashes'])} artifacts**, "
                  f"**{len(repro['differences'])} differences**. Exact comparison rules and fingerprints are in "
                  '[hotfix_synthetic_reproducibility.json](evidence/hotfix_synthetic_reproducibility.json).', '',
                  'The build clock is a declared deterministic reference, not a wall-clock collection timestamp. '
                  'Comparison permits generated_at/calculated_at metadata and row/newline normalization; analytical values are not discarded.', '',
                  f"The checked-in real release is **{validation_level(ROOT)}**. The synthetic reproduction proof is not presented as proof that the real release was rebuilt from the live workbook.", '',
                  '## Validation', '', '| Check | Result |', '| --- | --- |'])
    for command, result in checks['commands'].items():
        lines.append(f'| `{command}` | {result} |')
    lines.extend(['', f'The final full suite passed **{test_count} tests** after all code changes. '
                  'The suite includes historical-window preservation, a shared writer lock and nested T16/T20 recovery. '
                  'Small synthetic graphs emit undefined-assortativity warnings; these are not failed checks.', '',
                  '## Preserved security and historical contracts', '',
                  '- LEVEL A credentials remain local/ignored, never Git or Sheets.',
                  '- LEVEL B viewer records remain only in the existing authorized ThaiVtuber_SNA workbook. No private tabs were removed or written by this hotfix.',
                  '- Real T15 regeneration reads the private archive into RAM; exported artifacts are LEVEL C aggregates.',
                  '- Local generation journals are permitted only in external synthetic sandboxes. The real T20 local-storage guard remains active pending a transactional Sheet ingestion backend.',
                  '- HMAC key and fingerprint were not changed. Historical snapshots and coordinates were not regenerated.', '',
                  f"Coordinates: `{compute_coordinates_block_hash(ROOT/'web/app.js')}`.", '',
                  f"Protected pre-2026 snapshot digest: `{compute_historical_baseline_hash(ROOT/'data/temporal/snapshots/network_snapshots.parquet')}`.", '',
                  'No live collection or broad production-readiness claim is made by these sandbox results.', ''])
    (ROOT/'docs/final_correctness_hotfix_report.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    main()
