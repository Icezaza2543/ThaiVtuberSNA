"""Crawl Hub VTuber Thai and emit first-seen public account observations.

The collector is intentionally conservative:
- crawls only public vtuberthai.com directory/profile pages;
- extracts only supported public platform profile URLs;
- never auto-links or verifies personas;
- diffs against canonical registry accounts/candidates and prior discovery batches;
- emits new observations as JSONL for review/intake.

No login, cookies, private profiles, chat, viewer lists, or personal contact data are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import sys
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from registry.discovery.normalize import (
    extract_handle_from_url,
    infer_platform,
    normalize_url,
)
from registry.store import load, rows

BASE_URL = "https://vtuberthai.com"
DEFAULT_GROUPS = tuple("abcdefghijklmnopqrstuvwxyz") + ("0-9", "th", "other")
SUPPORTED_PLATFORMS = {
    "youtube",
    "twitch",
    "tiktok",
    "facebook",
    "instagram",
    "x",
    "kick",
    "ganknow",
}
USER_AGENT = (
    "ThaiVirtualCreatorRegistry/1.0 "
    "(public directory discovery; https://github.com/Icezaza2543/ThaiVirtualCreatorRegistry)"
)
YOUTUBE_CHANNEL_RE = re.compile(r"^/channel/(UC[A-Za-z0-9_-]{22})/?$")
BATCH_FILE_RE = re.compile(r"discovery-web-batch-(\d+)\.jsonl$")
NOISE_PATH_PARTS = {
    "watch",
    "shorts",
    "live",
    "playlist",
    "playlists",
    "videos",
    "streams",
    "clip",
    "clips",
    "status",
    "post",
    "posts",
    "reel",
    "reels",
}


class LinkAndHeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._in_h1 = False
        self._h1_parts: list[str] = []
        self.h1: str = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href.strip())
        elif tag == "h1" and not self.h1:
            self._in_h1 = True
            self._h1_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1" and self._in_h1:
            text = " ".join("".join(self._h1_parts).split())
            if text:
                self.h1 = text
            self._in_h1 = False
            self._h1_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_parts.append(data)


def fetch_text(url: str, *, timeout: float = 20.0, retries: int = 2) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "th,en;q=0.8",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise OSError(f"HTTP {response.status} for {url}")
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read(4 * 1024 * 1024).decode(charset, errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
    raise OSError(f"failed to fetch {url}: {last_error}") from last_error


def extract_profile_links(html: str, *, base_url: str = BASE_URL) -> list[str]:
    parser = LinkAndHeadingParser()
    parser.feed(html)
    found: set[str] = set()
    for href in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme != "https" or parsed.hostname != "vtuberthai.com":
            continue
        if not parsed.path.startswith("/vtuber/"):
            continue
        canonical = f"https://vtuberthai.com{parsed.path.rstrip('/')}"
        found.add(canonical)
    return sorted(found)


def _is_creator_profile_url(platform: str, url: str) -> bool:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if platform == "youtube":
        if YOUTUBE_CHANNEL_RE.match(parsed.path):
            return True
        return bool(parts and parts[0].startswith("@"))
    if not parts:
        return False
    if any(part.casefold() in NOISE_PATH_PARTS for part in parts[:2]):
        return False
    if platform == "facebook" and parts[0].casefold() in {"groups", "events", "watch"}:
        return False
    return True


def _stable_identity(platform: str, url: str) -> tuple[str | None, str | None]:
    if platform == "youtube":
        match = YOUTUBE_CHANNEL_RE.match(urlparse(url).path)
        if match:
            return "channel_id", match.group(1)
    return None, None


def extract_profile_observations(
    html: str,
    *,
    profile_url: str,
    observed_at: str | None = None,
) -> tuple[str, list[dict[str, str]]]:
    parser = LinkAndHeadingParser()
    parser.feed(html)
    name = parser.h1.strip()
    if not name:
        raise ValueError(f"profile has no h1: {profile_url}")
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()

    observations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href in parser.links:
        absolute = urljoin(profile_url, href)
        if not absolute.startswith(("https://", "http://")):
            continue
        platform = infer_platform(absolute)
        if platform not in SUPPORTED_PLATFORMS:
            continue
        try:
            canonical = normalize_url(platform, absolute)
        except (ValueError, TypeError):
            continue
        if not _is_creator_profile_url(platform, canonical):
            continue
        key = (platform, canonical.casefold())
        if key in seen:
            continue
        seen.add(key)
        id_namespace, platform_id = _stable_identity(platform, canonical)
        handle = extract_handle_from_url(platform, canonical)
        record = {
            "platform": platform,
            "url": canonical,
            "name": name,
            "source_url": profile_url,
            "method": "directory_crawl",
            "query": "Hub VTuber Thai full-directory diff",
            "source_kind": "secondary_source",
            "observed_at": observed_at,
        }
        if handle:
            record["handle"] = handle
        if platform_id:
            record["platform_id"] = platform_id
            record["id_namespace"] = id_namespace
        observations.append(record)
    return name, observations


def identity_keys(record: dict) -> set[str]:
    platform = str(record.get("platform") or "")
    url = record.get("url")
    keys: set[str] = set()
    if platform and url:
        try:
            canonical = normalize_url(platform, str(url))
            keys.add(f"url:{platform}:{canonical.casefold()}")
            namespace, inferred_id = _stable_identity(platform, canonical)
            if namespace and inferred_id:
                keys.add(f"id:{platform}:{namespace}:{inferred_id}")
        except (ValueError, TypeError):
            pass
    namespace = record.get("id_namespace")
    platform_id = record.get("platform_id")
    if platform and namespace and platform_id:
        keys.add(f"id:{platform}:{namespace}:{platform_id}")
    return keys


def load_known_identity_keys(root: Path = ROOT) -> set[str]:
    known: set[str] = set()
    db = load(root / "data/registry.json")
    try:
        for table in ("accounts", "candidates"):
            for record in rows(db, table):
                known.update(identity_keys(record))
    finally:
        db.close()

    for path in sorted((root / "intake").glob("*-discovery-web-batch-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                known.update(identity_keys(record))

    raw_dir = root / "intake" / "raw"
    if raw_dir.is_dir():
        for path in sorted(raw_dir.glob("*vtuberthai-directory*.jsonl")):
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    known.update(identity_keys(record))
    return known


def crawl_index_groups(
    groups: Iterable[str],
    *,
    timeout: float,
) -> tuple[list[str], list[dict[str, str]]]:
    profiles: set[str] = set()
    errors: list[dict[str, str]] = []
    group_list = list(groups)
    for index, group in enumerate(group_list, 1):
        url = f"{BASE_URL}/vtubers/browse/{group}"
        try:
            html = fetch_text(url, timeout=timeout)
            before = len(profiles)
            profiles.update(extract_profile_links(html))
            added = len(profiles) - before
            print(
                f"[directory index {index}/{len(group_list)}] {group}: "
                f"+{added} profiles, total={len(profiles)}",
                flush=True,
            )
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            print(
                f"[directory index {index}/{len(group_list)}] {group}: ERROR {exc}",
                flush=True,
            )
    return sorted(profiles), errors


def crawl_profiles(
    profile_urls: list[str],
    *,
    workers: int,
    timeout: float,
    observed_at: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    observations: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    def one(url: str):
        html = fetch_text(url, timeout=timeout)
        return extract_profile_observations(
            html,
            profile_url=url,
            observed_at=observed_at,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_url = {pool.submit(one, url): url for url in profile_urls}
        total = len(future_to_url)
        completed = 0
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                _, rows_found = future.result()
                observations.extend(rows_found)
            except Exception as exc:
                errors.append({"url": url, "error": str(exc)})
            completed += 1
            if completed == 1 or completed % 25 == 0 or completed == total:
                print(
                    f"[creator profiles] {completed}/{total} complete; "
                    f"supported account observations={len(observations)}; "
                    f"errors={len(errors)}",
                    flush=True,
                )

    observations.sort(key=lambda r: (r["name"].casefold(), r["platform"], r["url"]))
    return observations, errors


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def next_batch_number(root: Path = ROOT) -> int:
    highest = 0
    for path in (root / "intake").glob("*-discovery-web-batch-*.jsonl"):
        match = BATCH_FILE_RE.search(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def emit_batch_files(
    records: list[dict],
    *,
    root: Path,
    batch_size: int,
    batch_date: str,
) -> list[Path]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    start = next_batch_number(root)
    written: list[Path] = []
    for offset in range(0, len(records), batch_size):
        number = start + len(written)
        path = root / "intake" / f"{batch_date}-discovery-web-batch-{number}.jsonl"
        if path.exists():
            raise FileExistsError(path)
        write_jsonl(path, records[offset : offset + batch_size])
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "intake" / "raw" / (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
            + "-vtuberthai-directory-new.jsonl"
        ),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Summary JSON path (default: <output>.summary.json)",
    )
    parser.add_argument(
        "--group",
        action="append",
        dest="groups",
        help="Directory group to crawl; repeatable. Default: a-z, 0-9, th, other.",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--limit-profiles", type=int)
    parser.add_argument(
        "--include-known",
        action="store_true",
        help="Emit known observations too; default emits first-seen identities only.",
    )
    parser.add_argument(
        "--emit-batches",
        action="store_true",
        help="Also split emitted rows into numbered intake discovery batches.",
    )
    parser.add_argument("--batch-size", type=int, default=6)
    args = parser.parse_args()

    if not 1 <= args.workers <= 8:
        raise SystemExit("--workers must be between 1 and 8")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    groups = tuple(args.groups or DEFAULT_GROUPS)
    observed_at = datetime.now(timezone.utc).isoformat()

    known = load_known_identity_keys(ROOT)
    profile_urls, index_errors = crawl_index_groups(groups, timeout=args.timeout)
    if args.limit_profiles is not None:
        profile_urls = profile_urls[: max(0, args.limit_profiles)]

    observations, profile_errors = crawl_profiles(
        profile_urls,
        workers=args.workers,
        timeout=args.timeout,
        observed_at=observed_at,
    )

    emitted: list[dict[str, str]] = []
    seen_current: set[str] = set()
    known_observations = 0
    platform_counts = Counter()
    profiles_with_new: set[str] = set()
    profiles_seen: set[str] = set()

    for record in observations:
        profiles_seen.add(record["source_url"])
        keys = identity_keys(record)
        if not keys:
            continue
        primary = sorted(keys)[0]
        if primary in seen_current:
            continue
        seen_current.update(keys)
        if known.intersection(keys):
            known_observations += 1
            if not args.include_known:
                continue
        emitted.append(record)
        profiles_with_new.add(record["source_url"])
        platform_counts[record["platform"]] += 1

    write_jsonl(args.output, emitted)
    batch_paths: list[Path] = []
    if args.emit_batches and emitted:
        batch_paths = emit_batch_files(
            emitted,
            root=ROOT,
            batch_size=args.batch_size,
            batch_date=date.today().isoformat(),
        )

    summary_path = args.summary or args.output.with_suffix(args.output.suffix + ".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "source": BASE_URL,
        "observed_at": observed_at,
        "groups": list(groups),
        "profiles_discovered": len(profile_urls),
        "profiles_fetched": len(profile_urls) - len(profile_errors),
        "profiles_with_supported_accounts": len(profiles_seen),
        "profiles_with_new_accounts": len(profiles_with_new),
        "raw_supported_account_urls": len(observations),
        "unique_supported_identity_keys": len(seen_current),
        "known_observations": known_observations,
        "emitted_rows": len(emitted),
        "emitted_platforms": dict(platform_counts.most_common()),
        "batch_files": [str(path.relative_to(ROOT)) for path in batch_paths],
        "errors": index_errors + profile_errors,
        "semantics": (
            "public secondary-source discovery only; emitted rows are first-seen account identities "
            "unless --include-known is used; no persona is linked or verified automatically"
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
