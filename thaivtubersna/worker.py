"""
24/7 Worker Loop
================
Runs the 4-step pipeline continuously with configurable intervals,
state persistence in worker_state, and exponential backoff on errors.

    collect  → every COLLECT_INTERVAL seconds
    review   → every REVIEW_INTERVAL seconds
    sna      → every SNA_INTERVAL seconds
    export   → every EXPORT_INTERVAL seconds

Worker State Tracked:
    last_collect_at, last_discovery_at, last_review_at, last_sna_at, last_export_at
    next_collect_at, next_discovery_at, next_review_at
    last_success, last_error, consecutive_failures

Usage:
    python -m thaivtubersna worker            # run 24/7
    python -m thaivtubersna worker --once     # run one full cycle then exit
"""
from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from . import collect, export, review, sna
from .store import DB_PATH, connect, get_state, set_state, utc_now

logger = logging.getLogger(__name__)

# ── Default intervals (seconds) ──────────────────────────────────────────────
COLLECT_INTERVAL = 1800     # 30 minutes
REVIEW_INTERVAL  = 3600     # 1 hour
SNA_INTERVAL     = 3600     # 1 hour
EXPORT_INTERVAL  = 1800     # 30 minutes
MAX_BACKOFF      = 3600     # 1 hour cap on error backoff

# ── Graceful shutdown ────────────────────────────────────────────────────────

_stop = False


def _handle_sigterm(signum, frame):
    global _stop
    logger.info("worker: received signal %s; finishing current step then stopping", signum)
    _stop = True


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


# ── Step runner with backoff ─────────────────────────────────────────────────

def _run_step(name: str, fn: Callable, *args, **kwargs) -> dict:
    """Run a step function, catch exceptions, return result or error dict."""
    try:
        result = fn(*args, **kwargs)
        logger.info("worker: [%s] ✓  %s", name, _brief(result))
        return result
    except Exception as exc:
        logger.error("worker: [%s] ✗  %s: %s", name, type(exc).__name__, exc, exc_info=True)
        return {"error": str(exc), "step": name}


def _brief(result: dict) -> str:
    """One-line summary of a step result for logging."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("skipped"):
        return f"skipped ({result.get('reason', '?')})"
    parts = []
    for key in ("applied", "edges", "total_rows", "candidates_added"):
        if key in result:
            parts.append(f"{key}={result[key]}")
    return ", ".join(parts) if parts else str(result)[:80]


def _is_due(con, step_name: str, interval: int) -> bool:
    """Check if a step is due based on next_*_at or elapsed interval."""
    next_at_str = get_state(con, f"next_{step_name}_at")
    now = datetime.now(timezone.utc)
    if next_at_str:
        try:
            next_at = datetime.fromisoformat(next_at_str.replace("Z", "+00:00"))
            return now >= next_at
        except Exception:
            pass

    last_at_str = get_state(con, f"last_{step_name}_at")
    if not last_at_str:
        return True  # never ran yet
    try:
        last_at = datetime.fromisoformat(last_at_str.replace("Z", "+00:00"))
        return (now - last_at).total_seconds() >= interval
    except Exception:
        return True


def _record_step_result(con, step_name: str, result: dict, interval: int) -> None:
    """Update worker_state timestamps, next schedules, and error backoffs."""
    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    if "error" in result:
        failures = int(get_state(con, "consecutive_failures", 0) or 0) + 1
        set_state(con, "consecutive_failures", failures)
        set_state(con, "last_error", f"{step_name} at {now_iso}: {result['error']}")

        # Exponential backoff: 60s, 120s, 240s, 480s, ... capped at MAX_BACKOFF
        backoff_sec = min(60 * (2 ** min(failures - 1, 6)), MAX_BACKOFF)
        next_dt = now + timedelta(seconds=backoff_sec)
        next_iso = next_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        set_state(con, f"next_{step_name}_at", next_iso)
        if step_name == "collect":
            set_state(con, "next_discovery_at", next_iso)
        logger.warning(
            "worker: [%s] failed (consecutive=%d); backing off %ds until %s",
            step_name, failures, backoff_sec, next_iso
        )
    else:
        set_state(con, "consecutive_failures", 0)
        set_state(con, f"last_{step_name}_at", now_iso)
        if step_name == "collect":
            set_state(con, "last_discovery_at", now_iso)

        next_dt = now + timedelta(seconds=interval)
        next_iso = next_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        set_state(con, f"next_{step_name}_at", next_iso)
        if step_name == "collect":
            set_state(con, "next_discovery_at", next_iso)
        set_state(con, "last_success", f"{step_name} at {now_iso}")


# ── Single cycle ─────────────────────────────────────────────────────────────

def run_once(db_path=None, output_dir: Path | None = None) -> dict:
    """Run one complete 4-step cycle. Returns a dict of results."""
    path = db_path or DB_PATH
    logger.info("worker: === starting cycle at %s ===", utc_now())

    results = {}
    with connect(path) as con:
        results["collect"] = _run_step("collect", collect.run, path)
        _record_step_result(con, "collect", results["collect"], COLLECT_INTERVAL)

        results["review"] = _run_step("review", review.run, path)
        _record_step_result(con, "review", results["review"], REVIEW_INTERVAL)

        results["sna"] = _run_step("sna", sna.run, path)
        _record_step_result(con, "sna", results["sna"], SNA_INTERVAL)

        results["export"] = _run_step("export", export.run, output_dir, path)
        _record_step_result(con, "export", results["export"], EXPORT_INTERVAL)

        set_state(con, "last_cycle_at", utc_now())

    logger.info("worker: === cycle complete ===")
    return results


# ── Continuous loop ──────────────────────────────────────────────────────────

def run_loop(
    db_path=None,
    output_dir: Path | None = None,
    collect_interval: int = COLLECT_INTERVAL,
    review_interval: int = REVIEW_INTERVAL,
    sna_interval: int = SNA_INTERVAL,
    export_interval: int = EXPORT_INTERVAL,
) -> None:
    """
    24/7 loop. Runs each step when its interval has elapsed or next_*_at is reached.
    Stops gracefully on SIGTERM / SIGINT.
    """
    global _stop
    path = db_path or DB_PATH

    logger.info(
        "worker: starting 24/7 loop (collect=%ds review=%ds sna=%ds export=%ds)",
        collect_interval, review_interval, sna_interval, export_interval
    )

    steps = [
        ("collect", collect_interval, lambda: collect.run(path)),
        ("review",  review_interval,  lambda: review.run(path)),
        ("sna",     sna_interval,     lambda: sna.run(path)),
        ("export",  export_interval,  lambda: export.run(output_dir, path)),
    ]

    while not _stop:
        with connect(path) as con:
            for name, interval, func in steps:
                if _stop:
                    break
                if _is_due(con, name, interval):
                    r = _run_step(name, func)
                    _record_step_result(con, name, r, interval)

        if _stop:
            break

        # Sleep in short intervals to stay responsive to signals
        for _ in range(15):
            if _stop:
                break
            time.sleep(2)

    logger.info("worker: stopped cleanly")
