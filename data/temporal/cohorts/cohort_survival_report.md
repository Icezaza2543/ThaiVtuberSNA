# Phase T12: Audience Cohort & Survival Analysis Report

## Executive Summary
This report examines the longitudinal persistence, retention, and reactivation dynamics of pseudonymous audience cohorts across the Thai VTuber interaction ecosystem from 2020 to 2026. Cohorts are defined strictly by each viewer's `first_observed_year` in canonical interactions.

### Epistemic Stance on Observational Survival
1. **Observational Bounds (Not Viewer Churn/Death):** Absence of interaction in a subsequent year indicates that a viewer was *not re-observed in available sampled interaction evidence*. Because passive viewers who consume streams without commenting or chatting cannot be captured in public YouTube data, absence must never be termed 'viewer loss' or 'churn'.
2. **Methodological Rejection of Pure Kaplan-Meier Right-Censoring:** Traditional Kaplan-Meier estimators assume right-censoring is non-informative and that 'event' represents permanent departure. In online interaction networks, viewers frequently re-emerge after multi-year hiatuses (evidenced by the reactivation analysis below). Consequently, empirical cohort persistence matrices and recurrence curves are presented instead of unadjusted Kaplan-Meier models.
3. **Zero Viewer PII Export:** All statistics are presented as aggregated cohort totals and percentages. Zero individual hashes or raw identifiers are exported.

---

## 1. Empirical Cohort Retention Matrix

| Cohort Year | Cohort Size | Obs Year | Elapsed Yrs | Re-Observed Viewers | Continuation Rate | Same-Channel Retained | Same-Channel Rate | Cross-Channel Viewers | Cross-Agency Viewers | Median Breadth |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 5232 | 2020 | +0 | 5232 | 100.0% | 5232 | 100.0% | 0 | 0 | 1 |
| 2020 | 5232 | 2021 | +1 | 509 | 9.7% | 258 | 4.9% | 291 | 126 | 1 |
| 2020 | 5232 | 2022 | +2 | 240 | 4.6% | 79 | 1.5% | 179 | 81 | 1 |
| 2020 | 5232 | 2023 | +3 | 177 | 3.4% | 43 | 0.8% | 146 | 74 | 1 |
| 2020 | 5232 | 2024 | +4 | 136 | 2.6% | 21 | 0.4% | 121 | 35 | 1 |
| 2020 | 5232 | 2025 | +5 | 150 | 2.9% | 19 | 0.4% | 134 | 45 | 1 |
| 2020 | 5232 | 2026 | +6 | 103 | 2.0% | 5 | 0.1% | 100 | 19 | 1 |
| 2021 | 10750 | 2021 | +0 | 10750 | 100.0% | 10750 | 100.0% | 0 | 0 | 1 |
| 2021 | 10750 | 2022 | +1 | 1025 | 9.5% | 453 | 4.2% | 684 | 275 | 1 |
| 2021 | 10750 | 2023 | +2 | 530 | 4.9% | 164 | 1.5% | 426 | 193 | 1 |
| 2021 | 10750 | 2024 | +3 | 349 | 3.2% | 74 | 0.7% | 296 | 131 | 1 |
| 2021 | 10750 | 2025 | +4 | 362 | 3.4% | 47 | 0.4% | 331 | 164 | 1 |
| 2021 | 10750 | 2026 | +5 | 273 | 2.5% | 27 | 0.2% | 256 | 119 | 1 |
| 2022 | 10740 | 2022 | +0 | 10740 | 100.0% | 10740 | 100.0% | 0 | 0 | 1 |
| 2022 | 10740 | 2023 | +1 | 835 | 7.8% | 412 | 3.8% | 544 | 268 | 1 |
| 2022 | 10740 | 2024 | +2 | 405 | 3.8% | 121 | 1.1% | 317 | 162 | 1 |
| 2022 | 10740 | 2025 | +3 | 330 | 3.1% | 90 | 0.8% | 278 | 145 | 1 |
| 2022 | 10740 | 2026 | +4 | 225 | 2.1% | 44 | 0.4% | 191 | 95 | 1 |
| 2023 | 17104 | 2023 | +0 | 17104 | 100.0% | 17104 | 100.0% | 0 | 0 | 1 |
| 2023 | 17104 | 2024 | +1 | 1263 | 7.4% | 584 | 3.4% | 807 | 350 | 1 |
| 2023 | 17104 | 2025 | +2 | 885 | 5.2% | 327 | 1.9% | 629 | 256 | 1 |
| 2023 | 17104 | 2026 | +3 | 473 | 2.8% | 157 | 0.9% | 347 | 139 | 1 |
| 2024 | 11325 | 2024 | +0 | 11325 | 100.0% | 11325 | 100.0% | 0 | 0 | 1 |
| 2024 | 11325 | 2025 | +1 | 1311 | 11.6% | 566 | 5.0% | 878 | 335 | 1 |
| 2024 | 11325 | 2026 | +2 | 584 | 5.2% | 221 | 1.9% | 414 | 123 | 1 |
| 2025 | 14081 | 2025 | +0 | 14081 | 100.0% | 14081 | 100.0% | 0 | 0 | 1 |
| 2025 | 14081 | 2026 | +1 | 1115 | 7.9% | 467 | 3.3% | 772 | 214 | 1 |
| 2026 | 10486 | 2026 | +0 | 10486 | 100.0% | 10486 | 100.0% | 0 | 0 | 1 |

