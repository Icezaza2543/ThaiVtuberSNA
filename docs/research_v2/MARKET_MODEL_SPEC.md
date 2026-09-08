# Thai VTuber Market Sizing Model Specification

> **Status**: FORMAL SPECIFICATION (Pre-Deployment)  
> **Authoritative Epistemic Assessment**: **`INSUFFICIENT_EVIDENCE` for a single authoritative market size number**.  
> **Rule**: Do NOT publish manufactured revenue totals as empirical facts. All scenario models must state assumptions explicitly.

---

## 1. The Market Sizing Challenge

Unlike publicly traded Japanese virtual entertainment agencies (e.g. ANYCOLOR / Nijisanji, COVER Corporation / Hololive) which disclose audited quarterly revenues, merchandise margins, and average spend per paying user (ARPPU), the Thai VTuber ecosystem operates almost entirely via **private corporate entities** (e.g. Algorhythm Project, Pixela Official, Polygon) and **independent creators**.

Consequently:
- Total merchandise unit sales are confidential.
- Channel membership counts are private creator dashboard data.
- Brand sponsorship contracts are bound by non-disclosure agreements (NDAs).
- Third-party scrapers (e.g. Playboard) capture only a fraction of public YouTube Super Chats and miss local direct gateways (e.g. PromptPay, Tipme, LINE Pay).

Therefore, any single headline market figure (e.g. "The Thai VTuber market is worth 500M THB") published without bounding assumptions is methodologically fraudulent.

---

## 2. Three-Tier Market Modeling Architecture

To navigate this limitation with scientific rigor, we define three explicit modeling tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: OBSERVED MONETIZATION FLOOR (Empirical Minimum)                    │
│ Status: PARTIALLY VERIFIED (Sum of verified public price signals)           │
│ Scope: ~12M – 20M THB (Multi-year aggregated visible cash flow signals)     │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: ESTIMATED MARKET RANGE (Economic Sizing Framework)                 │
│ Status: INSUFFICIENT_EVIDENCE (Requires missing commercial data)           │
│ Scope: Structural formula defined; awaiting authenticated agency metrics.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: MARKET POTENTIAL SCENARIOS (Sensitivity Bounds)                     │
│ Status: DOCUMENTED BENCHMARK (Conservative / Base / Upside)                 │
│ Scope: Bounded by active interacting accounts × conversion × ARPU.          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tier 1: Observed Monetization Floor

The **Observed Monetization Floor** calculates the absolute observable cash flow lower bound from public records in `data/market/market_evidence.parquet`:

$$\text{Floor}_{\text{observed}} = \sum \text{SuperChat}_{\text{observed}} + \sum \text{Ticketing}_{\text{verified}} + \sum \text{Crowdfunding}_{\text{public}}$$

### Current Observed Minimum (2020–2025 Aggregate Sample):
1. **Public Super Chat Signals (Top 10 Channels)**: $\approx 6.8\text{M THB}$ (gross tracked by Playboard index).
2. **Offline Concert & Event Ticket Sales**: $\approx 4.5\text{M THB}$ (calculated from verified sold-out hall capacities $\times$ face value ticket tiers at 890–3,200 THB).
3. **Public Crowdfunding Campaigns**: $\approx 1.2\text{M THB}$ (completed public 3D and project campaigns).
- **Total Observed Multi-Year Cash Floor**: **$\approx 12.5\text{M THB}$**.

*Caveat*: This is an empirical floor, NOT an annual run-rate. It represents visible multi-year historical signals.

---

## 4. Tier 2: Structural Market Model Specification

When private data plane partnerships or agency survey disclosures become available, the industry sizing model will follow this additive formula across the 100 core cohort channels:

$$\text{Market Size}_{\text{annual}} = \sum_{c=1}^{N} \left( \text{SC}_c + \text{MEM}_c + \text{MERCH}_c + \text{TKT}_c + \text{SPON}_c \right)$$

