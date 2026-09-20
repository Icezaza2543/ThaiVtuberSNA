# Data and code locations

| Location | Role |
|---|---|
| `data/registry.json` | Canonical registry; do not derive the current state from old review batches |
| `intake/consolidated/` | Current stage outputs and retained source material for those stages |
| `intake/raw/` | New immutable public captures |
| `intake/*public-profiles*.jsonl`, `*owner*.jsonl`, `*evidence*.jsonl` | Legacy immutable captures: paths remain pinned for evidence and runtime globs |
| `intake/2026-09-13-analytics-*/` | Retained historical analytics sources/publication snapshots |
| `intake/archive/` | Old queues, partial runs and working notes; not the current pipeline input |
| `reviews/pending/` | Unfinished proposals; see its README before selecting a batch |
| `reviews/applied/` | Completed apply payloads, kept once |
| `reviews/archive/` | Lossless historical review bundle, never automatically applied |
| `reports/current/` | Only current report location; rebuild with the refresh command |
| `reports/archive/` | Dated publications and historical handoffs |
| `scripts/collect/` | Retained public collection utilities |
| `scripts/review/` | Retained review builders |
| `scripts/maintenance/` | Report refresh and publication utilities |
| `registry/` | Application and pipeline; legacy discovery is still imported, not dead code |

Refresh offline: `python scripts/maintenance/refresh_reports.py --as-of YYYY-MM-DD`.
`platform-coverage.json` records the registry checksum it was generated from.
The current matrix measures reviewed presence; dated activity uses `summary.json` and has different evidence requirements.

No canonical data, identity decisions, observations or evidence bytes were changed by cleanup.
Historical review files were bundled, not merged into a new identity truth.
Completed one-off programs remain recoverable in Git at pre-cleanup commit `b9b4094`.
Temporary files belong in ignored `scratch/`, not new tracked helper programs.

Frontend additions: `.agents/skills/` holds focused workspace skills; `DESIGN.md`
holds visual choices; `docs/frontend-handoff.md` holds the UI/data/hosting contract.
`web/` is reserved for frontend source. `web/public/data/registry.json` is generated
by `scripts/maintenance/export_frontend.py` and excluded from Git.
The pre-refresh Stage 3 snapshot is in `intake/archive/2026-09-16/`;
`scripts/_tmp_coverage.py` was untracked (recoverable at deed139).