---

## 2. Longitudinal Cohort Survival & Persistence Curve

| Elapsed Horizon | Cohorts Evaluated | Pooled Cohort Base | Pooled Re-Observed | Persistence Rate | Same-Channel Persistence | Cross-Channel Persistence | Cross-Agency Persistence | Mean Cohort Median Breadth |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| +0 Year(s) | 7 | 79718 | 79718 | 100.0% | 100.0% | 0.0% | 0.0% | 1.00 |
| +1 Year(s) | 6 | 69232 | 6058 | 8.8% | 4.0% | 5.7% | 2.3% | 1.00 |
| +2 Year(s) | 5 | 55151 | 2644 | 4.8% | 1.7% | 3.6% | 1.5% | 1.00 |
| +3 Year(s) | 4 | 43826 | 1329 | 3.0% | 0.8% | 2.4% | 1.1% | 1.00 |
| +4 Year(s) | 3 | 26722 | 723 | 2.7% | 0.4% | 2.4% | 1.1% | 1.00 |
| +5 Year(s) | 2 | 15982 | 423 | 2.6% | 0.3% | 2.4% | 1.0% | 1.00 |
| +6 Year(s) | 1 | 5232 | 103 | 2.0% | 0.1% | 1.9% | 0.4% | 1.00 |

### Substantive Observations on Persistence
- **Initial Continuation Drop (+1 Year):** In the first year after initial observation, pooled cohort continuation averages **8.8%**, reflecting the heavy long-tail of transient commenters common to social video platforms.
- **Long-Term Ecosystem Core (+6 Years):** The 2020 pioneer cohort retains **103 viewers (2.0%)** actively participating in 2026, establishing an empirical core audience with over half a decade of continuous ecosystem involvement.
- **Channel Dispersion Over Time:** As elapsed years increase, cross-channel and cross-agency interaction rates surpass same-channel retention, illustrating audience broadening across the creator network.

---

## 3. Audience Reactivation Dynamics (Intermittent Participation)

A total of **2730 reactivation occurrences** were detected where a viewer was re-observed after >= 1 unobserved intervening year.