Where:
- $\text{SC}_c$: Net Super Chat & direct tip revenue received by channel $c$.
- $\text{MEM}_c = \sum_{t \in \text{Tiers}} \left( \text{Price}_{c,t} \times \text{ActiveMembers}_{c,t} \times 12 \times (1 - \text{PlatformFee}) \right)$.
- $\text{MERCH}_c = \sum_{i \in \text{Items}} \left( \text{RetailPrice}_{c,i} \times \text{UnitsSold}_{c,i} \right)$.
- $\text{TKT}_c$: Net box office revenue from physical and digital paid concert streams.
- $\text{SPON}_c$: Total gross billings from commercial brand partnerships.

### Missing Parameter Audit:
| Parameter | Current Status | Required Source to Unlock |
|---|---|---|
| `ActiveMembers` | PRIVATE | YouTube Studio creator export or agency disclosure |
| `UnitsSold` | PRIVATE | E-commerce store backend reports (Shopee/Shopify/Booth) |
| `SPON Billings` | CONFIDENTIAL (NDA) | Agency commercial revenue audit |

Because these three parameters are currently unobserved in public data, **Tier 2 remains classified as `INSUFFICIENT_EVIDENCE`**.

---

## 5. Tier 3: Market Potential Sensitivity Scenarios

Using our verified canonical interaction account base as the empirical anchor, we model annual consumer direct spending scenarios using a standard conversion funnel:

$$\text{Annual Direct Consumer Revenue} = N_{\text{annual active}} \times \text{Payer Conversion Rate} \times \text{Annual Spend per Payer (ARPU)}$$

### Parameter Baseline:
- **Annual Active Interacting Accounts ($N_{\text{annual active}}$)**: $\approx 17,119$ accounts (observed in 2025 canonical events).

### Scenario Matrix:

| Scenario Tier | Payer Conversion Rate (%) | Estimated Paying Backers | Annual ARPU (THB) | Monthly Equivalent (THB/mo) | Estimated Annual Market (THB) |
|---|---|---|---|---|---|
| **Conservative** | `5.0%` | 856 | 1,200 | 100 | **1,027,200 THB** |
| **Base Case** | `10.0%` | 1,712 | 3,600 | 300 | **6,163,200 THB** |
| **Upside Case** | `18.0%` | 3,081 | 8,400 | 700 | **25,880,400 THB** |

### Scenario Justification:
- **Conservative (1.0M THB)**:
  - Assumes virtual livestream viewers behave like general YouTube viewers (low payer conversion $\sim 5\%$).
  - Spending is restricted to entry-level monthly memberships (50–100 THB/mo) with minimal merchandise uptake.
- **Base Case (6.2M THB)**:
  - Aligns with standard niche VTuber audience loyalty benchmarks (10% payer conversion).
  - Average payer maintains a mid-tier channel membership (150 THB/mo) and purchases 1–2 official goods or ticket items per year (~1,800 THB).
- **Upside Case (25.9M THB)**:
  - Fandom behavior mirrors Japanese virtual idol dedication (18% conversion).
  - Core "whales" and passionate fans buy VIP concert passes (3,200 THB), birthday goods boxes (1,890 THB), and monthly tier-3 memberships (450 THB/mo).

---

## 6. Implementation Guard for Research v2 Frontend

The `web/research/index_v2.html` interface includes dedicated slots:
- `data-field="market.observed.monetization"`
- `data-field="market.estimated_size"`
- `data-field="market.estimate_status"`
- `data-field="market.scenario.conservative.*"`
- `data-field="market.scenario.base.*"`
- `data-field="market.scenario.upside.*"`

### Wiring Rules:
1. `market.estimate_status` must display: `"INSUFFICIENT_EVIDENCE (Awaiting Agency Disclosures)"`.
2. `market.observed.monetization` must display: `"~12.5M THB (Observed Multi-Year Public Floor)"`.
3. Scenario fields must carry the explicit tooltip and badge: `"SCENARIO MODEL (Conversion Assumption: 5%–18%)"`.
4. No scenario output may be labeled as "Actual Industry Revenue".
