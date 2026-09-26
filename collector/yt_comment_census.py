"""
collector/yt_comment_census.py

Full YouTube comment census for every verified Thai VTuber channel, 2021-2026.

Scope (owner decision 2026-10-02):
- YouTube only. All uploads published 2021-01-01 .. 2026-12-31.
- Per comment/reply store: comment_id, video_id, channel_id, author_channel_id,
  author_display_name, published_at, like_count, parent_id.
  Comment TEXT is never requested or stored.
- Years are processed newest first (2026, 2025, ... 2021).
- Free tier only: one API key, daily budget below the 10,000-unit quota.
  Stops for the day when the budget or quotaExceeded is hit and resumes after
  the Pacific-time reset. Every page is checkpointed, so stopping the process or
  shutting down the PC loses nothing.

Data lives OUTSIDE the repo (default %LOCALAPPDATA%/ThaiVtuberSNA/yt_comments.duckdb,
override with YT_COMMENTS_DB).

Usage:
  python -m collector.yt_comment_census channels   # refresh channel list from ThaiVtuber_DATA
  python -m collector.yt_comment_census run        # run until stopped (sleeps over quota resets)
  python -m collector.yt_comment_census run --once # run until today's budget is spent, then exit
  python -m collector.yt_comment_census status
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import requests

from collector import yt_metrics

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.googleapis.com/youtube/v3"
PT = ZoneInfo("America/Los_Angeles")
YEARS = list(range(2026, 2020, -1))
START = "2021-01-01T00:00:00Z"
END = "2027-01-01T00:00:00Z"
DEFAULT_BUDGET = 9500

log = logging.getLogger("yt_comment_census")

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR PRIMARY KEY, uploads_playlist VARCHAR, title VARCHAR,
    scan_status VARCHAR DEFAULT 'pending', scan_page_token VARCHAR, scanned_at VARCHAR);
CREATE TABLE IF NOT EXISTS videos (
    video_id VARCHAR PRIMARY KEY, channel_id VARCHAR, published_at VARCHAR, year INTEGER,
    status VARCHAR DEFAULT 'pending', page_token VARCHAR, pages INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0, error VARCHAR, done_at VARCHAR);
CREATE TABLE IF NOT EXISTS comments (
    comment_id VARCHAR PRIMARY KEY, video_id VARCHAR, channel_id VARCHAR,
    author_channel_id VARCHAR, author_display_name VARCHAR, published_at VARCHAR,
    like_count INTEGER, parent_id VARCHAR);
CREATE TABLE IF NOT EXISTS reply_jobs (
    parent_id VARCHAR PRIMARY KEY, video_id VARCHAR, channel_id VARCHAR,
    status VARCHAR DEFAULT 'pending', page_token VARCHAR);
CREATE TABLE IF NOT EXISTS quota (day_pt VARCHAR PRIMARY KEY, units INTEGER);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS duration_s INTEGER;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS is_short BOOLEAN;
"""
SHORTS_MAX_S = 180  # YouTube Shorts can be up to 3 minutes


def iso_seconds(d: str) -> int:
    """PT1H2M3S -> 3723. Unknown/empty -> -1."""
    import re
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return -1
    dd, h, mi, se = (int(x or 0) for x in m.groups())
    return ((dd * 24 + h) * 60 + mi) * 60 + se


class QuotaExhausted(Exception):
    pass


def db_path() -> Path:
    p = os.getenv("YT_COMMENTS_DB")
    if p:
        return Path(p)
    base = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "ThaiVtuberSNA" / "yt_comments.duckdb"


