# Historical account eligibility filter

This export covers the legacy 1,370-channel registry and all 884 discovery
accounts recovered from commit `4a1db6212de59d497d2a998baff29bd2c436a55a`.
The 884 entries are **402 YouTube accounts and 482 accounts on other platforms**,
not 884 additional YouTube channels. It also includes all canonical accounts
from that master snapshot and the later `97116ca274a6940ba3919c13c8e7fd5778322cca`
snapshot, plus the legacy discovery CSVs and excluded-channel list. Source
revisions, paths, sections, exact blob SHA-256 hashes and row counts are in
`historical_account_eligibility_v1.json`. Each output record points back to its
original source rows. No source or persona record was changed.

## Files to use

- `strict_virtual_channels.csv`: 274 YouTube channels that pass the existing
  reviewed eligibility filter. Use this file for the filtered historical set.
- `held_or_excluded.csv`: every input account that does not pass. HOLD means
  insufficient reviewed evidence, **not a finding that the creator is nonvirtual**.
- `all_accounts.csv`: the complete filter results.
- `historical_account_eligibility_v1.json`: provenance and per-record decisions.

There are 1,409 distinct resolved YouTube channel IDs: 274 STRICT_VIRTUAL,
1,133 HOLD_NEEDS_CHANNEL_REVIEW and 2 EXCLUDE_NON_PERSONA_ACCOUNT. Another 4,168
records have no resolved YouTube channel ID (including other platforms). All
remain on HOLD. These 4,168 records are **not** a unique-channel or persona count:
only identical original account/candidate IDs are deduplicated. Names, handles,
visual identity matches, legacy CONFIRMED labels and Thai-confidence scores
never grant virtual eligibility or merge identities. Legacy exclusions based
on nationality do not establish nonvirtual status either.

## Limits

This is a fail-closed filtering pass using existing channel eligibility reviews,
not a new public-evidence review of every historical account. The 45 accepted
channel decisions are unchanged. Other historical accounts need further
channel/platform evidence review before inclusion. No claim is made that all
HOLD accounts are non-VTubers or that the remaining review is complete.
The existing 229 strict decisions are inherited from the existing reviewed
eligibility layer; this pass does not independently reconfirm their evidence.

The Surface cohort remains 274 channels / 83,129 videos. Network and clean
audience semantics are unchanged. The filter is an explicit standalone export;
it does not rewrite the live registry, worker, workbook or any frozen release.

## Rebuild

With the historical objects available (the snapshots are on
`origin/temp/visual-identity-review`), run:

```powershell
python scripts/build_historical_eligibility.py
python -m pytest tests/test_historical_eligibility.py -q
```

Source review: `docs/evidence/expanded-v1/public-review-2026-09-10/channel_eligibility_v1.json`.
No YouTube Data API or public network calls are made by this builder.
