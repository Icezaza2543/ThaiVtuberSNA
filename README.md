<div align="center">

# ✦ ThaiVtuberSNA ✦

### Network & Analytics Engine for the Thai VTuber ecosystem

*observe • connect • analyze • export*

[![Python](https://img.shields.io/badge/Python-3.11%2B-7aa2f7?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-SNA_Engine-f4d35e?style=for-the-badge)](https://duckdb.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/Icezaza2543/ThaiVtuberSNA/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/Icezaza2543/ThaiVtuberSNA/actions)
[![Project](https://img.shields.io/badge/Project-ThaiVtuberMaster-f5a9d0?style=for-the-badge)](https://github.com/Icezaza2543/ThaiVtuberMaster)

<br>

**ThaiVtuberSNA** is the downstream network and analytics engine of the Thai VTuber data stack.

Canonical identity state lives in **ThaiVtuber_DATA**. New public-account discovery and
candidate enrichment live in [**ThaiVtuberFinder**](https://github.com/Icezaza2543/ThaiVtuberFinder).
SNA consumes reviewed identities, processes audience/network observations, and exports
derived datasets for [**ThaiVtuberMaster**](https://github.com/Icezaza2543/ThaiVtuberMaster).

</div>

---

## ✧ System architecture

```mermaid
flowchart LR
    A["Public / Official Sources"] --> B["ThaiVtuberFinder"]
    B --> C["FINDER_INBOX"]
    C --> D["Human Review"]
    D --> E["ThaiVtuber_DATA<br/>Canonical Source of Truth"]
    E --> F["ThaiVtuberSNA<br/>Network + Analytics"]
    E --> G["ThaiVtuberMaster<br/>Registry Views"]
    F --> G
```

> **Finder discovers. Humans review. ThaiVtuber_DATA decides. SNA analyzes. Master presents.**

| Component | Responsibility |
|---|---|
| [ThaiVtuberFinder](https://github.com/Icezaza2543/ThaiVtuberFinder) | Discover/enrich public accounts and submit review candidates |
| **ThaiVtuber_DATA** | Canonical personas, accounts, account links, organizations, affiliations, lifecycle state, reviewed decisions |
| **ThaiVtuberSNA** | Audience/network observations, graph computation, derived metrics, reproducible exports |
| [ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster) | Public-facing registry and analytics explorer |

---

## 🌙 What belongs here?

| Module | Responsibility |
|---|---|
| **Canonical input** | Consume reviewed persona/account/link state from ThaiVtuber_DATA or a validated canonical snapshot |
| **Observation collection** | Gather analytical/audience observations for already-known reviewed identities |
| **SNA** | Calculate audience overlap and network-derived metrics |
| **Analytics** | Produce dated, reproducible derived datasets |
| **Export** | Deliver clean datasets to ThaiVtuberMaster and research workflows |
| **Worker** | Run analytical pipelines continuously with checkpoints/backoff where applicable |

New creator discovery and candidate review intake should go to **ThaiVtuberFinder**, not be
implemented as a second discovery system here.

Legacy discovery/reconciliation scripts may remain for reproducibility and migration history,
but they are not the authoritative path for new canonical identities.

---

## 💫 Shared identity and evidence rules

- **ThaiVtuber_DATA is the source of truth.**
- Public personas/accounts are modeled separately from private people.
- Identity links require reviewed evidence.
- No automatic persona merging from name, voice, artwork, handle similarity, or presumed operator.
- New persona/model/re-debut records remain separate until a reviewed canonical decision says otherwise.
- Organization/group accounts remain separate from individual personas.
- Audience identities remain privacy-preserving.
- Analytical observations do not silently rewrite canonical persona/account ownership.
- Processing is reproducible and idempotent where possible.

---

## 🪄 Quick start

```bash
pip install -r requirements.txt

python migrate.py
python -m thaivtubersna validate
python -m thaivtubersna run
```

Continuous worker:

```bash
python -m thaivtubersna worker
```

Tests:

```bash
python -m pytest tests/ -v
```

---

## 📦 Derived exports

The analytical pipeline currently produces datasets such as:

```text
VTUBERS.csv
NETWORK_RESULT.csv
TIKTOK_VERIFIED.csv
TWITCH_VERIFIED.csv
ANALYTICS_METRICS.csv
```

These are downstream delivery/analysis artifacts. They do not replace ThaiVtuber_DATA as
canonical identity state.

---

## 🔄 Finder → Canonical → SNA handoff

The intended flow is:

```text
ThaiVtuberFinder
    ↓
FINDER_INBOX / relation proposals
    ↓
Human review
    ↓
ThaiVtuber_DATA
    ↓
validated canonical snapshot
    ↓
ThaiVtuberSNA
    ↓
network + analytics exports
    ↓
ThaiVtuberMaster
```

SNA must not treat an unreviewed Finder candidate as a canonical persona.

---

## 🧭 Responsibility boundary

Use this repository for:

- audience/network collection for reviewed accounts
- DuckDB/network computation
- analytical metrics and research outputs
- export preparation
- migration/reconciliation reproducibility

Do **not** use it as the primary home for:

- broad public-account discovery
- Finder inbox synchronization
- automatic cross-platform identity linking
- canonical persona promotion
- public website presentation

Those responsibilities belong to Finder, ThaiVtuber_DATA, and Master respectively.

---

## 📚 Related projects

- [ThaiVtuberFinder](https://github.com/Icezaza2543/ThaiVtuberFinder) — discovery, enrichment, provenance, review candidates
- **ThaiVtuber_DATA** — canonical source of truth
- [ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster) — public registry and analytics explorer

---

<div align="center">

### ✦ Finder discovers. Data decides. SNA analyzes. Master presents. ✦

*Built for a cleaner, traceable view of the Thai VTuber ecosystem.*

**₊˚⊹♡ ThaiVtuberSNA ♡⊹˚₊**

</div>
