# Discovery saturation baseline — 2026-09-19

This report measures **retrospective novelty of recorded discovery observations**.
It does not claim that the registry is a census of all Thai virtual creators.

## Scope

- Repository HEAD before this report: `5d356aaf77428f7678d9304d07a3db0ad760567c`
- Discovery files present: batches 1–277.
- Quantitative sample used here: batches **182–277** (96 batches).
- Sample size: **647 recorded rows**.
- URL identity proxy: lowercase URL with trailing slash removed.
- Name proxy: Unicode NFKC + case-folded alphanumeric display name.

Important limitation: historical manual batches record accepted discovery observations, not every
search attempt that was rejected as already known, irrelevant, non-Thai, or non-virtual. Therefore
this is a **recorded-observation novelty test**, not a full search-attempt capture–recapture estimate.
Because the comparison starts at batch 182, duplicates that occurred only in batches 1–181 are not
counted as repeats here. Novelty rates below are therefore an **upper bound**.

## Rolling retrospective novelty

| Batches | Recorded rows | First-seen URL proxies | URL novelty / rows | First-seen name proxies | Name novelty / rows | Dominant platforms |
|---|---:|---:|---:|---:|---:|---|
| 182–193 | 91 | 91 | 100.0% | 68 | 74.7% | website 33, X 29, YouTube 14 |
| 194–205 | 110 | 110 | 100.0% | 43 | 39.1% | YouTube 35, X 25, website 23, Facebook 15 |
| 206–217 | 107 | 107 | 100.0% | 66 | 61.7% | X 36, website 34, YouTube 12 |
| 218–229 | 87 | 74 | 85.1% | 64 | 73.6% | X 32, website 31, YouTube 15 |
| 230–241 | 64 | 60 | 93.8% | 57 | 89.1% | X 35, website 23, YouTube 6 |
| 242–253 | 60 | 59 | 98.3% | 49 | 81.7% | X 37, website 15 |
| 254–265 | 60 | 60 | 100.0% | 55 | 91.7% | website 35, X 23 |
| 266–277 | 68 | 33 | **48.5%** | 26 | **38.2%** | **X 68 / 68 (100%)** |

Across batches 182–277:

- 647 recorded rows
- 594 distinct URL proxies
- 428 distinct normalized name proxies
- The sharp novelty collapse is concentrated in the final all-X block, not across all platforms.

Name-proxy novelty must not be interpreted as verified-persona novelty. A creator can have multiple
accounts, aliases or renamed personas, and two unrelated creators can share a display name.

## Batches 272–277: first-seen yield collapse

Within the 182–277 comparison window, the six newest batches contain 36 X observations but only
**18 first-seen URL proxies**. The other 18 rows point to URLs that had already appeared earlier in
the sampled discovery history.

| Batch | Rows | First-seen URLs | Previously seen URLs |
|---|---:|---:|---:|
| 272 | 6 | 6 | 0 |
| 273 | 6 | 5 | 1 |
| 274 | 6 | 3 | 3 |
| 275 | 6 | 2 | 4 |
| 276 | 6 | 2 | 4 |
| 277 | 6 | **0** | **6** |
| **Total** | **36** | **18** | **18** |

This does **not** mean the duplicated observations are corrupt. The discovery architecture explicitly
preserves repeated observations/provenance. It means they must not be described as “36 new leads”.

## Interpretation

### Current generic-X discovery is locally saturated

For the current X-heavy/manual hashtag/profile source family, novelty has fallen sharply. Batch 277
produced no first-seen URL within this 96-batch comparison, and the 266–277 block is only 48.5%
first-seen URL observations.

This is strong evidence to **stop using generic X/#VTuberTH discovery as the default next source**.

### The Thai virtual-creator ecosystem is not shown to be saturated

The same conclusion cannot be extended to Thailand as a whole because the latest block is 100% X.
The repository already documents distinct discovery surfaces for YouTube, Twitch, TikTok, Facebook,
Instagram, agency/event rosters, creator hubs and personal websites. Those sources have different
coverage biases.

Current public source pools worth probing separately include:

- Thai VTubers Directory: https://vtuber.chuysan.com/
- Hub VTuber Thai / agency rosters: https://vtuberthai.com/
- CASFEST 2026 creator roster: https://2026.casfest.in.th/creators
- 2026 event lineups such as VERZO, which explicitly listed Thai creators and VTubers.

These are discovery sources only; a listing does not by itself verify persona scope or account
ownership.

## Operational saturation test for future collection

Future discovery should record **attempt-level yield**, not just accepted observations. For every
(platform, query/source, run), retain at least:

- `raw_hits`
- `known_account_or_candidate`
- `new_candidate`
- `rejected_out_of_scope`
- `unresolved`
- `stable_id_resolved`
- `verified_after_review`

Then evaluate each source family independently.

Suggested operational rule for a source family to be called **locally saturated**:

1. At least three independent runs on different queries/times.
2. Each run has a meaningful denominator (preferably >= 50 raw hits when the surface can provide it).
3. New-candidate yield remains below about 5–10% in all three runs.
4. No obvious untested sub-source remains (agency roster, event roster, language variant, platform
   category or link-hub path).

Do not call the overall Thai ecosystem saturated until this condition has been tested separately
across at least:

1. X / public social search
2. YouTube
3. Twitch
4. TikTok
5. Facebook / Instagram public creator surfaces
6. Agency, event and community rosters
7. Creator hubs / owner cross-links

A capture–recapture estimate may be added later by comparing independent source families, but the
independence assumption is weak because Thai VTuber directories, events and social profiles often
reference one another. Treat such an estimate as a range, not a census.

## Immediate collection decision

For the next discovery cycle, rotate away from generic X and spend one batch-equivalent probe on
each under-sampled source family. Keep repeated observations for provenance, but report separately:

- observations
- first-seen account URLs
- new candidates after entity dedupe
- verified personas after review

This distinction prevents observation count from being mistaken for creator count or discovery yield.
