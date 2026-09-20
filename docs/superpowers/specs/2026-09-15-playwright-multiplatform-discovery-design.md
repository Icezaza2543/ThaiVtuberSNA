# Multi-platform Playwright Discovery Design

Date: 2026-09-15

## Goal

Add a local, token-free discovery command that opens Chromium with Playwright and searches public web surfaces across multiple creator platforms. The command must collect public creator/account leads, normalize them into the existing registry discovery model, preserve source provenance, deduplicate safely, and leave identity/persona verification to human review.

The intended default command is:

```bash
python -m registry discover-all
```

A headless mode is also supported:

```bash
python -m registry discover-all --headless
```

The crawler must not use an LLM, must not bypass CAPTCHAs or login walls, and must not auto-verify creator identity.

## Scope

### Initial platform adapters

The first implementation supports these discovery targets:

- YouTube
- Twitch
- TikTok
- Facebook
- Instagram
- X / Twitter
- Kick
- GankNow
- Bilibili
- Niconico

The adapter architecture must allow additional platforms without changing the orchestrator contract.

### Discovery-support surfaces

These are not necessarily first-class creator-account platforms, but can be used as public evidence and cross-link hubs:

- Carrd
- Linktree
- lit.link
- personal websites
- agency websites
- Ko-fi
- Patreon
- VGen

A discovered URL on one of these surfaces may yield additional platform links but must not automatically establish that two accounts belong to the same persona.

## Design principles

1. **Browser-first discovery**: use Playwright against public pages so discovery works without requiring private API credentials.
2. **Official API optional**: existing Twitch Helix support remains available as an enrichment/discovery path when credentials exist.
3. **No LLM dependency**: keyword expansion, extraction, scoring, normalization, and deduplication are deterministic local code.
4. **Adapter isolation**: each platform owns selectors, navigation, extraction, pagination/scroll behavior, and platform-specific failure handling.
5. **Evidence before identity**: discovery creates `candidates`, `discovery_hits`, and evidence. It does not create verified persona links.
6. **Stable IDs preferred**: when a platform exposes a reliable public stable ID, store it. Otherwise retain URL/handle candidates without pretending a handle is stable identity.
7. **Failure isolation**: one platform may fail, rate-limit, require login, or change selectors without aborting the entire run.
8. **Public data only**: do not collect private profiles, chats, follower lists, viewer identities, session secrets, or private person identity information.
9. **No anti-bot bypass**: CAPTCHA, challenge pages, rate limits, and login requirements become explicit stop states.

## Proposed package layout

```text
registry/
  discovery/
    __init__.py
    orchestrator.py
    browser.py
    models.py
    queries.py
    normalize.py
    dedupe.py
    crosslinks.py
    adapters/
      __init__.py
      base.py
      youtube.py
      twitch.py
      tiktok.py
      facebook.py
      instagram.py
      x.py
      kick.py
      ganknow.py
      bilibili.py
      niconico.py
```

Existing `registry.operations.twitch_discover` remains supported for API-based Twitch discovery. The new package is responsible for browser-driven multi-platform discovery.

## Adapter contract

Each adapter implements one public discovery interface conceptually equivalent to:

```python
class PlatformAdapter:
    platform: str

    async def discover(self, context, query, limits) -> DiscoveryBatch:
        ...
```

An adapter returns normalized `DiscoveryLead` objects instead of writing the registry directly.

Each lead contains at minimum:

- platform
- name
- url
- handle when available
- platform_id when reliably observable
- id_namespace when a platform_id is present
- source_url
- query
- observed_at
- source_kind
- metadata used only during deterministic scoring/extraction

The orchestrator owns persistence so platform code cannot bypass registry validation.

## Query strategy

The crawler runs a bounded query set rather than attempting an unbounded platform census.

Default Thai/virtual-creator discovery terms include:

- VTuberTH
- ThaiVTuber
- VTuber Thailand
- วีทูบเบอร์ไทย
- วีทูปเบอร์
- วีไทย
- PNGTuberTH
- VSingerTH
- Virtual Idol Thailand
- เดบิวต์ VTuber
- เปิดตัวโมเดล

The list lives in `registry/discovery/queries.py` and can be replaced or extended from the CLI.

### Registry expansion queries

Existing public handles/names may also seed platform searches. A name or handle match only creates a lead; it never auto-links identities.

### Cross-link expansion

For a discovered public profile or link hub, the crawler extracts outbound links to known creator platforms. Those links generate additional leads with provenance pointing back to the source page.

Cross-links increase confidence for review but do not create `account_links` automatically.

## Browser lifecycle

