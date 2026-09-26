"""
collector/yt_metrics.py

Daily YouTube channel metrics (title, subscribers, views, video count) for every
channel in the census DB, plus publishing to the ThaiVtuber_SNA sheet.

Runs inside the comment-census process (DuckDB allows one writer):
- `collect(census)`: channels.list in batches of 50 (1 unit each, ~45 units/day)
  until every live channel has a row for today (Pacific quota day).
- `publish(con)`: ANALYTICS_METRICS keeps one latest YouTube row per channel
  (other platforms untouched); ANALYTICS_GROWTH gets 7/30/90-day deltas from the
  local history. Full history stays local in `channel_metrics`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
SNA_SHEET = "1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE"
log = logging.getLogger("yt_metrics")

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_metrics (
    channel_id VARCHAR, day VARCHAR, title VARCHAR, custom_url VARCHAR,
    subscribers BIGINT, views BIGINT, videos BIGINT, observed_at VARCHAR, source VARCHAR,
    PRIMARY KEY (channel_id, day));
CREATE TABLE IF NOT EXISTS metrics_published (day VARCHAR PRIMARY KEY, published_at VARCHAR);
CREATE TABLE IF NOT EXISTS metrics_missing (channel_id VARCHAR, day VARCHAR, PRIMARY KEY (channel_id, day));
CREATE TABLE IF NOT EXISTS channel_links (
    channel_id VARCHAR, url VARCHAR, domain VARCHAR, first_seen VARCHAR, last_seen VARCHAR,
    PRIMARY KEY (channel_id, url));
"""
METRIC_COLUMNS = ["platform", "platform_id", "name", "scope", "followers_or_subscribers", "views", "likes_received",
                  "metric_time", "time_basis", "observed_at", "source", "source_url", "account_url"]
GROWTH_COLUMNS = ["channel_id", "name", "scope", "source", "first_date", "last_date", "history_points",
                  "subscribers_delta_7d", "baseline_7d", "subscribers_delta_30d", "baseline_30d",
                  "subscribers_delta_90d", "baseline_90d", "views_delta_30d", "views_baseline_30d",
                  "source_url", "account_url"]


URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'，、。]+", re.I)


def description_links(text: str) -> list[tuple[str, str]]:
    """Outbound links written by the channel owner in the About description."""
    out = {}
    for raw in URL_RE.findall(text or ""):
        url = raw.rstrip(".,;:!?)」』】。")
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.").removeprefix("m.")
        if host:
            out[url] = host
    return list(out.items())