| Cohort Year | Reactivation Year | Gap Duration | Reactivated Viewers | Cohort Size | Reactivation Rate | Note |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 2020 | 2022 | 2 Yrs | 111 | 5232 | 2.12% | Reactivated after 1 unobserved year(s) |
| 2020 | 2023 | 2 Yrs | 37 | 5232 | 0.71% | Reactivated after 1 unobserved year(s) |
| 2020 | 2023 | 3 Yrs | 63 | 5232 | 1.20% | Reactivated after 2 unobserved year(s) |
| 2020 | 2024 | 2 Yrs | 17 | 5232 | 0.32% | Reactivated after 1 unobserved year(s) |
| 2020 | 2024 | 3 Yrs | 9 | 5232 | 0.17% | Reactivated after 2 unobserved year(s) |
| 2020 | 2024 | 4 Yrs | 58 | 5232 | 1.11% | Reactivated after 3 unobserved year(s) |
| 2020 | 2025 | 2 Yrs | 18 | 5232 | 0.34% | Reactivated after 1 unobserved year(s) |
| 2020 | 2025 | 3 Yrs | 8 | 5232 | 0.15% | Reactivated after 2 unobserved year(s) |
| 2020 | 2025 | 4 Yrs | 17 | 5232 | 0.32% | Reactivated after 3 unobserved year(s) |
| 2020 | 2025 | 5 Yrs | 58 | 5232 | 1.11% | Reactivated after 4 unobserved year(s) |
| 2020 | 2026 | 2 Yrs | 9 | 5232 | 0.17% | Reactivated after 1 unobserved year(s) |
| 2020 | 2026 | 3 Yrs | 11 | 5232 | 0.21% | Reactivated after 2 unobserved year(s) |
| 2020 | 2026 | 4 Yrs | 4 | 5232 | 0.08% | Reactivated after 3 unobserved year(s) |
| 2020 | 2026 | 5 Yrs | 9 | 5232 | 0.17% | Reactivated after 4 unobserved year(s) |
| 2020 | 2026 | 6 Yrs | 28 | 5232 | 0.54% | Reactivated after 5 unobserved year(s) |
| 2021 | 2023 | 2 Yrs | 269 | 10750 | 2.50% | Reactivated after 1 unobserved year(s) |
| 2021 | 2024 | 2 Yrs | 59 | 10750 | 0.55% | Reactivated after 1 unobserved year(s) |
| 2021 | 2024 | 3 Yrs | 136 | 10750 | 1.27% | Reactivated after 2 unobserved year(s) |
| 2021 | 2025 | 2 Yrs | 52 | 10750 | 0.48% | Reactivated after 1 unobserved year(s) |
| 2021 | 2025 | 3 Yrs | 45 | 10750 | 0.42% | Reactivated after 2 unobserved year(s) |
| 2021 | 2025 | 4 Yrs | 126 | 10750 | 1.17% | Reactivated after 3 unobserved year(s) |
| 2021 | 2026 | 2 Yrs | 24 | 10750 | 0.22% | Reactivated after 1 unobserved year(s) |
| 2021 | 2026 | 3 Yrs | 21 | 10750 | 0.20% | Reactivated after 2 unobserved year(s) |
| 2021 | 2026 | 4 Yrs | 17 | 10750 | 0.16% | Reactivated after 3 unobserved year(s) |
| 2021 | 2026 | 5 Yrs | 89 | 10750 | 0.83% | Reactivated after 4 unobserved year(s) |
| 2022 | 2024 | 2 Yrs | 197 | 10740 | 1.83% | Reactivated after 1 unobserved year(s) |
| 2022 | 2025 | 2 Yrs | 61 | 10740 | 0.57% | Reactivated after 1 unobserved year(s) |
| 2022 | 2025 | 3 Yrs | 119 | 10740 | 1.11% | Reactivated after 2 unobserved year(s) |
| 2022 | 2026 | 2 Yrs | 30 | 10740 | 0.28% | Reactivated after 1 unobserved year(s) |
| 2022 | 2026 | 3 Yrs | 19 | 10740 | 0.18% | Reactivated after 2 unobserved year(s) |
| 2022 | 2026 | 4 Yrs | 54 | 10740 | 0.50% | Reactivated after 3 unobserved year(s) |
| 2023 | 2025 | 2 Yrs | 444 | 17104 | 2.60% | Reactivated after 1 unobserved year(s) |
| 2023 | 2026 | 2 Yrs | 65 | 17104 | 0.38% | Reactivated after 1 unobserved year(s) |
| 2023 | 2026 | 3 Yrs | 160 | 17104 | 0.94% | Reactivated after 2 unobserved year(s) |
| 2024 | 2026 | 2 Yrs | 286 | 11325 | 2.53% | Reactivated after 1 unobserved year(s) |

---
*Report generated automatically by `scripts/analyze_audience_cohorts.py`.*
