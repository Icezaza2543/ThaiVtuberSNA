# Unverified Historical Dataset Archive

**Archived Date:** 2026-09-06
**Status:** UNVERIFIED PROVENANCE (Preserved for Audit)

## Provenance Verification Report

1. **Key Continuity:**
   - Active Persistent Key Fingerprint: `142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`
   - Active Persistent Key Mtime: `2026-09-06 20:15:39`

2. **Historical Data Timestamps:**
   - The Parquet files in this archive were generated between `20:11:08` and `20:11:37` on 2026-09-06.
   - They predate the initialization of the current persistent key.

3. **Mathematical Identity Test:**
   - In-memory collection of 79 comments from video `G1LXXzZx48c` hashed with the active persistent key was tested against `2026/08/G1LXXzZx48c.parquet`.
   - **Result:** 0 matches out of 79 hashes.
   - **Conclusion:** This historical dataset was generated with an ephemeral secret key that was not retained. In accordance with project governance rules, this dataset is NOT bound to `identity_manifest.json` and must NOT be mixed with new verified collection runs.
