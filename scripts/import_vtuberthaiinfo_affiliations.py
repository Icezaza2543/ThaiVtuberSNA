"""Import VtuberThaiInfo agency/group memberships into ORGANIZATIONS + AFFILIATIONS.

Trusted base (owner decision 2026-09-26). Talent -> persona by stable account ID
(same matching as import_vtuberthaiinfo_base). Organizations reuse an existing
row when the name matches exactly (case-insensitive), else a new row keyed by the
VtuberThaiInfo affiliate id. Dates keep their source precision (YYYY, YYYY-MM or
YYYY-MM-DD); a missing year means no date. Existing (persona, organization)
affiliations are left untouched.

Dry-run unless --write. Append only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import SOURCE, Index, fetch_talents, sha, talent_accounts  # noqa: E402
from migrate_canonical_sheet import Sheet, pad, token, upsert  # noqa: E402

REVIEWER = "owner:vtuberthaiinfo-base"
MARKER = "vtuberthaiinfo_affiliations"
ORG_TYPE = {"AFFILIATE": "agency", "GROUP": "group"}


def date(y, m, d) -> str:
    if not y:
        return ""
    if m and d:
        return f"{y:04d}-{m:02d}-{d:02d}"
    return f"{y:04d}-{m:02d}" if m else f"{y:04d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    talents = fetch_talents()
    sh = Sheet(token())
    idx = Index(sh)
    status = {pad(r, 12)[0]: pad(r, 12)[8] for r in idx.raw["PERSONAS"] if r}
    org_raw = sh.get("'ORGANIZATIONS'!A2:J")
    aff_raw = sh.get("'AFFILIATIONS'!A2:K")
    org_by_name = {pad(r, 10)[1].casefold(): pad(r, 10)[0] for r in org_raw if r}
    have_aff = {(pad(r, 11)[1], pad(r, 11)[2]) for r in aff_raw if r}
    orgs, affs, skipped = {}, {}, {"no_persona": 0, "ambiguous_persona": 0, "no_affiliate": 0, "exists": 0}

    for t in talents:
        if not t.get("transfers"):
            continue
        aids = [idx.account(a) for a in talent_accounts(t)]
        ps = {p for a in aids if a for p in idx.personas_of[a] if status.get(p) == "verified"}
        if len(ps) != 1:
            skipped["no_persona" if not ps else "ambiguous_persona"] += len(t["transfers"])
            continue
        pid = ps.pop()
        for tr in t["transfers"]:
            aff = tr.get("affiliate")
            if not aff:
                skipped["no_affiliate"] += 1
                continue
            oid = org_by_name.get(aff["name"].casefold())
            if not oid:
                oid = "org_" + sha(f"vti-org:{aff['id']}")
                org_by_name[aff["name"].casefold()] = oid
                orgs[oid] = [oid, aff["name"], ORG_TYPE.get(aff.get("type"), "unknown"), "", "", "unknown",
                             "verified", now, now, f"{MARKER}; vti_affiliate_id={aff['id']}; slug={aff.get('slug')}"]
            if (pid, oid) in have_aff:
                skipped["exists"] += 1
                continue
            have_aff.add((pid, oid))
            ended = date(tr.get("yearOut"), tr.get("monthOut"), tr.get("dayOut"))
            affid = "aff_" + sha(f"vti-transfer:{tr['id']}")
            affs[affid] = [affid, pid, oid, "talent", date(tr.get("yearIn"), tr.get("monthIn"), tr.get("dayIn")),
                           ended, f"{SOURCE}/{t['slug']}", "verified", REVIEWER, now,
                           f"{MARKER}; vti_transfer_id={tr['id']}; vti_is_active={tr.get('isActive')}"]

    print(json.dumps({"organizations": len(orgs), "affiliations": len(affs), "skipped": skipped}))
    if not args.write:
        print("dry-run")
        return 0
    if orgs:
        print(upsert(sh, "ORGANIZATIONS", list(orgs.values()), org_raw))
    if affs:
        print(upsert(sh, "AFFILIATIONS", list(affs.values()), aff_raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
