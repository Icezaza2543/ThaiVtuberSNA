# Research v2 source identity hotfix

Baseline: `d71738070f7e17c017aab2260f393a54e169ea1e`.

All 40 curated identity entries were compared against the frozen manifest and registry names, plus the existing source title/subject. This bounded audit does not claim a new verification of every event date or remote page. No broad research or private workbook access was performed.

## Identity disposition

| Subject | Old key | Corrected key / disposition | Reason |
|---|---|---|---|
| Cazzie K. Monie | `UC-qBbCCqtD2H4WSs9m978Ow` | `UC-qBbCCqtD2H4WSs9m978Ow` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Dacapo | `UC_nmh9XycGlquouvai2UC6g` | `UCuZ1ajvlGFUMCHZAPdetKHw` / CORRECTED | Name agrees with manifest and registry |
| Baabel | `UC3ZglUA0HEUCuGbe5b8zXKw` | `UC3ZglUA0HEUCuGbe5b8zXKw` / QUARANTINED | CONFLICT: registry owner The Lupas, curated subject Baabel; outside frozen manifest |
| Schneider | `UCpGtwNmbOtgmcKIY81MIX_w` | `UCNTEr2_96vJnXNazr5MwNLA` / CORRECTED | Name agrees with manifest and registry |
| Aisha | `UCqhhWjpw23dWhJ5rRwCCrMA` | `UCqhhWjpw23dWhJ5rRwCCrMA` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Catalog-verified graduation | `UC32lsx7u7vqy63SguuuzmVg` | `UC32lsx7u7vqy63SguuuzmVg` / QUARANTINED | OUTSIDE_FROZEN_MANIFEST; source identity not verified |
| Lucene | `UC25e5qEqvVaG_VKrkTmJBmw` | `UC25e5qEqvVaG_VKrkTmJBmw` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Luxia | `UCRG5fX1v4b-3sUyKfAAtxxA` | `UCRG5fX1v4b-3sUyKfAAtxxA` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Lapine | `UCC5q6CpuDflPvO7pNn52RGQ` | `UCC5q6CpuDflPvO7pNn52RGQ` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Hoku | `UCZilc7jP-X_92Fii1uTIs0Q` | `UCZilc7jP-X_92Fii1uTIs0Q` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |
| Laibaht | `UCR1Htb-H1-tus7UPotPh69A` | `UCR1Htb-H1-tus7UPotPh69A` / QUARANTINED | AGENCY_AT_SELECTION_CONFLICT; historical affiliation requires explicit verification |

The misleading “Schneider / S1R” comment was replaced by explicit S1R identity metadata. The Baabel/The Lupas conflict is quarantined, not reassigned. The other out-of-cohort channel is Narelle (`UC32lsx7u7vqy63SguuuzmVg`); its catalog graduation event remains quarantined. Historical affiliations that differ from Independent at selection are not assumed false: they require separate explicit evidence before release.

## Mechanical changes

Lifecycle events: 232 → 229. Primary: 13 → 12; secondary: 40 → 32; proxy: 179 → 185. Quarantine contains 12 curated events across 9 entries; 3 were already outside the frozen cohort and absent from the old event output. Proxy replacement explains why total events do not fall by 12.

Full-ecosystem supply saturation: STRONGLY SUPPORTED → HYPOTHESIS / INSUFFICIENT_EVIDENCE. Registry and cohort scopes cannot form a valid competition ratio.

Reactivation counts are generated from audience_behavior_yearly.parquet, with partial 2026 excluded from full-year trend comparison. WACTOR corporate registration remains UNVERIFIED; RPG closure remains INFERRED_PROXY. Neither is a verified legal closure.

Snapshot activity is MANIFEST_AT_SELECTION; lifecycle evidence tier is separate. No automatic VERIFIED label for active channels. EXIT_PRESSURE is primary_verified_graduations; terminations, secondary exits and proxy boundaries are separately tabulated in the generated reports.

## Rebuild order

```powershell
python scripts/audit_creator_identity_mapping.py
python scripts/build_creator_lifecycle_evidence.py
python scripts/build_outlook_model.py
python scripts/build_research_v2_data.py
python scripts/refresh_research_integrity_docs.py
python scripts/audit_research_v2_consistency.py
python -m pytest
```

The lifecycle builder writes events, then coverage, then the dependent public snapshot. pytest.ini limits default collection to tests/; scratch/test_canonical_query.py is a live workbook diagnostic with import-time I/O, not an offline regression test.

Remaining evidence blockers: quarantined identities/affiliations need source verification; full-registry audience coverage is missing; legal organizational closure evidence is unavailable. These remain excluded or qualified rather than being treated as established findings.

## Validation

Both identity and consistency audits PASS. `python -m pytest`: **362 passed, 120 warnings in 108.70s (0:01:48)**. The 120 warnings are NetworkX assortativity warnings. Final hotfix regressions: 9 passed. `git diff --check` and JavaScript syntax check PASS. Canvas coordinate SHA-256 remains `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.
