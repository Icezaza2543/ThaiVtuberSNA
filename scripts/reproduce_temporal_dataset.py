#!/usr/bin/env python3
"""Phase T18: End-to-End Temporal Dataset Reproduction Orchestrator

Executes downstream deterministic pipelines in strict order:
1. T11: Community Lineage v2 (Global maximum-weight bipartite matching)
2. T13: Centrality Evolution & Bridge Dynamics (th5_retention_ratio >= 0.50 threshold)
3. T14: Ecosystem Evolution (agency_at_selection metadata, 2025->2026 partial break)
4. T15: Evidence Quality & Perturbation Sensitivity (high_comment_volume_rate, 10% dropout)
5. T17: Research Dashboard Data Build (NO_VIEWER_LEVEL_DATA)
6. T18: Dataset Release Manifest & Reproducibility Package Build
7. Release Validation Audit
"""
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

PIPELINE_STEPS = [
    ("T11 Community Lineage v2", ["python", "scripts/build_community_lineage_v2.py"]),
    ("T13 Centrality Evolution", ["python", "scripts/analyze_centrality_evolution.py"]),
    ("T14 Ecosystem Evolution", ["python", "scripts/analyze_ecosystem_evolution.py"]),
    ("T15 Evidence Quality", ["python", "scripts/generate_evidence_quality_report.py"]),
    ("T17 Research Dashboard Data", ["python", "scripts/build_research_dashboard_data.py"]),
    ("T18 Dataset Release Package", ["python", "scripts/build_dataset_release.py"]),
    ("T18 Release Validation", ["python", "scripts/validate_dataset_release.py"]),
]


def run_pipeline(dry_run: bool = False) -> bool:
    print("=" * 65)
    print("ThaiVTuberSNA: Reproducible Downstream Dataset Pipeline")
    print("=" * 65)

    for name, cmd in PIPELINE_STEPS:
        print(f"\n>>> Executing Step: {name}")
        print(f"    Command: {' '.join(cmd)}")
        if dry_run:
            print("    [DRY RUN] Skipping actual execution.")
            continue

        result = subprocess.run(cmd, cwd=str(BASE))
        if result.returncode != 0:
            print(f"\n❌ FAILED at step '{name}' (exit code {result.returncode})")
            return False
        print(f"    ✓ {name} completed successfully.")

    print("\n" + "=" * 65)
    print("✓ Full reproducible dataset pipeline finished successfully.")
    print("=" * 65)
    return True


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    success = run_pipeline(dry_run=dry_run)
    sys.exit(0 if success else 1)