def api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("YOUTUBE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise SystemExit("YOUTUBE_API_KEY not set")
    return key


class Census:
    def __init__(self, con: duckdb.DuckDBPyConnection, key: str, budget: int = DEFAULT_BUDGET,
                 session: requests.Session | None = None, web: requests.Session | None = None,
                 publish_metrics: bool = False):
        self.con, self.key, self.budget = con, key, budget
        self.http = session or requests.Session()
        self.web = web or requests.Session()
        self.publish_metrics = publish_metrics
        self._next_publish_try = 0.0
        con.execute(SCHEMA)
        yt_metrics.ensure(con)

    # ---- quota -------------------------------------------------------------
    def today(self) -> str:
        return datetime.now(PT).strftime("%Y-%m-%d")

    def used(self) -> int:
        return self.used_on(self.con)

    @staticmethod
    def used_on(con) -> int:
        r = con.execute("SELECT units FROM quota WHERE day_pt = ?", [datetime.now(PT).strftime("%Y-%m-%d")]).fetchone()
        return r[0] if r else 0

    def spend(self):
        if self.used() >= self.budget:
            raise QuotaExhausted()
        self.con.execute("INSERT INTO quota VALUES (?, 1) ON CONFLICT (day_pt) DO UPDATE SET units = units + 1",
                         [self.today()])

    def get(self, resource: str, params: dict) -> tuple[int, dict]:
        self.spend()
        for attempt in range(4):
            try:
                r = self.http.get(f"{API}/{resource}", params=params, headers={"X-Goog-Api-Key": self.key}, timeout=30)
            except requests.RequestException:
                time.sleep(2 ** attempt * 5)
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(2 ** attempt * 5)
                continue
            body = r.json() if r.content else {}
            reasons = {e.get("reason") for e in body.get("error", {}).get("errors", [])}
            if r.status_code == 403 and reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}:
                self.con.execute("INSERT INTO quota VALUES (?, ?) ON CONFLICT (day_pt) DO UPDATE SET units = ?",
                                 [self.today(), self.budget, self.budget])
                raise QuotaExhausted()
            return r.status_code, body
        return 599, {}

    # ---- phase 1: channels -> uploads playlists ----------------------------
    def resolve_uploads(self):
        ids = [r[0] for r in self.con.execute("SELECT channel_id FROM channels WHERE uploads_playlist IS NULL").fetchall()]
        for i in range(0, len(ids), 50):
            batch = ids[i:i + 50]
            code, body = self.get("channels", {"part": "contentDetails,snippet", "id": ",".join(batch), "maxResults": 50})
            if code != 200:
                log.warning("channels.list HTTP %s", code)
                continue
            found = set()
            for it in body.get("items", []):
                found.add(it["id"])
                self.con.execute("UPDATE channels SET uploads_playlist = ?, title = ? WHERE channel_id = ?",
                                 [it["contentDetails"]["relatedPlaylists"]["uploads"], it["snippet"]["title"], it["id"]])
            for cid in set(batch) - found:
                self.con.execute("UPDATE channels SET uploads_playlist = '', scan_status = 'gone' WHERE channel_id = ?", [cid])

    # ---- phase 2: list uploads 2021+ ---------------------------------------
    def scan_channel(self, cid: str, playlist: str, token: str | None):
        while True:
            params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
            if token:
                params["pageToken"] = token
            code, body = self.get("playlistItems", params)
            if code == 404:
                self.con.execute("UPDATE channels SET scan_status = 'gone' WHERE channel_id = ?", [cid])
                return
            if code != 200:
                self.con.execute("UPDATE channels SET scan_status = 'error' WHERE channel_id = ?", [cid])
                return
            oldest_seen = None
            for it in body.get("items", []):
                cd = it["contentDetails"]
                pub = cd.get("videoPublishedAt")
                if not pub:
                    continue  # private/deleted upload
                oldest_seen = min(oldest_seen or pub, pub)
                if START <= pub < END:
                    self.con.execute("INSERT INTO videos (video_id, channel_id, published_at, year) VALUES (?, ?, ?, ?) "
                                     "ON CONFLICT DO NOTHING", [cd["videoId"], cid, pub, int(pub[:4])])
            token = body.get("nextPageToken")
            # Uploads are newest-first; stop once a full page is older than 2021.
            if not token or (oldest_seen and oldest_seen < START):
                self.con.execute("UPDATE channels SET scan_status = 'done', scan_page_token = NULL, scanned_at = ? "
                                 "WHERE channel_id = ?", [datetime.now(timezone.utc).isoformat(), cid])
                return
            self.con.execute("UPDATE channels SET scan_page_token = ? WHERE channel_id = ?", [token, cid])

    # ---- phase 3: comments, newest year first -------------------------------
    def save(self, item: dict, video_id: str, channel_id: str, parent_id: str | None):
        s = item["snippet"]
        author = (s.get("authorChannelId") or {}).get("value")
        self.con.execute(
            "INSERT INTO comments VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [item["id"], video_id, channel_id, author, s.get("authorDisplayName"), s.get("publishedAt"),
             s.get("likeCount"), parent_id])

    def video_comments(self, vid: str, cid: str, token: str | None):
        while True:
            # textFormat is irrelevant: we never read textDisplay/textOriginal.
            params = {"part": "snippet,replies", "videoId": vid, "maxResults": 100, "order": "time"}
            if token:
                params["pageToken"] = token
            code, body = self.get("commentThreads", params)
            if code in (403, 404):
                reasons = {e.get("reason") for e in body.get("error", {}).get("errors", [])}
                status = "disabled" if "commentsDisabled" in reasons else "gone" if code == 404 else "forbidden"
                self.con.execute("UPDATE videos SET status = ?, error = ?, done_at = ? WHERE video_id = ?",
                                 [status, ",".join(sorted(r for r in reasons if r)), datetime.now(timezone.utc).isoformat(), vid])
                return
            if code != 200:
                self.con.execute("UPDATE videos SET status = 'error', error = ? WHERE video_id = ?", [f"HTTP {code}", vid])
                return
            n = 0
            self.con.execute("BEGIN")
            for th in body.get("items", []):
                top = th["snippet"]["topLevelComment"]
                self.save(top, vid, cid, None)
                n += 1
                inline = (th.get("replies") or {}).get("comments", [])
                for rep in inline:
                    self.save(rep, vid, cid, top["id"])
                    n += 1
                if th["snippet"].get("totalReplyCount", 0) > len(inline):
                    self.con.execute("INSERT INTO reply_jobs (parent_id, video_id, channel_id) VALUES (?, ?, ?) "
                                     "ON CONFLICT DO NOTHING", [top["id"], vid, cid])
            token = body.get("nextPageToken")
            self.con.execute("UPDATE videos SET pages = pages + 1, comments = comments + ?, page_token = ?, status = ?, "
                             "done_at = ? WHERE video_id = ?",
                             [n, token, "partial" if token else "done",
                              None if token else datetime.now(timezone.utc).isoformat(), vid])
            self.con.execute("COMMIT")
            if not token:
                return

    def replies(self, parent: str, vid: str, cid: str, token: str | None):
        while True:
            params = {"part": "snippet", "parentId": parent, "maxResults": 100}
            if token:
                params["pageToken"] = token
            code, body = self.get("comments", params)
            if code != 200:
                self.con.execute("UPDATE reply_jobs SET status = 'error' WHERE parent_id = ?", [parent])
                return
            self.con.execute("BEGIN")
            for rep in body.get("items", []):
                self.save(rep, vid, cid, parent)
            token = body.get("nextPageToken")
            self.con.execute("UPDATE reply_jobs SET page_token = ?, status = ? WHERE parent_id = ?",
                             [token, "partial" if token else "done", parent])
            self.con.execute("COMMIT")
            if not token:
                return

    # ---- phase 2b: skip Shorts (owner decision: loyal viewers only) ----------
    def classify_durations(self, year: int) -> bool:
        ids = [r[0] for r in self.con.execute("SELECT video_id FROM videos WHERE year = ? AND duration_s IS NULL "
                                              "AND status = 'pending' LIMIT 50", [year]).fetchall()]
        if not ids:
            return False
        code, body = self.get("videos", {"part": "contentDetails", "id": ",".join(ids), "maxResults": 50})
        if code != 200:
            return False
        seen = set()
        for it in body.get("items", []):
            seen.add(it["id"])
            secs = iso_seconds(it["contentDetails"].get("duration"))
            self.con.execute("UPDATE videos SET duration_s = ?, is_short = CASE WHEN ? > ? OR ? <= 0 THEN false END "
                             "WHERE video_id = ?", [secs, secs, SHORTS_MAX_S, secs, it["id"]])
        for vid in set(ids) - seen:  # removed/private since the playlist scan
            self.con.execute("UPDATE videos SET duration_s = -1, is_short = false, status = 'gone' WHERE video_id = ?", [vid])
        return True

    def is_short_url(self, vid: str) -> bool | None:
        """No API quota: /shorts/<id> answers 200 for a Short, redirects otherwise."""
        try:
            r = self.web.head(f"https://www.youtube.com/shorts/{vid}", allow_redirects=False, timeout=15,
                              headers={"User-Agent": "Mozilla/5.0"}, cookies={"CONSENT": "YES+1"})
        except requests.RequestException:
            return None
        if r.status_code == 200:
            return True
        if r.status_code in (301, 302, 303, 307, 308):
            return False
        return None

    def classify_shorts(self, year: int) -> bool:
        rows = self.con.execute("SELECT video_id FROM videos WHERE year = ? AND status = 'pending' AND duration_s "
                                "BETWEEN 1 AND ? AND is_short IS NULL LIMIT 20", [year, SHORTS_MAX_S]).fetchall()
        if not rows:
            return False
        for (vid,) in rows:
            short = self.is_short_url(vid)
            short = False if short is None else short  # unknown -> keep the video
            self.con.execute("UPDATE videos SET is_short = ?, status = CASE WHEN ? THEN 'skipped_short' ELSE status END "
                             "WHERE video_id = ?", [short, short, vid])
            time.sleep(0.3)
        return True

    # ---- driver ------------------------------------------------------------
    def step(self) -> bool:
        """Do one unit of work. Returns False when everything is finished."""
        # Once per day pick up channels newly verified in ThaiVtuber_DATA (sheet reads, no API quota).
        if self.publish_metrics and getattr(self, "_channels_day", None) != self.today():
            self._channels_day = self.today()
            try:
                refresh_channels(self.con)
            except Exception:
                log.exception("channel refresh failed; keeping current list")
        # Daily channel metrics first (~45 units), then publish once per day.
        if yt_metrics.collect(self):
            return True
        if self.publish_metrics and time.monotonic() >= self._next_publish_try:
            self._next_publish_try = time.monotonic() + 1800
            yt_metrics.publish_if_due(self)
        if self.con.execute("SELECT 1 FROM channels WHERE uploads_playlist IS NULL LIMIT 1").fetchone():
            self.resolve_uploads()
            return True
        ch = self.con.execute("SELECT channel_id, uploads_playlist, scan_page_token FROM channels "
                              "WHERE scan_status = 'pending' AND uploads_playlist <> '' LIMIT 1").fetchone()
        if ch:
            self.scan_channel(*ch)
            return True
        for year in YEARS:
            if self.classify_durations(year) or self.classify_shorts(year):
                return True
            v = self.con.execute("SELECT video_id, channel_id, page_token FROM videos WHERE year = ? "
                                 "AND status IN ('pending', 'partial') AND is_short = false "
                                 "ORDER BY published_at DESC LIMIT 1", [year]).fetchone()
            if v:
                self.video_comments(*v)
                return True
            rj = self.con.execute("SELECT r.parent_id, r.video_id, r.channel_id, r.page_token FROM reply_jobs r "
                                  "JOIN videos v USING (video_id) WHERE v.year = ? AND r.status IN ('pending', 'partial') "
                                  "LIMIT 1", [year]).fetchone()
            if rj:
                self.replies(*rj)
                return True
        return False

    def write_status(self, path: Path | None, state: str):
        if path is None:
            return
        tmp = path.with_suffix(".tmp")
        tmp.write_text(status_report(self.con, self.used(), self.budget, state), encoding="utf-8")
        os.replace(tmp, path)

    def run(self, once: bool = False, status_file: Path | None = None):
        last = 0.0
        while True:
            try:
                if time.monotonic() - last > 60:
                    self.write_status(status_file, "running")
                    last = time.monotonic()
                if not self.step():
                    log.info("census complete")
                    self.write_status(status_file, "complete")
                    return
            except QuotaExhausted:
                log.info("daily budget reached (%s units); %s", self.used(), status_line(self.con))
                self.write_status(status_file, "waiting for quota reset (00:00 Pacific = 14:00/15:00 Thailand)")
                if once:
                    return
                now = datetime.now(PT)
                reset = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
                time.sleep(max(60, (reset - now).total_seconds()))


