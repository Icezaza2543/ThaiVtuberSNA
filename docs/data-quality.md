# Data Quality & Freshness Monitoring

## Overview

The data quality and freshness report (`reports/current/data-quality.json` and `.csv`) audits the completeness of the registry, highlights unresolved backlog items for human review, and tracks evidence observation ages.

Generating the data-quality report is strictly read-only and **never mutates** the canonical registry database (`data/registry.json`).

## Key Semantics

### 1. Evidence Freshness vs. Creator Activity
Old evidence means the registry has not recently re-observed the claim; it does **not** prove the claim is no longer true or that the creator is inactive.

Freshness buckets:
- `0_30_days`
- `31_90_days`
- `91_180_days`
- `181_365_days`
- `over_365_days`
- `unknown`

These buckets measure the elapsed time since the evidence's `observed_at` timestamp.

### 2. Shared Accounts
An account associated with multiple personas is **not** automatically an error or duplicate. Examples include shared agency channels, group stream channels, or shared donation platforms (e.g. TipMe, EasyDonate).
In the quality report, these are explicitly categorized as:
```text
shared_account_review_context
```

### 3. Identity & Ownership Backlog
The report categorizes unresolved items requiring human attention:
- **Verified Personas with 0 Verified Accounts**: Highlights personas awaiting verified first-party account links.
- **Needs Evidence Account Links**: Links currently retained as `needs_evidence` (e.g. HoloList or secondary directory claims awaiting first-party proof).
- **Unresolved Candidates**: Candidates with pending handle resolution (missing YouTube Channel ID, Twitch numeric user ID, or TikTok numeric web_user_id).
- **Unverified Lifecycle Claims**: Graduation or debut claims from secondary sources that have not yet been backed by first-party statements.

## Commands

Generate via the registry CLI:
```bash
python -m registry quality --as-of YYYY-MM-DD
```

Generate via the maintenance report refresh script:
```bash
python scripts/maintenance/refresh_reports.py --as-of YYYY-MM-DD
```
