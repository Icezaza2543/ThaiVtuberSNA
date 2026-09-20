"""Build Task 8 Twitch identity research from reviewed evidence.

This collector is intentionally conservative.  It never merges by display name,
handle similarity, agency membership, or video thumbnail.  A Twitch account joins
an existing persona only when one of these evidence paths exists:

1. the exact Twitch URL was already recorded as an official account on a resolved
   discovery row;
2. the corrected trusted registry already has a verified exact account link; or
3. the public Twitch profile exposes an outgoing official URL that exactly matches
   a previously resolved/trusted official account.

Everything else remains a separate new persona with positive Twitch-profile
identity evidence.  Ambiguous cross-links fail closed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

OFFICIAL_KINDS = {"official_profile", "official_website", "self_statement", "youtube_api"}
FIXED_REVIEWED_AT = "2026-09-19T00:00:00Z"


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def account_key(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError(f"invalid account URL: {value}")
    if host.startswith("www."):
        host = host[4:]
    host = {"twitter.com": "x.com", "m.youtube.com": "youtube.com"}.get(host, host)
    path = parsed.path.rstrip("/") or "/"
    if host in {"x.com", "twitch.tv", "tiktok.com", "instagram.com"}:
        path = path.casefold()
    return urlunsplit(("https", host, path, parsed.query, ""))


def clean_url(value: str) -> str:
    value = html.unescape(value.strip()).replace("\\/", "/")
    value = value.replace("\\u002F", "/").replace("\\u002f", "/")
    value = value.replace("\\u0026", "&")
    if not value.startswith(("http://", "https://")):
        raise ValueError(value)
    return value


def canonical_name(row: dict) -> str:
    for key in ("canonical_name", "display_name", "name", "handle", "title"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    path = urlsplit(row["url"]).path.strip("/")
    if path:
        return path.split("/")[0]
    raise ValueError(f"missing canonical name for {row.get('discovery_id')}")


class TwitchHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta":
            key = values.get("property") or values.get("name")
            if key == "og:title" and values.get("content"):
                self.title = html.unescape(values["content"])
            elif key in {"og:description", "description"} and values.get("content") and not self.description:
                self.description = html.unescape(values["content"])
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])


def extract_urls(raw: str) -> list[str]:
    found = set()
    parser = TwitchHTML()
    try:
        parser.feed(raw)
    except Exception:
        pass
    for value in parser.links:
        try:
            found.add(clean_url(value))
        except ValueError:
            pass
    patterns = [
        r'https?://[^\s"\'<>]+',
        r'https?:\\/\\/[^\s"\'<>]+',
        r'https?:\\u002F\\u002F[^\s"\'<>]+',
    ]
    for pattern in patterns:
        for value in re.findall(pattern, raw, flags=re.I):
            try:
                found.add(clean_url(value))
            except ValueError:
                pass
    return sorted(found), parser.title, parser.description


def fetch_twitch_profile(url: str, timeout: float) -> dict:
    attempts = []
    base = url.rstrip("/")
    for target in (base + "/about", base):
        try:
            request = Request(target, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ThaiVtuberSNA identity-review/1.0)",
                "Accept-Language": "th,en;q=0.8",
            })
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(4_000_000).decode("utf-8", errors="replace")
                links, title, description = extract_urls(raw)
                return {
                    "status": getattr(response, "status", 200),
                    "source_url": target,
                    "title": title,
                    "description": description,
                    "links": links,
                }
        except HTTPError as exc:
            attempts.append({"url": target, "status": exc.code})
        except (URLError, TimeoutError, OSError) as exc:
            attempts.append({"url": target, "error": type(exc).__name__})
    return {"status": None, "source_url": url, "title": None, "description": None,
            "links": [], "attempts": attempts}


def reviewed_profile_evidence(row: dict, profile: dict, name: str) -> dict:
    title = profile.get("title")
    description = profile.get("description")
    if title or description:
        parts = [f"The public Twitch profile identifies the accepted account for {name}."]
        if title:
            parts.append(f"Visible profile title: {title!r}.")
        if description:
            excerpt = " ".join(description.split())[:360]
            parts.append(f"Visible profile description excerpt: {excerpt!r}.")
        parts.append("Names and agency labels are not used as cross-platform merge evidence.")
        method = "direct_public_twitch_profile"
    else:
        reason = row.get("reason") or row.get("review_reason") or ""
        parts = [
            f"The accepted review record retains {row['url']} as the owner-controlled Twitch account for {name}.",
            "This evidence establishes only the Twitch account/persona identity; it does not merge another account from name or agency similarity.",
        ]
        if reason:
            parts.append("Review basis: " + " ".join(str(reason).split())[:360])
        method = "retained_reviewed_twitch_profile"
    evidence = {
        "source_url": row["url"],
        "source_kind": "official_profile",
        "summary": " ".join(parts),
        "supports": ["account_ownership", "persona_identity"],
        "observed_at": FIXED_REVIEWED_AT,
        "collection_method": method,
    }
    if title:
        evidence["profile_title"] = title
    if description:
        evidence["profile_description_excerpt"] = " ".join(description.split())[:500]
    retained = [u for u in row.get("evidence_urls", []) if isinstance(u, str) and u.startswith(("http://", "https://"))]
    if retained:
        evidence["review_evidence_urls"] = sorted(set(retained))
    return evidence


def usable_prior_evidence(resolution: dict, candidate_url: str) -> list[dict]:
    handle = urlsplit(candidate_url).path.strip("/").casefold()
    rows = []
    for evidence in resolution.get("evidence", []):
        if evidence.get("source_kind") not in OFFICIAL_KINDS or not evidence.get("observed_at"):
            continue
        if "account_ownership" not in evidence.get("supports", []):
            continue
        summary = str(evidence.get("summary", "")).casefold()
        score = 0
        if account_key(candidate_url) == account_key(evidence.get("source_url", candidate_url)):
            score -= 4
        if candidate_url.casefold() in summary:
            score -= 3
        if handle and handle in summary:
            score -= 2
        if evidence.get("source_kind") == "official_website":
            score -= 1
        rows.append((score, evidence.get("source_url", ""), evidence))
    rows.sort(key=lambda item: (item[0], item[1]))
    return [dict(item[2]) for item in rows]


def prior_indexes(previous: dict):
    by_url = defaultdict(list)
    by_discovery = {}
    for row in previous.get("resolutions", []):
        by_discovery[row["discovery_id"]] = row
        for url in row.get("official_account_urls", []):
            try:
                by_url[account_key(url)].append(row)
            except ValueError:
                pass
    return by_url, by_discovery


def trusted_index(registry: dict, corrections: dict):
    tables = registry.get("tables", registry)
    rejected = {row["link_id"] for row in corrections.get("corrections", [])}
    personas = {row["id"]: row for row in tables.get("personas", [])
                if row.get("review_status") == "verified"}
    accounts = {row["id"]: row for row in tables.get("accounts", [])}
    evidence = {row["id"]: row for row in tables.get("evidence", [])}
    by_url = defaultdict(list)
    for link in tables.get("account_links", []):
        ev = evidence.get(link.get("evidence_id"))
        account = accounts.get(link.get("account_id"))
        if (link.get("id") in rejected or link.get("review_status") != "verified"
                or link.get("valid_to") or link.get("persona_id") not in personas
                or not account or not ev or ev.get("kind") not in OFFICIAL_KINDS
                or not ev.get("summary")):
            continue
        try:
            key = account_key(account["url"])
        except (KeyError, ValueError):
            continue
        by_url[key].append({"link": link, "account": account, "evidence": ev})
    return by_url


def one_persona(rows: list[dict], label: str) -> str | None:
    personas = {row.get("persona_id") or row.get("link", {}).get("persona_id")
                for row in rows}
    personas.discard(None)
    if len(personas) > 1:
        raise ValueError(f"ambiguous {label}: multiple personas {sorted(personas)}")
    return next(iter(personas), None)


def choose_prior(rows: list[dict], label: str) -> dict | None:
    if not rows:
        return None
    personas = {row["persona_id"] for row in rows}
    if len(personas) > 1:
        raise ValueError(f"ambiguous {label}: multiple prior personas {sorted(personas)}")
    return sorted(rows, key=lambda row: row["discovery_id"])[0]


def build_row(review_row: dict, previous_by_url, trusted_by_url, accepted_by_id,
              profile: dict) -> tuple[dict, str]:
    did = review_row["discovery_id"]
    url = review_row["url"]
    key = account_key(url)
    name = canonical_name(review_row)
    profile_evidence = reviewed_profile_evidence(review_row, profile, name)
    evidence = [profile_evidence]
    checked = {url}
    official = {url}
    assertions = []
    route = None

    exact_prior = choose_prior(previous_by_url.get(key, []), f"exact Twitch URL {url}")
    if exact_prior:
        proofs = usable_prior_evidence(exact_prior, url)
        if not proofs:
            raise ValueError(f"{did}: prior ledger records {url} as official but retains no reusable owner evidence")
        proof = proofs[0]
        if proof["source_url"] != url:
            evidence.append(proof)
            checked.add(proof["source_url"])
        target_review = accepted_by_id[exact_prior["discovery_id"]]
        official.update(exact_prior.get("official_account_urls", []))
        official.add(target_review["url"])
        assertions.append({
            "method": "official_crosslink",
            "target_discovery_id": exact_prior["discovery_id"],
            "source_urls": [proof["source_url"]],
        })
        route = "prior_official_twitch_url"

    if route is None:
        trusted_claims = trusted_by_url.get(key, [])
        trusted_pid = one_persona(trusted_claims, f"trusted exact Twitch URL {url}")
        if trusted_pid:
            route = "trusted_exact_twitch_url"

    outgoing = []
    for candidate in profile.get("links", []):
        try:
            candidate_key = account_key(candidate)
        except ValueError:
            continue
        if candidate_key == key:
            continue
        outgoing.append((candidate, candidate_key))

    if route is None and outgoing:
        matched_prior = []
        matched_urls = []
        for candidate, candidate_key in outgoing:
            rows = previous_by_url.get(candidate_key, [])
            if rows:
                chosen = choose_prior(rows, f"Twitch outgoing URL {candidate}")
                matched_prior.append(chosen)
                matched_urls.append(candidate)
        if matched_prior:
            personas = {row["persona_id"] for row in matched_prior}
            if len(personas) > 1:
                raise ValueError(f"{did}: Twitch profile outgoing links point at multiple prior personas {sorted(personas)}")
            target = sorted(matched_prior, key=lambda row: row["discovery_id"])[0]
            target_review = accepted_by_id[target["discovery_id"]]
            matched = sorted(set(matched_urls), key=account_key)
            official.update(matched)
            official.add(target_review["url"])
            profile_evidence["summary"] += " The profile exposes owner-supplied outgoing link(s) matching an already resolved official account: " + ", ".join(matched) + "."
            assertions.append({
                "method": "official_crosslink",
                "target_discovery_id": target["discovery_id"],
                "source_urls": [url],
            })
            route = "twitch_outgoing_prior_account"

    if route is None and outgoing:
        trusted_matches = []
        matched_urls = []
        for candidate, candidate_key in outgoing:
            claims = trusted_by_url.get(candidate_key, [])
            if claims:
                trusted_matches.extend(claims)
                matched_urls.append(candidate)
        if trusted_matches:
            pid = one_persona(trusted_matches, f"Twitch outgoing trusted URL for {did}")
            matched = sorted(set(matched_urls), key=account_key)
            official.update(matched)
            profile_evidence["summary"] += " The profile exposes owner-supplied outgoing link(s) matching a verified trusted-registry account: " + ", ".join(matched) + "."
            assertions.append({
                "method": "official_crosslink",
                "persona_id": pid,
                "source_urls": [url],
            })
            route = "twitch_outgoing_trusted_account"

    no_existing = route is None
    if no_existing:
        route = "new_persona"
        search = {
            "corpora": [
                "data/registry/identity_resolutions.json: 242 previously resolved accepted accounts",
                "ThaiVirtualCreatorRegistry/data/registry.json: verified owner links after required corrections",
                "review_bundle.json: corrected accepted discovery account URLs",
                "public Twitch profile outgoing links when available",
            ],
            "method": "Exact normalized account URL comparison and owner-controlled outgoing-link comparison only. Names, handles, agency membership, and visual similarity are not identity joins.",
            "official_urls_checked": sorted({url, *[candidate for candidate, _ in outgoing]}, key=account_key),
            "result": "No verified existing-persona attachment was found through the inspected official identity paths; this Twitch account remains a separate new persona.",
        }
    else:
        search = None

    # Deduplicate evidence by canonical source URL while requiring identical content.
    by_source = {}
    for item in evidence:
        source = account_key(item["source_url"])
        if source in by_source and by_source[source] != item:
            raise ValueError(f"{did}: conflicting evidence for {item['source_url']}")
        by_source[source] = item
    evidence = [by_source[key] for key in sorted(by_source)]

    checked.update(item["source_url"] for item in evidence)
    entry = {
        "discovery_id": did,
        "canonical_name": name,
        "checked_urls": sorted(checked, key=account_key),
        "evidence_urls": sorted({item["source_url"] for item in evidence}, key=account_key),
        "official_account_urls": sorted(official, key=account_key),
        "reviewer": "chatgpt:task-8-twitch-identity-research",
        "evidence": evidence,
        "assertions": assertions,
        "no_existing_persona_match": no_existing,
    }
    if search:
        entry["existing_persona_search"] = search
    return entry, route


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-bundle", required=True, type=Path)
    parser.add_argument("--previous-ledger", required=True, type=Path)
    parser.add_argument("--trusted-registry", required=True, type=Path)
    parser.add_argument("--trusted-link-corrections", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    review = load(args.review_bundle)
    previous = load(args.previous_ledger)
    registry = load(args.trusted_registry)
    corrections = load(args.trusted_link_corrections)

    accepted = {row["discovery_id"]: row for row in review["rows"] if row.get("eligibility") == "vtuber"}
    twitch = [row for row in accepted.values() if str(row.get("platform", "")).casefold() == "twitch"]
    if len(twitch) != 150 or len({row["discovery_id"] for row in twitch}) != 150:
        raise SystemExit(f"expected exactly 150 accepted Twitch accounts, got {len(twitch)}")

    previous_by_url, _ = prior_indexes(previous)
    trusted_by_url = trusted_index(registry, corrections)
    rows = []
    routes = Counter()
    fetch_status = Counter()
    fetch_failures = []
    for review_row in sorted(twitch, key=lambda row: row["discovery_id"]):
        profile = {"status": None, "source_url": review_row["url"], "title": None,
                   "description": None, "links": []}
        if not args.offline:
            profile = fetch_twitch_profile(review_row["url"], args.timeout)
        fetch_status[str(profile.get("status"))] += 1
        if profile.get("status") != 200:
            fetch_failures.append({
                "discovery_id": review_row["discovery_id"],
                "url": review_row["url"],
                "profile_fetch": profile,
            })
        entry, route = build_row(review_row, previous_by_url, trusted_by_url, accepted, profile)
        rows.append(entry)
        routes[route] += 1

    payload = {
        "schema_version": 1,
        "reviewed_at": "2026-09-19",
        "platform": "twitch",
        "scope": "Exactly 150 accepted Twitch accounts in the corrected 392-account review bundle.",
        "required_trusted_link_corrections": review.get("required_trusted_link_corrections", []),
        "rows": rows,
    }
    if len({row["discovery_id"] for row in rows}) != 150:
        raise SystemExit("duplicate/missing Twitch discovery IDs in generated research")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "accepted_twitch": 150,
        "generated_rows": len(rows),
        "route_counts": dict(sorted(routes.items())),
        "profile_fetch_statuses": dict(sorted(fetch_status.items())),
        "profile_fetch_failures": fetch_failures,
        "required_correction_count": len(payload["required_trusted_link_corrections"]),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "profile_fetch_failures"}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
