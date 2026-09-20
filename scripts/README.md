# Maintained utilities

Run scripts from the repository root.

| Folder | Tools |
|---|---|
| `collect/` | YouTube About, Twitch source collection/expansion, analytics directories |
| `review/` | Twitch review preparation/building; current Stage 4 classification and payload builder |
| `maintenance/` | `refresh_reports.py`; saturation analysis; analytics Sheets request preparation |
| `automation/` | Windows 24/7 bounded discovery loop (`run_discovery_24x7.ps1`) |

The application entrypoint is `python -m registry`. The removed two-pass `run_all.py` is superseded by `map-creators`; completed lead/retry/integration programs remain recoverable in Git history.
Collection and apply builders run only on explicit request. Some older utilities still have run-specific input defaults: inspect `--help` or their input constants before use.
Refresh counts without crawling: `python scripts/maintenance/refresh_reports.py --as-of YYYY-MM-DD`.
No tracked scratch programs or empty category directories are needed.

Frontend projection: `python scripts/maintenance/export_frontend.py` reads the
registry and writes a public allowlist to ignored `web/public/data/registry.json`.
It does not fetch profiles, review identities or change canonical data.


## Windows 24/7 discovery

Create a Python 3.11+ virtual environment with the discovery extra, then test one bounded cycle before leaving it unattended. On Windows the discovery browser prefers installed Chrome, then Microsoft Edge, and only falls back to the Playwright Chromium bundle; a browser download is therefore optional:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/automation/run_discovery_24x7.ps1 -Once
```

Continuous mode defaults to a three-hour tick during the harvest phase. Directory diff runs once per day, core browser discovery every six hours, and experimental public surfaces every twelve hours. Scheduled runs execute rather than being suppressed by multi-day freshness guards; entity dedupe still prevents repeated observations from being treated as new identities.
The loop creates backups/logs under ignored `scratch/discovery-24x7/` and deliberately does
not push or merge Git changes automatically. Automated Hub VTuber Thai crawls are kept as one
`intake/raw/*-vtuberthai-directory-new.jsonl` capture per cycle instead of exploding the capture
into hundreds of six-row batch files; manual/review workflows can split or ingest that raw capture later.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/automation/run_discovery_24x7.ps1
```
