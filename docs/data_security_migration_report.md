# Single-spreadsheet security and recovery report

Migration complete on main. Production T20 has not been started and remains ON HOLD. The sole private workbook is [ThaiVtuber_SNA](https://docs.google.com/spreadsheets/d/1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE/edit). No second spreadsheet was created.

## Classification and credentials

| Scope | SECRET_CREDENTIAL | PRIVATE_DATA | PUBLIC_RESEARCH_DATA |
|---|---:|---:|---:|
| Final repository files, including this report/evidence | 0 | 0 | 256 |
| Final local project-data inventory | 3 | 0 | 136 |
| Initial local inventory before migration | 3 | 4,489 | 144 |

Counts are files in the stated scope, not people or mutually additive inventories. Local A files are `.env`, `config/secret.key`, and `credentials.json`; they stay ignored, outside Sheets and Git. No committed credential material was detected in the reachable-history audit, so no COMPROMISED credential or rotation requirement was identified. Preserve the original HMAC key. Scans do not prove the absence of arbitrary unlabeled personal text, OS swap, external backups or inaccessible history.

Full path classifications and allowed/current locations are in [data_security_classification.md](data_security_classification.md).

## Recovery and continuity

- Expected historical count: 38,240. Original records recovered from Drive revision 380: **38,240**, verified by full readback. Only the missing viewer dataset was restored.
- Distinct historical URL candidates: **28,762**. Duplicate URL rows: **9,478**. These are not verified unique people.
- Verified historical raw channel IDs / reconstructed historical HMAC identities: **0**. All historical URLs are handles. **28,762** candidates remain unmatched; names and mutable handles were not treated as immutable IDs.
- Independent canonical HMAC identities preserved: **79,718**, retaining the original key. They are not claimed to match the historical handle candidates.
- VIEWER_INDEX therefore has **108,480** entries across two explicitly unmatched populations.
- The initial private source archive contains **142,184** source records. Complete archive readback produced exactly the same **114,869 canonical records**, same 79,718 hashes and same canonical checksum as the original local sources.
- The archive subsequently received one original synthetic regression test log whose embedded pseudonyms were redacted from the public copy. Final archive: **142,185** records. The extra log is excluded from canonical analytics.
- Removed **4,494** verified private working-copy files, including recovery staging and database sidecars. Six task-generated public test logs were also cleaned up. No credentials or legitimate public channel/video datasets were removed.

The canonical checksum is `sha256_9e502a23f6a9f83fd2a85d6934c080dae1e50c26b55ba61bb1bbe75bffa28b76`. The HMAC fingerprint remains `sha256_142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`; AGENCY_ISLAND_COORDINATES remains `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.

## Final workbook tabs

Counts exclude the header row.

| Tab | Data rows |
|---|---:|
| NETWORK_RESULT | 3,665 |
| VTUBERS | 1,370 |
| SYSTEM | 24 |
| ALL_COMMENTERS | 38,240 |
| VIEWER_INDEX | 108,480 |
| VIEWER_CHANNEL_PRESENCE | 98,170 |
| VIEWER_ACTIVITY_SUMMARY | 79,718 |
| PRIVATE_DATA_ARCHIVE | 142,185 |
| RECOVERY_METADATA | 13 |
| MIGRATION_AUDIT | 4,494 |
| DATA_DICTIONARY | 30 |

NETWORK_RESULT and VTUBERS were preserved. SYSTEM now states the private/control architecture, accurate recovery counts and T20 hold. The dictionary explains unresolved identities, observed-presence count units and source provenance. Whole-workbook permissions were checked: owner plus one service-account writer, no public/domain grant. Anyone granted workbook access may potentially access private viewer tabs; hidden/protected tabs are not independently confidential.

## Git findings and migration actions

1. Real private pilot: `data/temporal/pilot/temporal_comment_pilot.parquet`, 1,474 rows; introduced in `ac6ce266c09498a7057558aa17c229593cad441a`, blob `64a74dcafd5af0ae5aa75a2043ea1c7e51596277`. Archived in Sheets, removed from HEAD by `7bf5ac0e979812d89f503012782ccf356e4c4436`.
2. Synthetic pseudonym-bearing log: `docs/evidence/continuous-baseline-regressions.txt`; introduced in `f314b419d1720d674fa41623f0c711c1cc0d1fc0`, blob `04d65663058e96230c2f86913d18661e6cb826fd`. Original privately archived; public pseudonyms redacted by `f52af54cd2971afa0239c0c1d524f3d521edc313`.
3. Old blobs remain reachable in Git history. History audit is **WARNING**, not an erasure claim. No history rewrite or force push occurred.
4. `.gitignore` now covers private recovery/cache/archive paths, viewer CSV/JSON/Parquet exports, crawler identity outputs, incremental viewer Parquet and local SQLite/DB files. Existing credential ignores remain.
5. `purge_sheets_pii.py` and the old destructive merge are read-only audit wrappers. The Sheet writer never clears or deletes approved tabs, checks the workbook identity, rejects A credentials/message text, uses RAW input and verifies readback; conflicting or shortened replacements fail closed.
6. Default canonical analytics reads the private archive into in-memory DuckDB with disk spill disabled. Legacy production local writers and T20 update/publish are blocked. Public research outputs contain aggregates and public metadata.

## Validation

| Check | Result |
|---|---|
| `python -m pytest tests/ -q` | **269 passed**, 45.42 s |
| Fresh Git export, no secret.key/credentials/private datasets | **269 passed**, 44.09 s; source `fe0ec307db69ec8a4fc41a4d20b4498a57cf1a5a` |
| `python scripts/audit_data_security.py` | **PASS**: Git/public data, local storage boundaries and full private workbook |
| `python scripts/privacy_audit.py` | **PASS**, 139 local files checked, synthetic canary passed |
| `python scripts/audit_sheets_privacy.py --verify` | **PASS**, zero credential findings; approved B data allowed |
| Reachable-history audit | **WARNING**: two documented historical artifacts; zero detected credentials |
| Exact canonical comparison | **PASS**, all 114,869 rows and checksum equal |
| `git diff --check` | **PASS** |

The clean-export check uncovered automatic newline conversion of two byte-sealed public integrity reports; `.gitattributes` now preserves their exact bytes without changing report content or release checksums. Tests use synthetic temporal observations and injected keys; no production T20 ingestion or publication ran. Native formatting was read back through Sheets API. Google-rendered browser inspection was unavailable because the in-app browser required sign-in; no private workbook export was created for visual inspection.

## Commits pushed to main

| Commit | Milestone |
|---|---|
| `d0a7cba1304435870fe63dea8f9d1b5b3443e2d4` | Define single-sheet private data plane |
| `104f4f978c5d3544d7d5a0cf13ed296b37236ea7` | Restore historical viewer index and archive |
| `7bf5ac0e979812d89f503012782ccf356e4c4436` | Remove private working files and enforce storage boundaries |
| `f52af54cd2971afa0239c0c1d524f3d521edc313` | Security regression tests and synthetic fixtures |
| `fe0ec307db69ec8a4fc41a4d20b4498a57cf1a5a` | Fresh-export byte reproducibility |

## T20 decision

**Do not resume T20 yet.** Recovery and migration are complete, but its production incremental commit/recovery protocol and normalized-table refresh still need adaptation to the private Sheet backend and end-to-end validation. The archive writer does not provide concurrent multi-editor transactions. Historical handle-to-ID matching also remains unresolved. This task deliberately did not start production collection, publish a release, or claim continuous-collection readiness.

Machine-readable evidence is under `docs/evidence/`: `data_security_final.json`, `git_head_final.json`, `git_history_final.json`, `private_sheet_audit.json`, `private_migration_validation.json`, `private_migration_cleanup.json`, `private_archive_extension.json`, `security_fresh_clone.json`, and the test logs. All contain only safe paths, counts, test results and digests.
