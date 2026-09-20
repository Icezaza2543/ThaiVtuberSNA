"""registry/pipeline — Creator-Owned Link Pipeline.

Pipeline stages (run via `python -m registry map-creators`):

  Stage 1: youtube-to-x
    Input:  All YouTube accounts in data/registry.json
    Source: existing intake JSONL / YouTube About first (free), then optional X Search
    Output: intake/consolidated/youtube-to-x-<date>.jsonl

  Stage 2: x-to-hub
    Input:  youtube-to-x-*.jsonl (high/medium X candidates)
    Tool:   Playwright browser fetch of X profile page
    Output: intake/consolidated/x-profile-links-<date>.jsonl

  Stage 3: hub-to-platforms
    Input:  x-profile-links-*.jsonl (hub URLs from X profiles)
    Tool:   Playwright or stdlib fetch of hub page (Linktree/Carrd/etc.)
    Output: intake/consolidated/creator-platform-links-<date>.jsonl

  Stage 4: build-review
    Input:  creator-platform-links-*.jsonl
    Tool:   Stable ID resolution (TikTok web_user_id, Twitch user_id, YT channel_id)
    Output: reviews/pending/creator-link-map-<date>.json
"""