def export_links(con, path: Path) -> int:
    """JSONL snapshot for importers (the worker holds the DB lock)."""
    rows = con.execute("SELECT channel_id, url, domain, first_seen, last_seen FROM channel_links "
                       "ORDER BY channel_id, url").fetchall()
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for cid, url, domain, first, last in rows:
            f.write(json.dumps({"channel_id": cid, "url": url, "domain": domain,
                                "first_seen": first, "last_seen": last}, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    return len(rows)


def ensure(con):
    con.execute(SCHEMA)


def _int(v):
    try:
        return int(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def seed_from_archive(con, archive_db: Path) -> int:
    """One-time: legacy YouTube points from the archived ANALYTICS_METRICS tab."""
    if con.execute("SELECT count(*) FROM channel_metrics WHERE source LIKE 'legacy:%'").fetchone()[0]:
        return 0
    if not archive_db.exists():
        return 0
    import duckdb
    src = duckdb.connect(str(archive_db), read_only=True)
    try:
        rows = src.execute('SELECT platform_id, name, followers_or_subscribers, views, metric_time, source '
                           'FROM "ANALYTICS_METRICS" WHERE platform = \'youtube\'').fetchall()
    finally:
        src.close()
    n = 0
    for pid, name, subs, views, when, source in rows:
        if not pid or not when:
            continue
        con.execute("INSERT INTO channel_metrics VALUES (?, ?, ?, NULL, ?, ?, NULL, ?, ?) ON CONFLICT DO NOTHING",
                    [pid, when[:10], name, _int(subs), _int(views), when, f"legacy:{source}"])
        n += 1
    return n


def collect(census) -> bool:
    """One batch of channels.list. Returns True if it did work (call again)."""
    con, day = census.con, census.today()
    ids = [r[0] for r in con.execute(
        "SELECT c.channel_id FROM channels c WHERE c.scan_status <> 'gone' AND NOT EXISTS "
        "(SELECT 1 FROM channel_metrics m WHERE m.channel_id = c.channel_id AND m.day = ?) "
        "AND c.channel_id NOT IN (SELECT channel_id FROM metrics_missing WHERE day = ?) LIMIT 50", [day, day]).fetchall()]
    if not ids:
        return False
    code, body = census.get("channels", {"part": "snippet,statistics", "id": ",".join(ids), "maxResults": 50})
    if code != 200:
        log.warning("channels.list HTTP %s", code)
        con.executemany("INSERT INTO metrics_missing VALUES (?, ?) ON CONFLICT DO NOTHING", [[i, day] for i in ids])
        return True
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen = set()
    for it in body.get("items", []):
        seen.add(it["id"])
        st, sn = it.get("statistics", {}), it.get("snippet", {})
        subs = None if st.get("hiddenSubscriberCount") else _int(st.get("subscriberCount"))
        con.execute("INSERT INTO channel_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'youtube_api') ON CONFLICT DO NOTHING",
                    [it["id"], day, sn.get("title"), sn.get("customUrl"), subs, _int(st.get("viewCount")),
                     _int(st.get("videoCount")), now])
        for url, host in description_links(sn.get("description")):
            con.execute("INSERT INTO channel_links VALUES (?, ?, ?, ?, ?) ON CONFLICT (channel_id, url) "
                        "DO UPDATE SET last_seen = excluded.last_seen", [it["id"], url, host, day, day])
    # Channels not returned today (terminated/private): don't retry until tomorrow.
    missing = [[i, day] for i in set(ids) - seen]
    if missing:
        con.executemany("INSERT INTO metrics_missing VALUES (?, ?) ON CONFLICT DO NOTHING", missing)
    return True


def _values_api(tok):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s, f"https://sheets.googleapis.com/v4/spreadsheets/{SNA_SHEET}/values/"


def growth_rows(con) -> dict[str, list]:
    hist = {}
    for cid, d, title, subs, views, source in con.execute(
            "SELECT channel_id, day, title, subscribers, views, source FROM channel_metrics ORDER BY channel_id, day"
    ).fetchall():
        hist.setdefault(cid, []).append((date.fromisoformat(d), title, subs, views, source))
    out = {}
    for cid, pts in hist.items():
        if len(pts) < 2:
            continue
        last_d, title, last_s, last_v, _ = pts[-1]

        def base(days, idx):
            # Nearest point at or before (last - N days), but no older than N + N/4 (min 2) days,
            # so a "7d" delta is never computed over two weeks.
            target, oldest = last_d - timedelta(days=days), last_d - timedelta(days=days + max(2, days // 4))
            cand = [p for p in pts if oldest <= p[0] <= target and p[idx] is not None]
            return cand[-1] if cand else None

        row = {"channel_id": cid, "name": title or "", "scope": "verified_persona",
               "source": "youtube_api", "first_date": pts[0][0].isoformat(), "last_date": last_d.isoformat(),
               "history_points": str(len(pts)), "source_url": "https://developers.google.com/youtube/v3",
               "account_url": f"https://www.youtube.com/channel/{cid}"}
        for n in (7, 30, 90):
            b = base(n, 2)
            row[f"subscribers_delta_{n}d"] = "" if not b or last_s is None else str(last_s - b[2])
            row[f"baseline_{n}d"] = b[0].isoformat() if b and last_s is not None else ""
        b = base(30, 3)
        row["views_delta_30d"] = "" if not b or last_v is None else str(last_v - b[3])
        row["views_baseline_30d"] = b[0].isoformat() if b and last_v is not None else ""
        out[cid] = [row[c] for c in GROWTH_COLUMNS]
    return out


def publish(con, tok) -> dict:
    """Rewrite YouTube rows of ANALYTICS_METRICS and merge ANALYTICS_GROWTH. Sheet-only, no deletes of tabs."""
    http, base = _values_api(tok)
    latest = con.execute(
        "SELECT channel_id, title, subscribers, views, observed_at FROM channel_metrics WHERE source = 'youtube_api' "
        "QUALIFY row_number() OVER (PARTITION BY channel_id ORDER BY day DESC) = 1").fetchall()
    if not latest:
        return {"published": 0}

    def get(a1):
        r = http.get(base + requests.utils.quote(a1, safe=""), timeout=120)
        r.raise_for_status()
        return r.json().get("values", [])

    def rewrite(tab, header, rows):
        width = chr(ord("A") + len(header) - 1)
        r = http.post(base + requests.utils.quote(f"'{tab}'!A2:{width}", safe="") + ":clear", timeout=120)
        r.raise_for_status()
        r = http.put(base + requests.utils.quote(f"'{tab}'!A2", safe=""), params={"valueInputOption": "RAW"},
                     json={"values": rows}, timeout=300)
        r.raise_for_status()

    current = get("'ANALYTICS_METRICS'!A1:M")
    if current[0] != METRIC_COLUMNS:
        raise RuntimeError(f"ANALYTICS_METRICS header changed: {current[0]}")
    keep = [r for r in current[1:] if r and r[0] != "youtube"]
    yt = [["youtube", cid, title or "", "verified_persona", "" if subs is None else str(subs),
           "" if views is None else str(views), "", at, "retrieved_from_platform", at, "youtube_api",
           "https://developers.google.com/youtube/v3", f"https://www.youtube.com/channel/{cid}"]
          for cid, title, subs, views, at in latest]
    rewrite("ANALYTICS_METRICS", METRIC_COLUMNS, keep + yt)

    g = get("'ANALYTICS_GROWTH'!A1:Q")
    if g[0] != GROWTH_COLUMNS:
        raise RuntimeError(f"ANALYTICS_GROWTH header changed: {g[0]}")
    ours = growth_rows(con)
    merged = {r[0]: r for r in g[1:] if r}
    for cid, row in ours.items():
        old = merged.get(cid)
        # Local history replaces the legacy row once it covers at least 7 days.
        if old is None or date.fromisoformat(row[5]) - date.fromisoformat(row[4]) >= timedelta(days=7):
            merged[cid] = row
    rewrite("ANALYTICS_GROWTH", GROWTH_COLUMNS, list(merged.values()))
    return {"metrics_youtube": len(yt), "metrics_other": len(keep), "growth": len(merged)}


def publish_if_due(census) -> None:
    con, day = census.con, census.today()
    if con.execute("SELECT 1 FROM metrics_published WHERE day = ?", [day]).fetchone():
        return
    sys.path.insert(0, str(ROOT / "scripts"))
    from migrate_canonical_sheet import token  # noqa: E402
    try:
        result = publish(con, token())
    except Exception:
        log.exception("metrics publish failed; will retry later today")
        return
    con.execute("INSERT INTO metrics_published VALUES (?, ?)", [day, datetime.now(timezone.utc).isoformat()])
    links_path = getattr(census, "links_export_path", None)
    if links_path:
        result["links_exported"] = export_links(con, links_path)
    log.info("metrics published %s", result)
