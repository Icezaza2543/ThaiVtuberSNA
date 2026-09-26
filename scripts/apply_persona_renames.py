"""Apply reviewed persona display-name changes to ThaiVtuber_DATA.

Input JSON: [{"persona_id": "...", "expected_name": "...", "new_name": "...", "reason": "..."}]
A row is changed only if its current display_name equals expected_name.
Dry-run unless --write.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from migrate_canonical_sheet import Sheet, pad, token, upsert  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changes = json.loads(Path(args.file).read_text(encoding="utf-8"))
    sh = Sheet(token())
    raw = sh.get("'PERSONAS'!A2:L")
    rows = {pad(r, 12)[0]: list(pad(r, 12)) for r in raw if r}
    out = []
    for c in changes:
        p = rows.get(c["persona_id"])
        if not p or p[1] != c["expected_name"]:
            print("skip", c["persona_id"], "current:", p and p[1])
            continue
        p[11] += f"; renamed_from={p[1]} ({c.get('reason', '')})"
        p[1], p[10] = c["new_name"], now
        out.append(p)
        print(c["expected_name"], "->", c["new_name"])
    if args.write and out:
        print(upsert(sh, "PERSONAS", out, raw))
    elif not args.write:
        print("dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
