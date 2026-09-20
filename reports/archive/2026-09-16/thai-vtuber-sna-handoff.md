# ThaiVtuberSNA Dataset Handoff Report

**Date of Discovery & Export:** 2026-09-16  
**Branch:** `fix/discovery-v2-cleanup`  
**Dataset Format:** JSONL (`dist/sna/creator-platform-registry.jsonl`, `dist/sna/discovery-candidates.jsonl`)  

---

## 1. Executive Summary & Inventory

This handoff packages the reviewed public virtual persona registry and discovery candidates for consumption by **ThaiVtuberSNA** (Social Network Analysis of the Thai VTuber / Virtual Creator Ecosystem).

- **Verified Personas**: 571 active personas (19 duplicate personas consolidated)
- **Verified Accounts**: 1118 unique accounts in core graph:
  - TikTok: 450 verified accounts
  - YouTube: 392 verified accounts (backed by direct first-party owner crosslinks)
  - Twitch: 275 verified accounts
- **Verified Persona-Account Links**: 1118 links (all backed by reviewed first-party evidence)
- **Verified Cross-Platform Presence (>= 2 platforms)**: 392 personas (68.7% of total verified personas)
- **Tri-Platform Presence (YouTube + Twitch + TikTok)**: 154 personas (27.0% of total verified personas, up from 64)
- **Unresolved Discovered Candidates (`needs_evidence`)**: 217 candidates
- **Graph Integrity**: 0 unlinked orphan links, 0 duplicate persona-account pairs, 0 multi-persona account conflicts.

---

## 2. Platform Overlap & Distribution

Distribution of verified personas across platforms:
- **1 Platform only**: 179 personas (31.3%)
  - Twitch only: 68 personas
  - TikTok only: 111 personas
- **2 Platforms**: 238 personas (41.7%)
  - TikTok + YouTube: 185 personas
  - Twitch + YouTube: 53 personas
  - TikTok + Twitch: 0 personas
- **3 Platforms (TikTok + Twitch + YouTube)**: 154 personas (27.0%)

**Key Improvements for SNA Graph**:
1. **Persona Identity Consolidation**: 22 duplicate single-platform persona records were consolidated into their canonical multi-platform personas, eliminating identity fragmentation in the network.
2. **Tri-Platform Expansion**: Tri-platform verified presence jumped from 64 to 154 (+90 personas), substantially increasing clustering and interconnectivity in the bipartite creator-platform graph.
3. **Verified Missing-Platform Links**: 14 TW+TT personas were 100% converted to Tri-platform via verified Twitch social links, and 46 indie tri-platform creator clusters were linked directly with first-party YouTube About crosslinks.

---

## 3. Known Biases & Methodological Constraints

1. **Cross-Platform Presence vs. Multi-Homing**: The presence of verified accounts across YouTube, Twitch, and TikTok documents public persona continuity and cross-platform presence. It does NOT automatically imply simultaneous or active "multi-homing" broadcasting behavior without longitudinal temporal activity observations.
2. **Exclusion of Unverified Agency Clusters**: Agency affiliations (e.g. Algorhythm Project, Pixela, Polygon, Euphora) are treated as secondary or unverified relationship structures unless backed by explicit first-party corporate/talent agreements. They are NOT projected as verified graph clusters in the primary SNA platform graph.
3. **Platform Discovery Asymmetries**:
   - YouTube remains the primary root seed and anchor for owner crosslinks.
   - Twitch profiles provide explicit outward social links and stable numeric IDs.
   - TikTok discovery is asymmetric due to web embed limits and guest access restrictions.
4. **Candidates ≠ Verified Graph**: Candidates in `dist/sna/discovery-candidates.jsonl` are unreviewed leads in `needs_evidence`. They must NOT be merged into verified SNA node graphs until human review is applied.

---

## 4. Preliminary SNA Readiness Check

### Ready for Analysis:
- **Creator-Platform Bipartite Graph**: Complete multi-platform mapping across YouTube, Twitch, and TikTok (1118 edges).
- **Cross-Platform Overlap Analysis**: Dense cross-platform core (392 creators with verified multi-platform presence, 154 across all 3 platforms).
- **Secondary Platform Leads**: 262 extracted outward links to X, Facebook, Instagram, Kick, and GankNow in `scratch/secondary-platform-link-review.json`.

### NOT Ready (Out of Scope for Static Registry):
- **Audience Overlap / Shared Viewers**: The registry tracks public creator personas and platform accounts, NOT audience or viewer data.
- **Follower / Subscriber Dynamics**: Follower metrics are dynamic and not tracked in the immutable registry schema.
- **Collaboration Networks**: Stream-level collaboration matrices require live co-occurrence mining, which should be performed downstream using the verified account IDs provided here.

---

## 5. Artifact Files for SNA

1. `dist/sna/creator-platform-registry.jsonl`: Curated verified persona-account links with confidence metadata (1118 rows).
2. `dist/sna/discovery-candidates.jsonl`: Discovery candidates with priority tiers and scores (217 rows).
3. `reports/archive/2026-09-16/sna-platform-coverage.json`: Machine-readable summary statistics.
4. `scratch/persona-consolidation-review.json`: Review dossier for 20 identity collision cases.
5. `scratch/high-priority-platform-link-review.json`: Review dossier for high-priority missing-platform queue.
6. `scratch/secondary-platform-link-review.json`: Review queue of 262 secondary platform links.