`browser.py` owns Playwright startup and shared browser state.

Default behavior:

- Chromium
- headed mode
- one browser process
- isolated context for the discovery run
- conservative navigation timeout
- bounded scrolling/pagination
- deterministic sleeps/backoff where necessary
- no stealth plugins or CAPTCHA bypass tooling

Optional CLI flags:

```text
--headless
--platform <name>          repeatable
--query <text>             repeatable
--max-results <n>
--max-pages <n>
--timeout <seconds>
--profile-dir <path>       optional persistent local browser profile
```

`--profile-dir` allows the user to reuse their own local authenticated browser state where a public search surface works better while logged in. Authentication data remains local and is never written into registry JSON, logs, reports, or commits.

## Run orchestration

`discover-all` performs these stages:

1. Load the registry and validate it.
2. Build the selected adapter list.
3. Start one Playwright browser/context.
4. Run bounded queries per adapter.
5. Record adapter status independently.
6. Normalize returned leads.
7. Deduplicate within the run.
8. Persist one or more `discovery_runs`, evidence rows, candidates, and discovery hits.
9. Revalidate the registry.
10. Print a machine-readable JSON summary.

A failure from one adapter does not roll back successful adapters unless registry validation itself fails.

## Data model changes

The current SQL enums hard-code four platforms and a small discovery-method/stop-reason set. The implementation will extend the existing schema rather than introduce a second discovery database.

### Platforms

Add:

- instagram
- x
- kick
- ganknow
- bilibili
- niconico
- carrd
- linktree
- litlink
- kofi
- patreon
- vgen
- website

YouTube, Twitch, TikTok, and Facebook remain unchanged.

The Python `PLATFORMS` constant and URL-domain validation must match the SQL contract. Named platforms use canonical-domain validation; `platform = website` is the explicit generic case and accepts any public HTTPS URL through `public_url()` rather than a fixed-domain check.

### Discovery methods

Add browser-oriented methods such as:

- `playwright_search`
- `crosslink_crawl`

Existing methods remain valid for backwards compatibility.

### Stop reasons

Extend stop reasons to represent browser outcomes without pretending every run completed normally:

- `completed`
- `partial`
- `login_required`
- `captcha`
- `rate_limited`
- `selector_changed`
- `timeout`
- `blocked`

Existing stop reasons remain supported.

## URL and identity normalization

Normalization is platform-specific but follows common rules:

- force HTTPS where the platform canonical form is HTTPS
- strip tracking/query fragments when not identity-bearing
- normalize common host aliases
- normalize handle prefixes only for comparison, not identity certification
- reject malformed or cross-domain URLs for named first-class platform candidates
- allow arbitrary public HTTPS domains only for the explicit `website` platform

`platform_id` is only stored when the adapter can extract a documented or clearly stable public identifier. Otherwise the lead stays URL-based.

No cross-platform identity merge occurs from matching display names or handles.

## Deterministic scoring

A local score may prioritize review order, but cannot change `review_status` to verified.

Example signals:

- official cross-link present
- VTuber/VSinger/PNGTuber tag or keyword
- Thai-language signal
- known registry handle match
- display-name similarity
- multiple independent discovery hits

The score is advisory and need not be persisted in v1 unless a schema-safe location is added later. The first implementation can use it only for ordering output to avoid unnecessary schema expansion.

## GankNow behavior

GankNow is treated as both:

1. a first-class platform candidate (`platform = ganknow`), and
2. a discovery source that may expose links to YouTube, Twitch, TikTok, X, Instagram, and other public creator pages.

The crawler must use public web pages and links. It must not depend on undocumented/private internal APIs.

## Platform-specific expectations

### YouTube

Use public search/channel result pages and channel pages. Extract canonical channel URLs/handles where available. Do not rely on comments or viewer data.

### Twitch

Browser discovery is available for search and public channel pages. Existing Helix discovery remains optional for users with credentials.

### TikTok

Use public search/profile pages where reachable. Treat challenge/CAPTCHA/login states as explicit stop reasons. Do not assume access to TikTok Research API.

### Facebook

Search only public Pages/public creator surfaces. Do not crawl private profiles or group membership.

### Instagram

Search/discover public profile links where reachable. Login-required behavior is reported and skipped rather than bypassed.

### X / Twitter

Search public results/profiles where reachable. Login or challenge walls produce an adapter stop state.

### Kick

Search public channel/category surfaces and extract public creator channel URLs.

### Bilibili / Niconico

Use public search/profile surfaces. These are useful for Thai-linked creators operating outside the dominant English-language platforms, but every candidate still requires review for Thai relation.

## Cross-link crawler

