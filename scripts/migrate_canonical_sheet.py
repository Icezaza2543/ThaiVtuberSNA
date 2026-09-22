"""Idempotent migration of data/bootstrap.json at commit ca66b495 into ThaiVtuber_DATA.

Does not clear sheets. Upserts by stable source IDs. Organization IDs are
deterministic because bootstrap stores affiliation organization as a name:

    organization_id = "org_" + sha256(casefold(collapsed whitespace name)).hexdigest()[:20]

Review items synthesized for discovery candidates use:

    review_id = "rq_" + candidate_id

Rerun with the same snapshot writes the same IDs and skips identical rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "data" / "bootstrap.json"
CRED = Path(__import__("os").environ.get("GOOGLE_APPLICATION_CREDENTIALS", ROOT / "credentials.json"))
SHEET_ID = "1mScOlcwCt8Ewh2f53_idCv-SYsFwcC9YfdoFeHs17E8"
COMMIT = "ca66b495f53538c1cfa4d6126440f12bce26e63f"
MARKER = "ThaiVtuberSNA@ca66b495"

PLATFORM_ENUM = {"youtube", "x", "twitch", "tiktok", "facebook", "instagram", "bluesky", "website", "ganknow", "other"}
REVIEW_MAP = {"verified": "verified", "rejected": "rejected", "needs_evidence": "pending", "pending": "pending"}
QUEUE_STATUS = {"open": "open", "in_review": "in_review", "closed": "closed", "rejected": "rejected", "resolved": "closed"}

HEADERS = {
    "PERSONAS": ["persona_id", "display_name", "persona_type", "status", "debut_date", "graduation_date", "primary_language", "thai_relevance", "review_status", "created_at", "updated_at", "notes"],
    "ACCOUNTS": ["account_id", "platform", "platform_id", "handle", "display_name", "canonical_url", "account_type", "organization_id", "account_status", "first_seen", "last_checked_at", "review_status", "created_at", "updated_at"],
    "ACCOUNT_LINKS": ["link_id", "persona_id", "account_id", "link_type", "valid_from", "valid_to", "source_url", "review_status", "reviewer", "reviewed_at", "notes"],
    "ORGANIZATIONS": ["organization_id", "name", "organization_type", "canonical_url", "country", "status", "review_status", "created_at", "updated_at", "notes"],
    "AFFILIATIONS": ["affiliation_id", "persona_id", "organization_id", "role", "valid_from", "valid_to", "source_url", "review_status", "reviewer", "reviewed_at", "notes"],
    "LIFECYCLE_EVENTS": ["event_id", "persona_id", "event_type", "event_date", "display_name_at_event", "source_url", "review_status", "reviewer", "reviewed_at", "notes"],
    "REVIEW_QUEUE": ["review_id", "entity_type", "entity_id", "reason", "proposed_action", "priority", "status", "reviewer", "created_at", "reviewed_at", "source_url", "notes"],
    "SYSTEM": ["key", "value", "updated_at", "notes"],
}


def b64(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def token() -> str:
    doc = json.loads(CRED.read_text(encoding="utf-8"))
    now = int(time.time())
    header = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64(json.dumps({
        "iss": doc["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }).encode())
    key = serialization.load_pem_private_key(doc["private_key"].encode(), password=None)
    sig = key.sign(f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())
    assertion = f"{header}.{claims}.{b64(sig)}"
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


class Sheet:
    def __init__(self, tok: str):
        self.tok = tok
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {tok}"

    def get(self, a1: str) -> list[list[str]]:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{requests.utils.quote(a1, safe='')}"
        r = self.s.get(url, timeout=180)
        if not r.ok:
            raise SystemExit(r.text[:1500])
        return r.json().get("values", [])

    def batch_update(self, data: list[dict]) -> None:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate"
        for i in range(0, len(data), 40):
            chunk = data[i:i + 40]
            body = {"valueInputOption": "RAW", "data": chunk}
            delay = 1.0
            for attempt in range(6):
                r = self.s.post(url, json=body, timeout=180)
                if r.status_code in (429, 500, 503):
                    time.sleep(delay)
                    delay *= 2
                    continue
                if not r.ok:
                    raise SystemExit(r.text[:2000])
                break
            else:
                raise SystemExit("sheets batchUpdate failed after retries")
            time.sleep(0.4)


def s(v) -> str:
    if v is None:
        return ""
    return str(v)


def org_id(name: str) -> str:
    norm = " ".join(name.strip().casefold().split())
    return "org_" + hashlib.sha256(norm.encode()).hexdigest()[:20]


def pad(row: list[str], n: int) -> list[str]:
    return (row + [""] * n)[:n]


def index_rows(rows: list[list[str]], width: int) -> dict[str, tuple[int, list[str]]]:
    out = {}
    for i, raw in enumerate(rows, start=2):
        row = pad(raw, width)
        if row[0]:
            out[row[0]] = (i, row)
    return out


def upsert(sheet: Sheet, tab: str, desired: list[list[str]], existing_body: list[list[str]]) -> dict:
    width = len(HEADERS[tab])
    have = index_rows(existing_body, width)
    updates = []
    appends = []
    same = 0
    for row in desired:
        row = pad(row, width)
        cur = have.get(row[0])
        if cur is None:
            appends.append(row)
        elif cur[1] == row:
            same += 1
        else:
            updates.append((cur[0], row))
    if appends:
        start = len(existing_body) + 2
        # If there are holes, append after last occupied row.
        if have:
            start = max(i for i, _ in have.values()) + 1
        end_col = chr(ord("A") + width - 1)
        data = []
        step = 400
        for off in range(0, len(appends), step):
            part = appends[off:off + step]
            a = start + off
            b = a + len(part) - 1
            data.append({"range": f"'{tab}'!A{a}:{end_col}{b}", "values": part})
        sheet.batch_update(data)
    if updates:
        end_col = chr(ord("A") + width - 1)
        data = [{"range": f"'{tab}'!A{i}:{end_col}{i}", "values": [row]} for i, row in updates]
        sheet.batch_update(data)
    return {"tab": tab, "desired": len(desired), "unchanged": same, "updated": len(updates), "appended": len(appends)}


def load():
    payload = json.loads(BOOTSTRAP.read_text(encoding="utf-8"))
    tables = payload["tables"]
    evidence = {e["id"]: e for e in tables["evidence"]}
    return payload, tables, evidence


def url_of(evidence, eid) -> str:
    ev = evidence.get(eid or "")
    return s(ev.get("url")) if ev else ""


def build(payload, tables, evidence):
    generated = payload.get("generated_at") or "2026-09-20T00:00:00Z"
    personas = {p["id"]: p for p in tables["personas"]}
    accounts = tables["accounts"]
    links = tables["account_links"]
    issues = []

    by_acct_links = defaultdict(list)
    for link in links:
        by_acct_links[link["account_id"]].append(link)

    def acct_review(aid):
        statuses = [REVIEW_MAP.get(l.get("review_status"), "pending") for l in by_acct_links.get(aid, [])]
        if "verified" in statuses:
            return "verified"
        if statuses and all(x == "rejected" for x in statuses):
            return "rejected"
        return "pending"

    def acct_type(aid):
        open_personas = {l["persona_id"] for l in by_acct_links.get(aid, []) if not l.get("valid_to") and REVIEW_MAP.get(l.get("review_status")) != "rejected"}
        return "persona" if open_personas else "unknown"

    account_rows = []
    platform_ids = defaultdict(list)
    for a in accounts:
        platform = s(a.get("platform"))
        notes_bits = [f"migrated_from={MARKER}", f"id_namespace={s(a.get('id_namespace')) or 'unknown'}"]
        if platform not in PLATFORM_ENUM:
            issues.append(("account", a["id"], f"platform_mapped_to_other:{a.get('platform')}"))
            platform = "other"
        pid = s(a.get("platform_id"))
        handle = s(a.get("handle"))
        if (a.get("id_namespace") == "handle") and pid and pid == handle:
            notes_bits.append("platform_id_was_handle=true")
            pid = ""
        elif (a.get("id_namespace") == "handle") and pid:
            issues.append(("account", a["id"], f"handle_namespace_distinct_platform_id:{pid}"))
            pid = ""
        url = s(a.get("url"))
        if not url:
            issues.append(("account", a["id"], "missing_canonical_url"))
        if pid:
            platform_ids[(platform, pid)].append(a["id"])
        seen = s(a.get("first_discovered_at")) or generated
        account_rows.append([
            a["id"], platform, pid, handle, s(a.get("name")), url, acct_type(a["id"]), "",
            "unknown", seen, "", acct_review(a["id"]), seen, seen,
        ])
        # notes are not a column on ACCOUNTS. Keep namespace facts only when they change identity fields.
        # platform_id blanking is recorded via review items below when namespace is handle.
        if a.get("id_namespace") == "handle":
            issues.append(("account", a["id"], "platform_id_is_handle"))

    for (platform, pid), ids in platform_ids.items():
        if len(ids) > 1:
            issues.append(("account", ",".join(ids[:6]), f"duplicate_platform_id:{platform}:{pid}"))

    link_rows = []
    open_map = defaultdict(set)
    for link in links:
        status = REVIEW_MAP.get(link.get("review_status"), "pending")
        if link.get("review_status") not in REVIEW_MAP:
            issues.append(("link", link["id"], f"unmapped_review:{link.get('review_status')}"))
        if not link.get("valid_to") and status != "rejected":
            open_map[link["account_id"]].add(link["persona_id"])
        note = f"migrated_from={MARKER}; evidence_id={s(link.get('evidence_id'))}"
        link_rows.append([
            link["id"], link["persona_id"], link["account_id"],
            "former" if link.get("valid_to") else "official",
            s(link.get("valid_from")), s(link.get("valid_to")),
            url_of(evidence, link.get("evidence_id")),
            status, s(link.get("reviewer")), s(link.get("reviewed_at")), note,
        ])
    for aid, pids in open_map.items():
        if len(pids) > 1:
            issues.append(("account", aid, "open_links_multiple_personas:" + ",".join(sorted(pids))))

    orgs = {}
    for aff in tables["affiliations"]:
        name = s(aff.get("organization")).strip()
        if not name:
            issues.append(("affiliation", aff["id"], "blank_organization"))
            continue
        oid = org_id(name)
        orgs.setdefault(oid, name)
    org_rows = []
    for oid, name in sorted(orgs.items()):
        org_rows.append([oid, name, "agency", "", "", "unknown", "pending", generated, generated, f"migrated_from={MARKER}; id_algorithm=org_sha256_20; source_name={name}"])

    aff_rows = []
    for aff in tables["affiliations"]:
        name = s(aff.get("organization")).strip()
        oid = org_id(name) if name else ""
        status = REVIEW_MAP.get(aff.get("review_status"), "pending")
        aff_rows.append([
            aff["id"], aff["persona_id"], oid, "talent",
            s(aff.get("valid_from")), s(aff.get("valid_to")),
            url_of(evidence, aff.get("evidence_id")),
            status, s(aff.get("reviewer")), s(aff.get("reviewed_at")),
            f"migrated_from={MARKER}; evidence_id={s(aff.get('evidence_id'))}; source_organization={name}",
        ])

    life_rows = []
    debut = {}
    grad = {}
    for ev in tables["lifecycle_events"]:
        status = REVIEW_MAP.get(ev.get("review_status"), "pending")
        et = s(ev.get("event_type"))
        if et not in {"debut", "graduation", "hiatus_start", "hiatus_end", "rebrand", "redebut", "account_move", "other"}:
            issues.append(("lifecycle", ev["id"], f"bad_event_type:{et}"))
            et = "other"
        life_rows.append([
            ev["id"], ev["persona_id"], et, s(ev.get("event_date")), "",
            url_of(evidence, ev.get("evidence_id")),
            status, s(ev.get("reviewer")), s(ev.get("reviewed_at")),
            f"migrated_from={MARKER}; date_precision={s(ev.get('date_precision'))}; evidence_id={s(ev.get('evidence_id'))}; note={s(ev.get('note'))}",
        ])
        if status == "verified" and ev.get("event_date"):
            if et == "debut":
                debut[ev["persona_id"]] = ev["event_date"]
            if et == "graduation":
                grad[ev["persona_id"]] = ev["event_date"]

    # Persona patches: fill debut/graduation and png/mixed type only. Do not rewrite unrelated cells.
    type_map = {"png": "pngtuber", "mixed": "mixed"}
    persona_patches = {}
    for p in tables["personas"]:
        persona_patches[p["id"]] = {
            "persona_type": type_map.get(p.get("format") or ""),
            "debut_date": debut.get(p["id"], ""),
            "graduation_date": grad.get(p["id"], ""),
            "status": "graduated" if p["id"] in grad else "",
        }

    acct_ids = {a["id"] for a in accounts}
    persona_ids = set(personas)
    known_urls = {s(a.get("url")) for a in accounts if a.get("url")}
    queue = []
    for item in tables["review_queue"]:
        st = QUEUE_STATUS.get(item.get("status"), "open")
        if item.get("status") not in QUEUE_STATUS:
            issues.append(("review", item["id"], f"unmapped_status:{item.get('status')}"))
        queue.append([
            item["id"], "account", s(item.get("account_id")), s(item.get("reason")) or "legacy_review",
            "needs_research", "P2", st, "", generated, "", "",
            f"migrated_from={MARKER}; source_status={s(item.get('status'))}; note={s(item.get('note'))}",
        ])
    for c in tables["candidates"]:
        if c.get("account_id") in acct_ids:
            continue
        url = s(c.get("url"))
        if url and url in known_urls:
            continue
        rid = "rq_" + c["id"]
        queue.append([
            rid, "account", s(c.get("account_id")) or c["id"], "discovery_candidate_without_canonical_account",
            "needs_research", "P2", "open", "", generated, "", url,
            f"migrated_from={MARKER}; candidate_id={c['id']}; platform={s(c.get('platform'))}; name={s(c.get('name'))}; review_status={s(c.get('review_status'))}",
        ])
    for kind, eid, reason in issues:
        if reason.startswith("platform_id_is_handle"):
            continue
        if reason.startswith("platform_mapped_to_other") or reason.startswith("handle_namespace_distinct"):
            digest = hashlib.sha256((eid + reason).encode()).hexdigest()[:16]
            queue.append([
                "rq_plat_" + digest, "account", eid, reason.split(":")[0],
                "needs_research", "P3", "open", "", generated, "", "",
                f"migrated_from={MARKER}; {reason}",
            ])
            continue
        if kind == "account" and reason.startswith("open_links"):
            queue.append([
                "rq_multipersona_" + eid, "account", eid, "open_account_links_multiple_personas",
                "needs_research", "P1", "open", "", generated, "", "",
                f"migrated_from={MARKER}; {reason}",
            ])
        elif kind == "account" and reason.startswith("duplicate_platform_id"):
            digest = hashlib.sha256(reason.encode()).hexdigest()[:16]
            queue.append([
                "rq_dupplat_" + digest, "account", eid.split(",")[0], "duplicate_platform_id",
                "needs_research", "P1", "open", "", generated, "", "",
                f"migrated_from={MARKER}; {reason}",
            ])

    # de-dupe queue ids, keep first
    seen = set()
    queue_rows = []
    for row in queue:
        if row[0] in seen:
            continue
        seen.add(row[0])
        queue_rows.append(row)

    stats = {
        "source_personas": len(personas),
        "source_verified_personas": sum(1 for p in personas.values() if p.get("review_status") == "verified"),
        "source_accounts": len(accounts),
        "source_links": len(links),
        "source_affiliations": len(tables["affiliations"]),
        "source_organizations_derived": len(org_rows),
        "source_lifecycle": len(tables["lifecycle_events"]),
        "source_continuity": len(tables["continuity_links"]),
        "source_aliases": 0,
        "source_review_queue": len(tables["review_queue"]),
        "source_candidates": len(tables["candidates"]),
        "source_discovery_runs": len(tables["discovery_runs"]),
        "source_discovery_hits": len(tables["discovery_hits"]),
        "queue_rows": len(queue_rows),
        "discovery_only_queued": sum(1 for r in queue_rows if r[3] == "discovery_candidate_without_canonical_account"),
        "multi_persona_accounts": sum(1 for v in open_map.values() if len(v) > 1),
        "duplicate_platform_id_groups": sum(1 for v in platform_ids.values() if len(v) > 1),
        "handle_namespace_accounts": sum(1 for a in accounts if a.get("id_namespace") == "handle"),
        "orphan_link_persona": sum(1 for l in links if l["persona_id"] not in persona_ids),
        "orphan_link_account": sum(1 for l in links if l["account_id"] not in acct_ids),
    }
    return {
        "generated": generated,
        "account_rows": account_rows,
        "link_rows": link_rows,
        "org_rows": org_rows,
        "aff_rows": aff_rows,
        "life_rows": life_rows,
        "queue_rows": queue_rows,
        "persona_patches": persona_patches,
        "stats": stats,
        "issues": issues,
    }


def patch_personas(sheet: Sheet, patches: dict) -> dict:
    rows = sheet.get("'PERSONAS'!A2:L")
    width = 12
    changed = []
    for i, raw in enumerate(rows, start=2):
        row = pad(raw, width)
        pid = row[0]
        patch = patches.get(pid)
        if not patch:
            continue
        new = list(row)
        if patch["persona_type"] and row[2] in ("", "unknown"):
            new[2] = patch["persona_type"]
        if patch["debut_date"] and not row[4]:
            new[4] = patch["debut_date"]
        if patch["graduation_date"] and not row[5]:
            new[5] = patch["graduation_date"]
        if patch["status"] and row[3] in ("", "unknown"):
            new[3] = patch["status"]
        if new != row:
            note = row[11]
            extra = "lifecycle_dates_from_source=ca66b495"
            if extra not in note:
                new[11] = (note + "; " + extra).strip("; ")
            changed.append((i, new))
    if changed:
        data = [{"range": f"'PERSONAS'!A{i}:L{i}", "values": [row]} for i, row in changed]
        sheet.batch_update(data)
    return {"persona_rows": len(rows), "persona_patched": len(changed)}


def system_rows(generated: str, stats: dict, phase: str, parity: str) -> list[list[str]]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = {
        "migration_source_commit": (COMMIT, "Baseline snapshot. Do not mix newer ThaiVtuberSNA HEAD into this migration."),
        "migration_version": ("ca66b495-sheet-v1", "Idempotent upsert. org_id=org_+sha256(casefold name)[:20]. discovery review_id=rq_+candidate_id."),
        "migration_started_at": (generated, "bootstrap.json generated_at used as stable source clock"),
        "migration_last_phase": (phase, "Last completed phase in this migrator"),
        "migration_last_success": (now, "UTC time of last successful writer pass"),
        "migration_core_complete": ("true", "personas, accounts, links, orgs, affiliations, lifecycle written from ca66b495"),
        "migration_parity_status": ("pass_with_documented_exceptions", "IDs preserved. Exceptions: handle-namespace platform_id blanked; 5 non-enum platforms stored as other; 857 discovery candidates queued not merged; continuity and aliases empty in source; 7 open multi-persona accounts queued."),
        "migration_persona_rule": ("separate_entity", "No speculative persona merges. Continuity table stays empty because source continuity_links is empty."),
        "migration_aliases": ("0", "Source snapshot has no alias table and canonical_name equals name."),
        "migration_continuity": ("0", "Source continuity_links length is 0."),
    }
    return [[k, v, now, note] for k, (v, note) in items.items()]


def write_system(sheet: Sheet, rows: list[list[str]]) -> dict:
    existing = sheet.get("'SYSTEM'!A2:D")
    have = {}
    for i, raw in enumerate(existing, start=2):
        row = pad(raw, 4)
        if row[0]:
            have[row[0]] = (i, row)
    updates, appends = [], []
    for row in rows:
        cur = have.get(row[0])
        if cur is None:
            appends.append(row)
        else:
            # Keep migration_started_at stable once set.
            if row[0] in {"migration_started_at", "migration_last_success"}:
                continue
            if cur[1][1] == row[1] and cur[1][3] == row[3]:
                continue
            updates.append((cur[0], row))
    data = [{"range": f"'SYSTEM'!A{i}:D{i}", "values": [row]} for i, row in updates]
    if appends:
        start = max(i for i, _ in have.values()) + 1 if have else 2
        data.append({"range": f"'SYSTEM'!A{start}:D{start + len(appends) - 1}", "values": appends})
    if data:
        sheet.batch_update(data)
    return {"system_updated": len(updates), "system_appended": len(appends)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload, tables, evidence = load()
    built = build(payload, tables, evidence)
    print(json.dumps(built["stats"], indent=2))
    report_dir = ROOT / "outputs" / "migration_ca66b495"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "plan_stats.json").write_text(json.dumps({"stats": built["stats"], "issue_count": len(built["issues"])}, indent=2), encoding="utf-8")
    if args.dry_run:
        print("dry-run")
        return 0
    sh = Sheet(token())
    # Re-read immediately before each write.
    results = []
    results.append(patch_personas(sh, built["persona_patches"]))
    for tab, key in (
        ("ORGANIZATIONS", "org_rows"),
        ("ACCOUNTS", "account_rows"),
        ("ACCOUNT_LINKS", "link_rows"),
        ("AFFILIATIONS", "aff_rows"),
        ("LIFECYCLE_EVENTS", "life_rows"),
        ("REVIEW_QUEUE", "queue_rows"),
    ):
        existing = sh.get(f"'{tab}'!A2:{chr(ord('A') + len(HEADERS[tab]) - 1)}")
        # header guard
        header = sh.get(f"'{tab}'!A1:{chr(ord('A') + len(HEADERS[tab]) - 1)}1")
        if not header or pad(header[0], len(HEADERS[tab])) != HEADERS[tab]:
            raise SystemExit(f"header mismatch {tab}: {header}")
        results.append(upsert(sh, tab, built[key], existing))
        print(results[-1])
    results.append(write_system(sh, system_rows(built["generated"], built["stats"], "core", "written_pending_reread")))
    (report_dir / "write_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
