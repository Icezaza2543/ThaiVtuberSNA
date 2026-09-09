# Empirical Ecosystem Outlook Model: Structural Indicators & Trajectory

> **Primary Classification**: **`INSUFFICIENT_EVIDENCE`**  
> **Methodological Standard**: Multi-dimensional empirical scorecard based on 11 verifiable indicators. Zero arbitrary black-box scores. Fails closed when commercial monetization evidence is absent.

---

## 1. Executive Summary & Epistemic Boundaries

Public commentary frequently poses questions regarding ecosystem contraction or expansion across virtual streamer rosters. Rather than relying on social media sentiment, this framework evaluates the ecosystem across **11 structural dimensions** spanning Creator Supply, Audience Activity, Persistence, and Network Topology.

### Observed Empirical Patterns
1. **Creator Activity in Target Cohort**:
   - Active channels in our target research cohort numbered **166 channels in 2025** (out of 193 total cohort channels).
   - Annual interacting audience volume in 2025 reached **17,119 active accounts**.
2. **Audience Account Persistence**:
   - Re-observed accounts accounted for **58.7% of all active interacting accounts in 2025** (up from 15.3% in 2021).
   - The proportion of newly observed interacting accounts decreased from 84.7% (2021) to 41.3% (2025), reflecting cohort maturation.
3. **Monetization & Commercial Transparency Boundary**:
   - While non-summable public price signals exist (e.g. ticket prices, retail merchandise unit prices), private agency disclosures and transaction volumes remain undisclosed.
   - Under the fail-closed epistemic policy, overall industry financial outlook remains **`INSUFFICIENT_EVIDENCE`**.

---

## 2. The 11-Dimension Outlook Scorecard

| Dimension | Metric | 2024 Value | 2025 Value | Observed Trajectory | Confidence | Source Artifact |
|---|---|---|---|---|---|---|
| **`CREATOR_SUPPLY`** | `active_channels_count` | `157.00` | `166.00` | **`EXPANDING`** | `HIGH` | `yearly_ecosystem_metrics.parquet` |
| **`ENTRY_RATE`** | `pct_new_interacting_audience` | `84.03%` | `82.25%` | **`CONTRACTING`** | `HIGH` | `audience_behavior_yearly.parquet` |
| **`EXIT_PRESSURE`** | `verified_graduations_and_closures` | `2.00` | `9.00` | **`EXPANDING`** | `MEDIUM` | `creator_status_events.parquet` |
| **`AUDIENCE_ACTIVITY`** | `annual_active_interaction_accounts` | `13,478` | `17,119` | **`EXPANDING`** | `HIGH` | `audience_behavior_yearly.parquet` |
| **`AUDIENCE_PERSISTENCE`** | `pct_re_observed_accounts` | `15.97%` | `17.75%` | **`EXPANDING`** | `HIGH` | `audience_behavior_yearly.parquet` |
| **`AUDIENCE_BREADTH`** | `pct_multi_channel_observed` | `8.90%` | `9.92%` | **`EXPANDING`** | `HIGH` | `audience_behavior_yearly.parquet` |
| **`NETWORK_INTEGRATION`** | `cross_community_edge_share` | `0.46` | `0.49` | **`STABLE`** | `HIGH` | `yearly_ecosystem_metrics.parquet` |
| **`NETWORK_CONCENTRATION`** | `degree_concentration_gini` | `0.44` | `0.43` | **`STABLE`** | `HIGH` | `yearly_ecosystem_metrics.parquet` |
| **`COMMUNITY_STRUCTURE`** | `modularity_q` | `0.31` | `0.32` | **`STABLE`** | `HIGH` | `yearly_ecosystem_metrics.parquet` |
| **`MONETIZATION_EVIDENCE`** | `monetization_evidence_status` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | **`INSUFFICIENT_EVIDENCE`** | `LOW` | `market_evidence.parquet` |
| **`DATA_CONFIDENCE`** | `catalog_channel_coverage_rate_pct` | `97.50%` | `98.80%` | **`STABLE`** | `HIGH` | `yearly_evidence_quality.parquet` |

---

## 3. Explicit Classification Rules & State Taxonomy

```
┌────────────────────┬─────────────────────────────────────────────────────────────┐
│ CLASSIFICATION     │ DECISION RULES                                              │
├────────────────────┼─────────────────────────────────────────────────────────────┤
│ EXPANSION          │ Supply growth > +15% AND Audience activity growth > +20%   │
│                    │ AND Entry rate expanding.                                   │
├────────────────────┼─────────────────────────────────────────────────────────────┤
│ CONSOLIDATING      │ Supply flat/modest (+-10%) AND Audience persistence > 50%   │
│                    │ AND Modularity Q >= 0.25 AND Concentration Gini stable.     │
├────────────────────┼─────────────────────────────────────────────────────────────┤
│ NICHE_STABLE       │ Supply stable (+-10%) AND Audience activity stable (+-15%)  │
│                    │ AND Persistence stable.                                     │
├────────────────────┼─────────────────────────────────────────────────────────────┤
│ CONTRACTING        │ Supply drop > -15% AND Audience drop > -20%                 │
│                    │ AND Persistence falling.                                    │
├────────────────────┼─────────────────────────────────────────────────────────────┤
│ INSUFFICIENT_EVID  │ Monetization evidence missing or indicators conflict.       │
│ [FAIL-CLOSED]      │ Default state when evidence gates fail.                     │
└────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 4. Sensitivity Analysis

- **Test 1: Excluding 2026 YTD**: 2026 represents an incomplete annual window. Analysis focuses on completed calendar years 2020 through 2025.
- **Test 2: Modality Sensitivity**: Comment-only and live-chat accounts show consistent re-observation trends across the target cohort.
- **Test 3: Commercial Disclosure Gate**: Without auditable revenue statements, economic viability cannot be inferred solely from audience participation.

---
*Report generated automatically by `scripts/build_outlook_model.py`.*