`crosslinks.py` inspects only public pages already discovered or explicitly supplied as sources.

It extracts links for domains known by the platform registry. It does not recursively crawl the open web without bounds.

Default limits:

- one hop from a creator profile/link hub
- bounded number of outbound links per page
- no same-site recursive site crawl unless an adapter explicitly needs it

This avoids accidental broad web crawling.

## Deduplication

Deduplication occurs at two levels.

### Within a run

Prefer keys in this order:

1. `(platform, id_namespace, platform_id)` when stable ID exists
2. canonicalized platform URL

### Against the registry

Use the existing `discover_candidate` semantics:

- stable ID can map to an already-known account
- URL-only/handle-only leads remain candidates
- repeated discoveries create additional `discovery_hits` so provenance is preserved

Matching handles across platforms are never merged.

## Failure handling

Adapters map recognizable states to explicit outcomes:

- completed
- partial
- login_required
- captcha
- rate_limited
- selector_changed
- timeout
- blocked

Unexpected adapter exceptions are contained, summarized, and do not expose cookies, tokens, authorization headers, or browser storage.

Console output may include platform, query, counts, and stop reason. It must not dump page HTML or authenticated state by default.

## Persistence semantics

Each adapter/query execution is represented as a discovery run or a bounded group of runs, so provenance remains attributable to a platform/method/query/time.

Every persisted lead receives evidence identifying the source URL and observation time.

The implementation must continue to use the registry's atomic edit/validation path. A malformed row must never leave a partially written registry JSON file.

## CLI output

A successful run prints JSON similar to:

```json
{
  "platforms": {
    "youtube": {"status": "completed", "hits": 120},
    "tiktok": {"status": "captcha", "hits": 35},
    "ganknow": {"status": "completed", "hits": 80}
  },
  "raw_hits": 235,
  "deduplicated_leads": 170,
  "new_candidates": 65,
  "known_accounts": 105
}
```

Exact counts depend on live platform results and are not part of tests.

## Dependency strategy

The current project has no runtime dependencies. Preserve the lightweight core by adding Playwright as an optional extra:

```toml
[project.optional-dependencies]
discovery = ["playwright>=1.55,<2"]
```

Installation:

```bash
pip install -e ".[discovery]"
playwright install chromium
```

Core commands such as `validate`, `report`, `candidate`, and `export` must continue to import and run without Playwright installed.

## Testing strategy

No live website is required for unit tests.

### Unit tests

Test:

- platform URL normalization
- cross-link extraction
- deterministic deduplication
- platform enum/schema acceptance
- discovery method and stop-reason acceptance
- adapter result normalization
- orchestrator partial failure behavior
- registry persistence and provenance
- CLI argument parsing
- Playwright-not-installed error message for `discover-all`

### Adapter tests

Adapters use synthetic HTML fixtures or mocked Playwright page objects. Tests verify selectors/extraction behavior without making network requests.

### Existing tests

All existing registry tests must remain green, including Twitch API discovery, atomic edits, evidence rules, temporal reporting, and export checks.

### Optional manual smoke test

A developer may run a small live crawl with one query and a low result limit. Live crawling is not part of CI because search results and anti-bot behavior are nondeterministic.

## README/documentation updates

Update:

- `README.md`: installation and `discover-all` examples
- `docs/discovery.md`: browser discovery model, supported platforms, limitations, CAPTCHA/login behavior, and provenance semantics
- `AGENTS.md`: keep rule that software changes do not imply live data collection; live crawl occurs only when the user explicitly runs it

## Security and privacy

- never commit browser profile data
- never log cookies, tokens, localStorage, authorization headers, or passwords
- never store chats, follower lists, viewers, or private identities
- never bypass CAPTCHA or platform access controls
- never infer or link undisclosed real-world identities
- keep persona/account linking in the reviewed evidence workflow

`.gitignore` must cover local Playwright/browser profile directories if the implementation provides a default local path.

## Definition of done

The feature is complete when:

1. `python -m registry discover-all` launches Chromium and executes selected adapters.
2. `--headless` works.
3. At least the initial adapter set is registered and isolated behind the common interface.
4. Browser discovery does not require LLM/API tokens.
5. Successful leads persist through the existing candidate/evidence/discovery-hit workflow.
6. Cross-links can create additional platform candidates without auto-linking personas.
7. One adapter failure does not abort the rest of the discovery run.
8. CAPTCHA/login/rate-limit/selector-change states are reported explicitly.
9. Core registry commands still work without Playwright installed.
10. Existing tests plus new deterministic tests pass.
11. Documentation accurately describes capabilities and limitations.
