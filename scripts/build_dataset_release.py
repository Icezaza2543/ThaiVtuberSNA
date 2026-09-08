#!/usr/bin/env python3
"""T18 — Reproducible Dataset Release Manifest

Generates a complete dataset release manifest documenting:
1. All data artifacts produced by T8–T16
2. Schema descriptions for every parquet file
3. File checksums for reproducibility
4. Provenance chain from collection through analysis
5. Methodological notes and limitations

Zero viewer PII is exported. All artifacts are macro-level.
"""

import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# ── Paths ──────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent
TEMPORAL = BASE / "data" / "temporal"
OUTPUT_DIR = BASE / "data" / "temporal" / "release"
MANIFEST_JSON = OUTPUT_DIR / "dataset_manifest.json"
MANIFEST_MD = OUTPUT_DIR / "dataset_release_notes.md"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return f"sha256_{h.hexdigest()}"


def describe_parquet(path: Path) -> dict:
    """Get schema and row count for a parquet file."""
    try:
        df = pd.read_parquet(path)
        schema = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            sample_vals = df[col].dropna().head(3).tolist()
            sample_strs = [str(v)[:60] for v in sample_vals]
            schema[col] = {
                "dtype": dtype,
                "null_count": int(df[col].isnull().sum()),
                "sample_values": sample_strs,
            }
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "schema": schema,
        }
    except Exception as e:
        return {"error": str(e)}


def scan_directory(dir_path: Path) -> list:
    """Recursively scan a directory for data artifacts."""
    artifacts = []
    if not dir_path.exists():
        return artifacts

    for path in sorted(dir_path.rglob("*")):
        if path.is_file() and not path.name.startswith('.'):
            rel = path.relative_to(BASE)
            entry = {
                "path": str(rel).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "checksum": sha256_file(path),
                "format": path.suffix.lstrip('.'),
            }

            if path.suffix == '.parquet':
                entry["schema_info"] = describe_parquet(path)
            elif path.suffix == '.md':
                entry["content_type"] = "markdown_report"
                entry["lines"] = len(path.read_text(encoding='utf-8', errors='replace').splitlines())
            elif path.suffix == '.json':
                entry["content_type"] = "json_data"
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    if isinstance(data, dict):
                        entry["top_level_keys"] = list(data.keys())[:20]
                    elif isinstance(data, list):
                        entry["record_count"] = len(data)
                except Exception:
                    pass

            artifacts.append(entry)

    return artifacts


def build_manifest():
    """Build the complete dataset manifest."""
    print("=" * 60)
    print("T18: Building Reproducible Dataset Release Manifest")
    print("=" * 60)

    # Scan all temporal subdirectories
    sections = {}
    subdirs = [
        ("lifecycle", "T8: Lifecycle Events & Intervals"),
        ("event_analysis", "T9: Lifecycle Event Impact Analysis"),
        ("robustness", "T10: Sensitivity & Robustness Analysis"),
        ("analysis", "T11: Community Lineage & Network Metrics"),
        ("cohorts", "T12: Audience Cohort Survival"),
        ("centrality", "T13: Bridge Dynamics & Centrality"),
        ("ecosystem", "T14: Ecosystem Structural Evolution"),
        ("quality", "T15: Evidence Quality & Bias"),
        ("incremental", "T16: Incremental Pipeline State"),
        ("research_integrity", "Integrity Reports"),
        ("snapshots", "Network Snapshots"),
        ("state", "Pipeline State"),
    ]

    total_files = 0
    total_bytes = 0

    for subdir, label in subdirs:
        path = TEMPORAL / subdir
        artifacts = scan_directory(path)
        if artifacts:
            sections[subdir] = {
                "label": label,
                "file_count": len(artifacts),
                "total_bytes": sum(a["size_bytes"] for a in artifacts),
                "artifacts": artifacts,
            }
            total_files += len(artifacts)
            total_bytes += sum(a["size_bytes"] for a in artifacts)
            print(f"  {label}: {len(artifacts)} files ({sum(a['size_bytes'] for a in artifacts) / 1024:.1f} KB)")

    manifest = {
        "meta": {
            "title": "Thai VTuber SNA — Reproducible Research Dataset",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phases_covered": "T8–T16",
            "temporal_range": "2020–2026 (2026 = YTD partial window)",
            "privacy_level": "AGGREGATED_MACRO_ONLY",
            "privacy_guarantee": "Zero raw viewer identifiers, channel IDs are public YouTube metadata.",
            "total_files": total_files,
            "total_bytes": total_bytes,
            "checksum_algorithm": "SHA-256",
        },
        "methodology": {
            "data_collection": (
                "YouTube public comment and live chat interaction evidence collected "
                "via YouTube Data API v3 with HMAC-SHA256 pseudonymization at ingestion. "
                "Viewer channel IDs are irreversibly transformed; zero raw IDs are stored."
            ),
            "network_construction": (
                "Co-commenter/co-chatter edges built from shared pseudonymized viewer "
                "presence across channel video pairs. Edge weight = count of shared distinct "
                "viewer pseudonyms."
            ),
            "temporal_slicing": (
                "Interactions partitioned by calendar year of video publication date. "
                "Undated interactions excluded from temporal slices."
            ),
            "community_detection": "Louvain community detection (NetworkX) at resolution=1.0.",
            "lineage_matching": (
                "Deterministic maximum-weight bipartite matching per adjacent-year pair "
                "using W = 0.4*Jaccard + 0.3*Forward + 0.3*Backward. "
                "Strict one-to-one backbone constraint."
            ),
            "limitations": [
                "Observational sampling: only commenters/chatters captured, not silent viewers.",
                "YouTube API pagination ceiling: ~100 comments per standard fetch.",
                "2026 represents partial Year-To-Date window.",
                "Agency/group assignments reflect selection-time status, not historical membership.",
                "HMAC pseudonymization is linkable within the same key; not full anonymity.",
            ],
        },
        "sections": sections,
    }

    return manifest


