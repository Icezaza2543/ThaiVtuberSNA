# Single-sheet data security and storage architecture

The sole authoritative private/control workbook is **ThaiVtuber_SNA**, ID
`1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE`. No second workbook is permitted.
This policy supersedes earlier “aggregates only” and “RAM-only HMAC” instructions.

| Classification | Content | Authorized durable location |
| --- | --- | --- |
| SECRET_CREDENTIAL | API keys, HMAC key, service-account private key, OAuth tokens, passwords | Local environment/encrypted storage or secret manager; never Git or Sheets |
| PRIVATE_DATA | Raw viewer IDs, names/URLs, deterministic viewer hashes, viewer-level presence and event history | Existing ThaiVtuber_SNA workbook only |
| PUBLIC_RESEARCH_DATA | Public VTuber/channel/video metadata, aggregate counts/networks/cohorts, methodology, non-secret fingerprints | Git, workbook, public research artifacts |

Raw identity → HMAC with the original verified key → private workbook → in-memory
canonical analytics → aggregate public output. Handles are not stable channel IDs;
unresolved historical handles retain a blank HMAC instead of inventing identity.
Unverified historical hashes and synthetic fixtures stay separate from canonical
identity. A fingerprint proves key continuity, not the provenance of every row.

Approved private tabs: ALL_COMMENTERS, VIEWER_INDEX, VIEWER_CHANNEL_PRESENCE,
VIEWER_ACTIVITY_SUMMARY, VIEWER_EVENT_ARCHIVE, PRIVATE_DATA_ARCHIVE and optional
REILIM_COMMENTERS_ARCHIVE. Metadata/control tabs: NETWORK_RESULT, VTUBERS, SYSTEM,
RECOVERY_METADATA, DATA_DICTIONARY, MIGRATION_AUDIT. No raw comment/chat text.

Anyone granted workbook access may potentially access private viewer tabs.
Hidden sheets and protected ranges prevent accidental edits; they do not provide
independent confidentiality. Access was checked before migration: owner plus one
service-account writer, with no anyone/domain grant. Recheck when sharing changes.

Recovery never restores the complete revision over the current workbook. Temporary
recovery staging is gitignored and removed only after verified Sheets readback.
Local private source files are likewise removed only after every source is preserved
in the private archive. Git history is documented, never rewritten automatically.

`purge_sheets_pii.py` is now a read-only policy-audit compatibility wrapper.
No approved private tab may be automatically deleted. Writes use RAW values,
bounded deterministic ranges and readback verification, never worksheet.clear().

T20 is held pending migration/security verification and an explicit subsequent
resume decision. This task must not run production T20 update or publish.

## Verified migration and analytical continuity

Revision 380 restored 38,240 original ALL_COMMENTERS rows into the current workbook without restoring other revision contents. Those rows contain 28,762 distinct handle URLs and 9,478 repeated URL rows. A handle is not an immutable raw UC channel ID: no historical raw IDs or HMACs were invented. The independent canonical population retains 79,718 original pseudonyms, yielding 108,480 VIEWER_INDEX entries across two explicitly unmatched groups.

The archive preserves 142,184 source rows, with path/table/row provenance including synthetic, worktree and unverified inputs. These source copies are not additive observations. Only the same explicitly selected production provenance paths feed canonical analytics. Complete Sheet readback produced exactly the same 114,869 sorted canonical records and checksum as the local baseline before cleanup. The verified working copies were then removed; Git history was not rewritten.

`storage/private_sheet_analytics.py` reads the archive into Arrow and an in-memory DuckDB connection with disk spill disabled. Production default canonical loaders use this interface. Public outputs remain aggregate tables. Local Parquet collectors and the old destructive crawlers are retired; explicit temporary directories remain available for synthetic offline tests. `PrivateSheetStore` validates the workbook identity and credentials, uses RAW values, verifies range readback, resumes identical writes and refuses conflicting or truncated table replacements. It does not promise transactions across concurrent Sheet editors.

T20 remains ON HOLD and has not been started. Resuming production collection requires adapting its incremental commit/recovery protocol and normalized-table refresh to the private Sheet backend, then validating those transitions. The migration and historical recovery do not establish continuous-ingestion correctness. The production T20 entry points reject update/publish during this hold.

The original key fingerprint and `AGENCY_ISLAND_COORDINATES` digest are unchanged. Public evidence lives under `docs/evidence/`; those files contain counts, paths and digests only. The source archive is solely in the existing workbook. Test fixtures use synthetic identities and an injected test key, never the owner's real data.