def status_line(con) -> str:
    ch, scanned = con.execute("SELECT count(*), count(*) FILTER (WHERE scan_status = 'done') FROM channels").fetchone()
    vids, done = con.execute("SELECT count(*), count(*) FILTER (WHERE status NOT IN ('pending', 'partial')) "
                             "FROM videos").fetchone()
    comments = con.execute("SELECT count(*) FROM comments").fetchone()[0]
    return f"channels {ch} (scanned {scanned}), videos {vids} (done {done}), comments {comments}"


def status_report(con, used: int, budget: int, state: str) -> str:
    shorts = con.execute("SELECT count(*) FROM videos WHERE status = 'skipped_short'").fetchone()[0]
    lines = [f"state: {state}", f"shorts skipped: {shorts}", f"updated: {datetime.now().isoformat(timespec='seconds')}",
             f"quota today (Pacific day): {used}/{budget}", status_line(con)]
    for y, n, d in con.execute("SELECT year, count(*), count(*) FILTER (WHERE status NOT IN ('pending','partial')) "
                               "FROM videos GROUP BY year ORDER BY year DESC").fetchall():
        lines.append(f"  {y}: {d}/{n} videos done")
    return "\n".join(lines) + "\n"


def status_path() -> Path:
    return db_path().with_name("yt_comments_status.txt")


