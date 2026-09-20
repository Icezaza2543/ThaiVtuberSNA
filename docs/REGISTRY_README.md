# ThaiVirtualCreatorRegistry

Evidence-backed registry of Thai-linked **public virtual personas** and their official platform accounts. This is not a census of private people.

## Start here

| Need | Read |
|---|---|
| Current data | [`data/registry.json`](data/registry.json) — the only source of truth |
| Current counts and exports | [`reports/current/`](reports/current/README.md) |
| Pending work | [`reviews/pending/`](reviews/pending/README.md) |
| Agent handoff | [`AGENTS.md`](AGENTS.md) |
| Where files belong | [`docs/data-layout.md`](docs/data-layout.md) |

## Creator-owned link mapping

YouTube → official X → creator hub or direct link → platform accounts → reviewed persona links.
Direct owner links are useful too; a creator does not need every platform or an X account.
Accounts, public personas, discovery leads and dated activity are separate concepts.
Matching names alone never establish ownership. See [review policy](docs/review.md).

Python 3.11+ stdlib supports the registry and offline reports. Browser stages need Playwright.

```sh
python -m registry validate
python scripts/maintenance/refresh_reports.py --as-of 2026-09-16
python -m registry queue --status pending --limit 50
python -m registry map-creators --help
```

Use the intended observation cutoff instead of the example date when refreshing reports.
`map-creators` is the pipeline entrypoint; Grok search results can be supplied externally.
Do not start paid API calls or new collection merely to refresh reports or tidy files.

## Review and apply

Pipeline `changes` proposals and classifier output are **not** directly applyable table payloads.
Review first, then apply a table-shaped change file:

```sh
python -m registry apply --file reviews/pending/CHANGE.json --dry-run
python -m registry apply --file reviews/pending/CHANGE.json
```

After successful apply, **move**, do not copy, the change file to `reviews/applied/`.
Keep unreviewed/deferred work in the pending index. Do not replay archived batches.

## Documentation

[Data model](docs/data-model.md) · [Taxonomy](docs/taxonomy.md) · [Provenance](docs/provenance.md) · [Pipeline](docs/data-pipeline.md) · [Architecture](docs/architecture.md) · [Analytics](docs/analytics.md)

Historical captures remain at their recorded paths. Archives preserve working history but are not current data.
Tests protect existing behavior; data-only work does not require new tests or throwaway scripts.
License: Internal Research / All Rights Reserved; see [LICENSE](LICENSE).

## Frontend preparation

See [Antigravity handoff](docs/frontend-handoff.md), [design direction](DESIGN.md)
and [installed skills](.agents/README.md). Generate the public projection with
`python scripts/maintenance/export_frontend.py`. Source belongs in `web/`;
Pages publication remains the next frontend build step.

## เกณฑ์ verified

มีเฉพาะ Twitch หรือ TikTok ก็ผ่าน review ได้ ไม่ต้องมี YouTube หรือบัญชีที่สอง
พิจารณาหลักฐาน virtual presentation, ความเกี่ยวข้องกับไทย และ ownership
จากบัญชีเจ้าตัว การ resolve บัญชีสำเร็จไม่เท่ากับยืนยัน virtual-creator scope
ดู [วิธี review](docs/review.md) และคิวอ่านอย่างเดียว:

```sh
python -m registry queue --kind account_scope --platform twitch
python -m registry queue --kind account_scope --platform tiktok
```
