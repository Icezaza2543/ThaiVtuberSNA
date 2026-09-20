# Pending work

| File | Meaning |
|---|---|
| `creator-link-map-2026-09-16.json` | Full Stage 4 classification snapshot, including already-applied accounts. Its 1,913 rows are not 1,913 unfinished actions. Compare with the current registry. |
| `legacy-creator-proposals-2026-09-16.json` | Consolidated original pass1/merged proposals. Exact duplicate rows were removed; unresolved rows and evidence were retained without re-verification. |
| `discovery-2026-09-15-high-value.json` | Historical discovery proposals retained for review; no automatic apply or claim of completion. |

The exact duplicate first-party payload now exists only in `../applied/`.
These three files are tracked workflow state, not temporary files. The two legacy proposal snapshots were archived with their original metadata; the consolidated queue preserves every distinct proposed change.
Do not feed a `changes` classifier directly to `registry apply`. For actual pending table payloads, dry-run then apply, and move the successful payload into `../applied/`.