def refresh_channels(con):
    """Verified YouTube channels of verified personas from ThaiVtuber_DATA (read-only)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from migrate_canonical_sheet import Sheet, pad, token  # noqa: E402
    sh = Sheet(token())
    verified = {pad(r, 12)[0] for r in sh.get("'PERSONAS'!A2:L") if r and pad(r, 12)[8] == "verified"}
    linked = {pad(r, 11)[2] for r in sh.get("'ACCOUNT_LINKS'!A2:K")
              if r and pad(r, 11)[7] == "verified" and pad(r, 11)[1] in verified}
    ids = {pad(r, 14)[2] for r in sh.get("'ACCOUNTS'!A2:N")
           if r and pad(r, 14)[1] == "youtube" and pad(r, 14)[0] in linked and pad(r, 14)[2].startswith("UC")}
    con.execute(SCHEMA)
    before = con.execute("SELECT count(*) FROM channels").fetchone()[0]
    con.executemany("INSERT INTO channels (channel_id) VALUES (?) ON CONFLICT DO NOTHING", [[i] for i in sorted(ids)])
    after = con.execute("SELECT count(*) FROM channels").fetchone()[0]
    print(f"verified channels {len(ids)}; added {after - before}; total {after}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="yt_comment_census")
    ap.add_argument("command", choices=["channels", "run", "status"])
    ap.add_argument("--once", action="store_true", help="exit when today's budget is spent")
    ap.add_argument("--budget", type=int, default=int(os.getenv("YT_DAILY_BUDGET", DEFAULT_BUDGET)))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "status":
        try:
            con = duckdb.connect(str(path), read_only=True)
        except duckdb.IOException:
            # The running worker holds the DB lock; show its last snapshot instead.
            sp = status_path()
            print(sp.read_text(encoding="utf-8") if sp.exists() else "worker running; no status snapshot yet")
            return
        print(f"db {path}")
        print(status_report(con, Census.used_on(con), args.budget, "not running"), end="")
        con.close()
        return
    con = duckdb.connect(str(path))
    con.execute(SCHEMA)
    if args.command == "channels":
        refresh_channels(con)
    else:
        yt_metrics.ensure(con)
        seeded = yt_metrics.seed_from_archive(con, path.with_name("sna_archive.duckdb"))
        if seeded:
            log.info("seeded %s legacy YouTube metric points", seeded)
        census = Census(con, api_key(), args.budget, publish_metrics=True)
        census.links_export_path = path.with_name("yt_channel_links.jsonl")
        census.run(once=args.once, status_file=status_path())
    con.close()


if __name__ == "__main__":
    main()
