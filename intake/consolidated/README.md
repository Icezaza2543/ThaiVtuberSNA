# intake/consolidated/

Consolidated output files from the creator-link mapping pipeline.

Each pipeline run writes one JSONL file per stage here, named with the run date.

## File types

| Pattern | Stage | Contents |
|---|---|---|
| `youtube-to-x-<date>.jsonl` | Stage 1 | YouTube account → verified X/Twitter handle + evidence chain |
| `x-profile-links-<date>.jsonl` | Stage 2 | X profile → creator hub URLs and direct platform links |
| `creator-platform-links-<date>.jsonl` | Stage 3 | Creator hub → all extracted platform account URLs |

## Schema

Each record preserves a complete evidence chain:
```json
{
  "youtube_account_id": "...",
  "youtube_channel_id": "UC...",
  "x_url": "https://x.com/...",
  "hub_url": "https://linktr.ee/...",
  "target_platform": "twitch",
  "target_url": "https://www.twitch.tv/...",
  "evidence_chain": [...],
  "observed_at": "2026-..."
}
```
