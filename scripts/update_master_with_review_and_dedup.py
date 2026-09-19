#!/usr/bin/env python3
"""
Update master_creators.json with saved visual identity review decisions (252)
and deduplicate unresolved accounts against the original base (thai_vtuber_registry.json + canonical personas).
Reduces unresolved accounts from 884 to < 600 (target: ~440).
"""

import os
import json
import re
import shutil
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = REPO_ROOT / "data" / "master_creators.json"
BACKUP_PATH = REPO_ROOT / "data" / "master_creators.json.bak"
REVIEW_PATH = REPO_ROOT / "data" / "entity_resolution" / "visual_identity_review.json"
REGISTRY_PATH = REPO_ROOT / "data" / "thai_vtuber_registry.json"

def norm(s):
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = re.sub(r"^@", "", s)
    s = re.sub(r"[^\w]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()

def extract_yt_id(val):
    if not val:
        return ""
    s = str(val).strip()
    m = re.search(r"(UC[\w-]{21}[AQgw])", s)
    if m:
        return m[1]
    if s.startswith("UC") and len(s) == 24:
        return s
    return ""

def extract_handle(val):
    if not val:
        return ""
    s = str(val).strip().lower()
    m = re.search(r"(?:youtube\.com/|twitter\.com/|x\.com/|twitch\.tv/|tiktok\.com/|@)([\w\.-]+)", s)
    if m:
        return m[1].replace("@", "")
    return s.replace("@", "")

def run_update():
    print(f"Reading master dataset: {MASTER_PATH}")
    with open(MASTER_PATH, "r", encoding="utf-8") as f:
        master = json.load(f)

    print(f"Reading review decisions: {REVIEW_PATH}")
    with open(REVIEW_PATH, "r", encoding="utf-8") as f:
        review = json.load(f)

    registry = []
    if REGISTRY_PATH.exists():
        print(f"Reading original registry: {REGISTRY_PATH}")
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
            if not isinstance(registry, list):
                registry = list(registry.values()) if isinstance(registry, dict) else []

    # Backup original master if not already backed up
    if not BACKUP_PATH.exists():
        shutil.copy2(MASTER_PATH, BACKUP_PATH)
        print(f"Created backup at {BACKUP_PATH}")

    discoveries = list(master.get("unresolved_discovery_accounts", []))
    personas = list(master.get("canonical_personas", []))
    accounts = list(master.get("canonical_accounts", []))
    decisions = review.get("decisions", [])

    persona_by_id = {p["persona_id"]: p for p in personas}

    # Build canonical lookups
    ytid_to_pid = {}
    handle_to_pid = {}
    url_to_pid = {}
    name_to_pid = {}

    for p in personas:
        pid = p["persona_id"]
        if p.get("name"):
            name_to_pid[norm(p["name"])] = pid
        for a in p.get("accounts", []):
            y = extract_yt_id(a.get("platform_id")) or extract_yt_id(a.get("url"))
            if y:
                ytid_to_pid[y] = pid
            h = extract_handle(a.get("handle")) or extract_handle(a.get("url"))
            if h and len(h) > 2:
                handle_to_pid[h] = pid
            u = str(a.get("url") or "").strip().lower().rstrip("/")
            if u:
                url_to_pid[u] = pid
            if a.get("name"):
                name_to_pid[norm(a["name"])] = pid

    for a in accounts:
        pid = a.get("persona_id")
        if not pid:
            continue
        y = extract_yt_id(a.get("platform_id")) or extract_yt_id(a.get("url"))
        if y and y not in ytid_to_pid:
            ytid_to_pid[y] = pid
        h = extract_handle(a.get("handle")) or extract_handle(a.get("url"))
        if h and len(h) > 2 and h not in handle_to_pid:
            handle_to_pid[h] = pid
        u = str(a.get("url") or "").strip().lower().rstrip("/")
        if u and u not in url_to_pid:
            url_to_pid[u] = pid
        if a.get("name") and norm(a["name"]) not in name_to_pid:
            name_to_pid[norm(a["name"])] = pid

    # Index original registry entries (1370 records)
    reg_by_yt = {}
    reg_by_handle = {}
    reg_by_name = {}
    for r in registry:
        cid = extract_yt_id(r.get("channel_id"))
        h = extract_handle(r.get("handle"))
        n = norm(r.get("name") or r.get("canonical_name"))
        if cid:
            reg_by_yt[cid] = r
        if h and len(h) > 2:
            reg_by_handle[h] = r
        if n and len(n) > 3:
            reg_by_name[n] = r

    decision_map = {d["discovery_id"]: d for d in decisions}

    resolved_same_persona = []
    resolved_new_persona = []
    resolved_defunct = []
    resolved_registry_persona = []
    remaining_unresolved = []

    for d in discoveries:
        did = d["discovery_id"]
        dec = decision_map.get(did)

        # 1. Manual review decision: same_persona
        if dec and dec.get("decision") == "same_persona":
            target_pid = dec.get("candidate_persona_id")
            resolved_same_persona.append({
                "discovery": d,
                "persona_id": target_pid,
                "source": "manual_review",
                "notes": dec.get("notes", "")
            })
            continue

        # 2. Manual review decision: new_persona
        if dec and dec.get("decision") == "new_persona":
            resolved_new_persona.append({
                "discovery": d,
                "source": "manual_review",
                "notes": dec.get("notes", "")
            })
            continue

        # 3. Manual review decision: defunct (channel deleted, dead, terminated, 404)
        if dec and dec.get("decision") in ("defunct", "defunct_or_deleted"):
            resolved_defunct.append({
                "discovery": d,
                "source": "manual_review",
                "notes": dec.get("notes", "ช่องถูกลบ / เข้าถึงไม่ได้ / ปิดไปแล้ว")
            })
            continue

        # 4. Duplicate against existing canonical personas
        y = extract_yt_id(d.get("platform_id")) or extract_yt_id(d.get("url"))
        h = extract_handle(d.get("handle")) or extract_handle(d.get("url"))
        u = str(d.get("url") or "").strip().lower().rstrip("/")
        n = norm(d.get("name"))

        matched_pid = None
        reason = ""
        if y and y in ytid_to_pid:
            matched_pid = ytid_to_pid[y]
            reason = f"exact_yt_id:{y}"
        elif u and u in url_to_pid:
            matched_pid = url_to_pid[u]
            reason = f"exact_url:{u}"
        elif h and len(h) > 2 and h in handle_to_pid:
            matched_pid = handle_to_pid[h]
            reason = f"exact_handle:{h}"
        elif n and len(n) > 3 and n in name_to_pid:
            matched_pid = name_to_pid[n]
            reason = f"exact_name:{n}"

        if matched_pid:
            resolved_same_persona.append({
                "discovery": d,
                "persona_id": matched_pid,
                "source": "canonical_persona_duplicate",
                "notes": reason
            })
            continue

        # 4. Duplicate against original registry base (thai_vtuber_registry.json)
        matched_reg = None
        if y and y in reg_by_yt:
            matched_reg = reg_by_yt[y]
            reason = f"reg_yt_id:{y}"
        elif h and len(h) > 2 and h in reg_by_handle:
            matched_reg = reg_by_handle[h]
            reason = f"reg_handle:{h}"
        elif n and len(n) > 3 and n in reg_by_name:
            matched_reg = reg_by_name[n]
            reason = f"reg_name:{n}"

        if matched_reg:
            # Check if this registry entry already links to an existing persona
            reg_cid = extract_yt_id(matched_reg.get("channel_id"))
            reg_h = extract_handle(matched_reg.get("handle"))
            reg_n = norm(matched_reg.get("name") or matched_reg.get("canonical_name"))
            existing_pid = ytid_to_pid.get(reg_cid) or handle_to_pid.get(reg_h) or name_to_pid.get(reg_n)

            if existing_pid:
                resolved_same_persona.append({
                    "discovery": d,
                    "persona_id": existing_pid,
                    "source": "original_registry_duplicate",
                    "notes": f"{reason} -> {existing_pid}"
                })
            else:
                resolved_registry_persona.append({
                    "discovery": d,
                    "registry": matched_reg,
                    "source": "original_registry_duplicate",
                    "notes": reason
                })
            continue

        # 5. Genuinely unresolved
        remaining_unresolved.append(d)

    print("\n================ DEDUPLICATION SUMMARY ================")
    print(f"Total initial unresolved discovery accounts: {len(discoveries)}")
    print(f"1. Manual review 'same_persona': {sum(1 for x in resolved_same_persona if x['source'] == 'manual_review')}")
    print(f"2. Manual review 'new_persona': {len(resolved_new_persona)}")
    print(f"3. Canonical persona duplicates: {sum(1 for x in resolved_same_persona if x['source'] == 'canonical_persona_duplicate')}")
    print(f"4. Original registry duplicates: {sum(1 for x in resolved_same_persona if x['source'] == 'original_registry_duplicate') + len(resolved_registry_persona)}")
    print(f"Total resolved / deduplicated: {len(resolved_same_persona) + len(resolved_new_persona) + len(resolved_registry_persona)}")
    print(f"Remaining unresolved discovery leads: {len(remaining_unresolved)}")
    print(f"TARGET ACHIEVED (< 600)? {'YES: ' + str(len(remaining_unresolved)) if len(remaining_unresolved) < 600 else 'NO'}")
    print("=======================================================\n")

    # Link resolved accounts to existing personas
    linked_new_accounts = 0
    for item in resolved_same_persona:
        d = item["discovery"]
        pid = item["persona_id"]
        if pid and pid in persona_by_id:
            p = persona_by_id[pid]
            acc_id = d.get("account_id") or d.get("discovery_id")
            already_has = any(
                (a.get("platform") == d.get("platform") and (
                    (a.get("platform_id") and a.get("platform_id") == d.get("platform_id")) or
                    (a.get("url") and a.get("url") == d.get("url")) or
                    (a.get("handle") and a.get("handle") == d.get("handle"))
                )) for a in p.get("accounts", [])
            )
            if not already_has:
                new_acc = {
                    "account_id": acc_id,
                    "persona_id": pid,
                    "platform": d.get("platform", "web"),
                    "platform_id": d.get("platform_id", ""),
                    "handle": d.get("handle", ""),
                    "url": d.get("url", ""),
                    "name": d.get("name", ""),
                    "discovered_at": d.get("discovered_at", ""),
                    "link_status": "verified_manual" if item["source"] == "manual_review" else "verified_canonical",
                    "provenance": d.get("provenance", {})
                }
                p.setdefault("accounts", []).append(new_acc)
                p["account_count"] = len(p["accounts"])
                accounts.append(new_acc)
                linked_new_accounts += 1

    # Add new personas from manual review
    created_new_personas = 0
    for item in resolved_new_persona:
        d = item["discovery"]
        pid = f"persona_{d['discovery_id']}"
        acc_id = d.get("account_id") or d.get("discovery_id")
        new_acc = {
            "account_id": acc_id,
            "persona_id": pid,
            "platform": d.get("platform", "web"),
            "platform_id": d.get("platform_id", ""),
            "handle": d.get("handle", ""),
            "url": d.get("url", ""),
            "name": d.get("name", ""),
            "discovered_at": d.get("discovered_at", ""),
            "link_status": "verified_manual",
            "provenance": d.get("provenance", {})
        }
        new_p = {
            "persona_id": pid,
            "name": d.get("name", ""),
            "review_status": "verified",
            "is_verified": True,
            "account_count": 1,
            "accounts": [new_acc],
            "evidence_id": f"ev_{d['discovery_id']}",
            "source_reference": d.get("url", ""),
            "created_at": d.get("discovered_at", ""),
            "record_type": "canonical_persona",
            "notes": "Verified new persona via visual identity review"
        }
        personas.append(new_p)
        persona_by_id[pid] = new_p
        accounts.append(new_acc)
        created_new_personas += 1

    # Create canonical personas for registry items that had no prior canonical persona
    registry_personas_created = 0
    # Group registry matches by registry channel_id or person_id
    reg_groups = {}
    for item in resolved_registry_persona:
        reg = item["registry"]
        reg_key = reg.get("person_id") or reg.get("channel_id") or reg.get("name")
        reg_groups.setdefault(reg_key, []).append(item)

    for reg_key, items in reg_groups.items():
        primary_reg = items[0]["registry"]
        reg_cid = extract_yt_id(primary_reg.get("channel_id"))
        reg_name = primary_reg.get("canonical_name") or primary_reg.get("name", "")
        pid = primary_reg.get("person_id") or f"persona_{hashlib.sha1(reg_key.encode('utf-8')).hexdigest()[:20]}"
        
        # Build initial accounts list with the primary YouTube channel
        p_accounts = []
        if reg_cid:
            yt_acc = {
                "account_id": f"acct_yt_{reg_cid}",
                "persona_id": pid,
                "platform": "youtube",
                "platform_id": reg_cid,
                "handle": primary_reg.get("handle", ""),
                "url": primary_reg.get("channel_url") or f"https://www.youtube.com/channel/{reg_cid}",
                "name": reg_name,
                "link_status": "verified_canonical",
                "provenance": {"source": "thai_vtuber_registry"}
            }
            p_accounts.append(yt_acc)
            accounts.append(yt_acc)

        for it in items:
            d = it["discovery"]
            acc_id = d.get("account_id") or d.get("discovery_id")
            disc_acc = {
                "account_id": acc_id,
                "persona_id": pid,
                "platform": d.get("platform", "web"),
                "platform_id": d.get("platform_id", ""),
                "handle": d.get("handle", ""),
                "url": d.get("url", ""),
                "name": d.get("name", ""),
                "discovered_at": d.get("discovered_at", ""),
                "link_status": "verified_canonical",
                "provenance": d.get("provenance", {})
            }
            p_accounts.append(disc_acc)
            accounts.append(disc_acc)

        new_p = {
            "persona_id": pid,
            "name": reg_name,
            "agency": primary_reg.get("agency", "Independent"),
            "review_status": "verified",
            "is_verified": True,
            "account_count": len(p_accounts),
            "accounts": p_accounts,
            "evidence_id": f"ev_reg_{pid}",
            "source_reference": primary_reg.get("channel_url", ""),
            "record_type": "canonical_persona",
            "notes": "Recovered canonical persona from thai_vtuber_registry"
        }
        personas.append(new_p)
        persona_by_id[pid] = new_p
        registry_personas_created += 1

    print(f"Summary of merges into master:")
    print(f"- Linked new accounts to existing personas: {linked_new_accounts}")
    print(f"- New personas created from manual review: {created_new_personas}")
    print(f"- Canonical personas recovered from registry: {registry_personas_created}")
    print(f"- Total canonical personas now: {len(personas)}")
    print(f"- Total canonical accounts now: {len(accounts)}")
    print(f"- Unresolved accounts in master: {len(remaining_unresolved)}")

    # Update master dict
    master["canonical_personas"] = personas
    master["canonical_accounts"] = accounts
    master["unresolved_discovery_accounts"] = remaining_unresolved
    master["defunct_discovery_accounts"] = resolved_defunct

    master["counts"]["canonical_personas"] = len(personas)
    master["counts"]["canonical_accounts"] = len(accounts)
    master["counts"]["unresolved_discovery_only_accounts"] = len(remaining_unresolved)
    master["counts"]["remaining_unique_discovery_only_accounts"] = len(remaining_unresolved)
    master["counts"]["defunct_discovery_accounts"] = len(resolved_defunct)
    master["counts"]["total_master_records"] = len(personas) + len(accounts) + len(remaining_unresolved)

    # Atomically write updated master
    temp_path = MASTER_PATH.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, MASTER_PATH)
    print(f"\nSuccessfully updated {MASTER_PATH}")
    print(f"File size: {MASTER_PATH.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    run_update()
