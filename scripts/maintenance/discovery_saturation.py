"""Measure retrospective novelty in discovery-web batch JSONL files.

This analyzes recorded observations, not rejected search attempts. It therefore
measures observation novelty and must not be presented as a census estimate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
BATCH_RE = re.compile(r"discovery-web-batch-(\d+)\.jsonl$")


def normalize_url(value: str) -> str:
    return str(value or "").strip().rstrip("/").casefold()


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def batch_files(root: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for path in (root / "intake").glob("*-discovery-web-batch-*.jsonl"):
        match = BATCH_RE.search(path.name)
        if match:
            found.append((int(match.group(1)), path))
    found.sort(key=lambda item: item[0])
    seen: set[int] = set()
    duplicates = [batch for batch, _ in found if batch in seen or seen.add(batch)]
    if duplicates:
        raise SystemExit(f"duplicate discovery batch numbers: {sorted(set(duplicates))}")
    return found


def read_rows(path: Path):
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL {path}:{line_number}: {exc}") from exc
        yield row


def analyze(
    root: Path,
    window_size: int,
    start_batch: int | None,
    end_batch: int | None,
):
    files = batch_files(root)
    if not files:
        raise SystemExit("no discovery web batch files found")
    min_batch, max_batch = files[0][0], files[-1][0]
    report_start = start_batch if start_batch is not None else min_batch
    report_end = end_batch if end_batch is not None else max_batch
    if window_size < 1:
        raise SystemExit("--window-size must be >= 1")
    if report_start > report_end:
        raise SystemExit("--start-batch must be <= --end-batch")

    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    windows: dict[int, dict] = {}
    total_rows = 0

    for batch, path in files:
        if batch > report_end:
            break
        in_report = batch >= report_start
        window_key = (batch - report_start) // window_size if in_report else None
        if in_report:
            bucket = windows.setdefault(
                window_key,
                {
                    "start_batch": batch,
                    "end_batch": batch,
                    "rows": 0,
                    "unique_urls": set(),
                    "unique_names": set(),
                    "new_urls": set(),
                    "new_names": set(),
                    "platforms": Counter(),
                },
            )
            bucket["end_batch"] = batch

        for row in read_rows(path):
            url = normalize_url(row.get("url", ""))
            name = normalize_name(row.get("name", ""))
            if in_report:
                total_rows += 1
                bucket["rows"] += 1
                bucket["platforms"][str(row.get("platform", "unknown"))] += 1
                if url:
                    bucket["unique_urls"].add(url)
                    if url not in seen_urls:
                        bucket["new_urls"].add(url)
                if name:
                    bucket["unique_names"].add(name)
                    if name not in seen_names:
                        bucket["new_names"].add(name)
            if url:
                seen_urls.add(url)
            if name:
                seen_names.add(name)

    output = []
    for key in sorted(windows):
        bucket = windows[key]
        rows = bucket["rows"]
        output.append(
            {
                "start_batch": bucket["start_batch"],
                "end_batch": bucket["end_batch"],
                "rows": rows,
                "unique_urls": len(bucket["unique_urls"]),
                "new_urls": len(bucket["new_urls"]),
                "url_novelty_per_row": (
                    len(bucket["new_urls"]) / rows if rows else 0.0
                ),
                "unique_name_proxies": len(bucket["unique_names"]),
                "new_name_proxies": len(bucket["new_names"]),
                "name_novelty_per_row": (
                    len(bucket["new_names"]) / rows if rows else 0.0
                ),
                "platforms": dict(bucket["platforms"].most_common()),
            }
        )
    return {
        "semantics": (
            "retrospective recorded-observation novelty; "
            "not search-attempt yield or census coverage"
        ),
        "available_batch_range": [min_batch, max_batch],
        "reported_batch_range": [report_start, report_end],
        "window_size": window_size,
        "reported_rows": total_rows,
        "windows": output,
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Discovery saturation (retrospective observation novelty)",
        "",
        (
            "> This measures recorded discovery rows only. It does not include "
            "rejected/known search attempts and is not a census estimate."
        ),
        "",
        (
            "| Batches | Rows | Unique URLs | First-seen URLs | URL novelty | "
            "Unique name proxies | First-seen names | Name novelty | Platforms |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["windows"]:
        platforms = ", ".join(
            f"{key} {value}" for key, value in row["platforms"].items()
        )
        lines.append(
            f"| {row['start_batch']}–{row['end_batch']} | {row['rows']} | "
            f"{row['unique_urls']} | {row['new_urls']} | "
            f"{row['url_novelty_per_row']:.1%} | "
            f"{row['unique_name_proxies']} | {row['new_name_proxies']} | "
            f"{row['name_novelty_per_row']:.1%} | {platforms} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-size", type=int, default=12)
    parser.add_argument("--start-batch", type=int)
    parser.add_argument("--end-batch", type=int)
    parser.add_argument("--format", choices=("json", "md"), default="md")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(ROOT, args.window_size, args.start_batch, args.end_batch)
    rendered = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.format == "json"
        else render_markdown(result)
    )
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
