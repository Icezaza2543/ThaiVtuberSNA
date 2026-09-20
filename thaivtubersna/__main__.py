"""
CLI entry point for thaivtubersna.

Commands:
    python -m thaivtubersna run            # one full cycle
    python -m thaivtubersna worker         # 24/7 loop
    python -m thaivtubersna validate       # check DB health + parity
    python -m thaivtubersna export         # export CSVs to dist/export/
    python -m thaivtubersna queue          # show review queue status
    python -m thaivtubersna apply <file>   # apply a review JSON file
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("thaivtubersna")

ROOT = Path(__file__).resolve().parents[1]


def _validate(args):
    from .store import DB_PATH, connect, count, verify_parity
    path = getattr(args, "db", None) or DB_PATH
    print(f"Validating {path} …\n")
    with connect(path) as con:
        result = verify_parity(con)
        ne = con.execute("SELECT COUNT(*) FROM network_edges").fetchone()[0]
        ws = con.execute("SELECT COUNT(*) FROM worker_state").fetchone()[0]

    ok_sym = lambda ok: "✓" if ok else "✗"
    print(f"  {'Metric / Table':<28} {'expected':>10} {'actual':>10} {'match':>6}")
    print("  " + "-" * 58)
    for table, info in result["tables"].items():
        print(f"  {table:<28} {info['expected']:>10,} {info['actual']:>10,} {ok_sym(info['ok']):>6}")
    print(f"  {'worker_state':<28} {'(state)':>10} {ws:>10,}")

    if result["ok"]:
        print("\n✓ Database is healthy.")
        return 0
    else:
        print("\n✗ Parity mismatch detected. Investigate before continuing.")
        return 1


def _run(args):
    from .worker import run_once
    path = getattr(args, "db", None) or None
    results = run_once(db_path=path)
    print(json.dumps(results, indent=2, default=str))
    return 0


def _worker(args):
    from .worker import run_loop
    path = getattr(args, "db", None) or None
    run_loop(db_path=path)
    return 0


def _export(args):
    from .export import export_all
    path = getattr(args, "db", None) or None
    out = Path(args.output) if args.output else None
    counts = export_all(output_dir=out, db_path=path)
    for fname, n in counts.items():
        print(f"  {fname}: {n:,} rows")
    return 0


def _queue(args):
    from .review import queue_status
    path = getattr(args, "db", None) or None
    status = queue_status(db_path=path)
    print(json.dumps(status, indent=2))
    return 0


def _apply(args):
    from .review import apply_change
    from .store import DB_PATH, connect
    path = getattr(args, "db", None) or DB_PATH
    review_file = Path(args.file)
    if not review_file.exists():
        print(f"File not found: {review_file}", file=sys.stderr)
        return 1
    change = json.loads(review_file.read_text(encoding="utf-8"))
    dry_run = args.dry_run
    with connect(path) as con:
        result = apply_change(con, change, dry_run=dry_run)
        if not dry_run:
            # Move to applied/
            applied_dir = ROOT / "reviews" / "applied"
            applied_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(review_file), applied_dir / review_file.name)
    print(json.dumps(result, indent=2))
    if dry_run:
        print("\n(dry run — nothing written)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m thaivtubersna",
        description="ThaiVtuberSNA — 4-step worker pipeline"
    )
    parser.add_argument("--db", type=Path, default=None,
                        help="Path to DuckDB file (default: runtime/thaivtubersna.duckdb)")
    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("validate", help="Check DB health and parity")
    subs.add_parser("run", help="Run one full cycle (collect → review → sna → export)")
    subs.add_parser("worker", help="Run 24/7 loop")

    exp = subs.add_parser("export", help="Export CSVs for ThaiVtuberMaster")
    exp.add_argument("--output", default=None, help="Output directory (default: dist/export/)")

    subs.add_parser("queue", help="Show review queue status")

    apply = subs.add_parser("apply", help="Apply a review JSON file")
    apply.add_argument("file", help="Path to review JSON change file")
    apply.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    dispatch = {
        "validate": _validate,
        "run":      _run,
        "worker":   _worker,
        "export":   _export,
        "queue":    _queue,
        "apply":    _apply,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