def write_release_notes(manifest):
    """Generate human-readable release notes."""
    lines = [
        "# Thai VTuber SNA — Reproducible Research Dataset Release Notes\n",
        f"**Version:** {manifest['meta']['version']}",
        f"**Generated:** {manifest['meta']['generated_at']}",
        f"**Phases:** {manifest['meta']['phases_covered']}",
        f"**Temporal Range:** {manifest['meta']['temporal_range']}",
        f"**Privacy:** {manifest['meta']['privacy_level']}",
        f"**Total Files:** {manifest['meta']['total_files']}",
        f"**Total Size:** {manifest['meta']['total_bytes'] / 1024:.1f} KB",
        "",
        "---",
        "",
        "## Privacy Guarantee",
        "",
        manifest['meta']['privacy_guarantee'],
        "",
        "---",
        "",
        "## Methodology",
        "",
        f"**Data Collection:** {manifest['methodology']['data_collection']}",
        "",
        f"**Network Construction:** {manifest['methodology']['network_construction']}",
        "",
        f"**Temporal Slicing:** {manifest['methodology']['temporal_slicing']}",
        "",
        f"**Community Detection:** {manifest['methodology']['community_detection']}",
        "",
        f"**Lineage Matching:** {manifest['methodology']['lineage_matching']}",
        "",
        "### Known Limitations",
        "",
    ]

    for lim in manifest['methodology']['limitations']:
        lines.append(f"- {lim}")

    lines.extend(["", "---", "", "## Dataset Contents", ""])

    for key, section in manifest['sections'].items():
        lines.append(f"### {section['label']}")
        lines.append(f"**Files:** {section['file_count']} | **Size:** {section['total_bytes'] / 1024:.1f} KB")
        lines.append("")
        lines.append("| File | Format | Size | Checksum |")
        lines.append("| :--- | :---: | ---: | :--- |")
        for art in section['artifacts']:
            name = art['path'].split('/')[-1]
            size = f"{art['size_bytes'] / 1024:.1f} KB"
            cksum = art['checksum'][:20] + '...'
            lines.append(f"| `{name}` | {art['format']} | {size} | `{cksum}` |")

        # Schema details for parquet files
        parquets = [a for a in section['artifacts'] if a['format'] == 'parquet' and 'schema_info' in a]
        if parquets:
            lines.append("")
            for pq in parquets:
                name = pq['path'].split('/')[-1]
                info = pq['schema_info']
                if 'error' in info:
                    continue
                lines.append(f"**`{name}`** schema ({info['rows']} rows × {info['columns']} cols):")
                lines.append("")
                lines.append("| Column | Type | Nulls |")
                lines.append("| :--- | :--- | ---: |")
                for col, meta in info['schema'].items():
                    lines.append(f"| `{col}` | `{meta['dtype']}` | {meta['null_count']} |")
                lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("*Release manifest generated automatically by `scripts/build_dataset_release.py`.*")
    return "\n".join(lines)


def main():
    manifest = build_manifest()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write JSON manifest
    MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )
    print(f"\n✓ JSON manifest: {MANIFEST_JSON} ({MANIFEST_JSON.stat().st_size / 1024:.1f} KB)")

    # Write markdown release notes
    md_content = write_release_notes(manifest)
    MANIFEST_MD.write_text(md_content, encoding="utf-8")
    print(f"✓ Release notes: {MANIFEST_MD} ({MANIFEST_MD.stat().st_size / 1024:.1f} KB)")

    # Privacy verification
    for path in [MANIFEST_JSON, MANIFEST_MD]:
        content = path.read_text(encoding="utf-8")
        import re
        # Check for non-prefixed hex strings (excluding sha256_ prefixed ones)
        raw_hex = re.findall(r'(?<!sha256_)\b[0-9a-f]{64}\b', content)
        if raw_hex:
            print(f"\n⚠ WARNING: {path.name} contains {len(raw_hex)} unprefixed 64-char hex strings!")
            return 1

    print("✓ Privacy check: zero unprefixed hex strings in outputs.")
    print(f"\n✓ T18 complete: {manifest['meta']['total_files']} artifacts documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
