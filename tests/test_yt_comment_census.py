import duckdb

from collector.yt_comment_census import Census


class Resp:
    def __init__(self, code, body):
        self.status_code, self._body, self.content = code, body, b"x"

    def json(self):
        return self._body


class FakeYT:
    """Minimal fake of the YouTube Data API endpoints the census uses."""

    def __init__(self):
        self.calls = []

    def get(self, url, params, headers, timeout):
        res = url.rsplit("/", 1)[1]
        self.calls.append((res, dict(params)))
        if res == "channels":
            return Resp(200, {"items": [{"id": "UCa", "snippet": {"title": "A"},
                                         "contentDetails": {"relatedPlaylists": {"uploads": "UUa"}}}]})
        if res == "playlistItems":
            items = [{"contentDetails": {"videoId": "v2026", "videoPublishedAt": "2026-03-01T00:00:00Z"}},
                     {"contentDetails": {"videoId": "v2021", "videoPublishedAt": "2021-05-01T00:00:00Z"}},
                     {"contentDetails": {"videoId": "vold", "videoPublishedAt": "2019-01-01T00:00:00Z"}},
                     {"contentDetails": {"videoId": "vprivate"}}]
            return Resp(200, {"items": items, "nextPageToken": "never-followed"})
        if res == "commentThreads":
            vid = params["videoId"]
            if vid == "v2021":
                return Resp(403, {"error": {"errors": [{"reason": "commentsDisabled"}]}})
            if "pageToken" not in params:
                return Resp(200, {"nextPageToken": "p2", "items": [{
                    "snippet": {"totalReplyCount": 7, "topLevelComment": {"id": "c1", "snippet": {
                        "authorChannelId": {"value": "UCviewer1"}, "authorDisplayName": "Viewer One",
                        "publishedAt": "2026-03-02T00:00:00Z", "likeCount": 3, "textDisplay": "SECRET"}}},
                    "replies": {"comments": [{"id": "c1.r1", "snippet": {
                        "authorChannelId": {"value": "UCviewer2"}, "authorDisplayName": "Viewer Two",
                        "publishedAt": "2026-03-03T00:00:00Z", "likeCount": 0, "textDisplay": "SECRET"}}]}}]})
            return Resp(200, {"items": []})
        if res == "comments":
            return Resp(200, {"items": [{"id": "c1.r2", "snippet": {
                "authorChannelId": {"value": "UCviewer3"}, "authorDisplayName": "Viewer Three",
                "publishedAt": "2026-03-04T00:00:00Z", "likeCount": 1, "textDisplay": "SECRET"}}]})
        raise AssertionError(res)


def make(budget=100):
    con = duckdb.connect(":memory:")
    c = Census(con, "k", budget, session=FakeYT())
    con.execute("INSERT INTO channels (channel_id) VALUES ('UCa')")
    return con, c


def test_full_run_scope_and_no_text():
    con, c = make()
    c.run(once=True)
    vids = dict(con.execute("SELECT video_id, status FROM videos").fetchall())
    assert vids == {"v2026": "done", "v2021": "disabled"}  # 2019 and private uploads excluded
    rows = con.execute("SELECT comment_id, author_channel_id, author_display_name, parent_id FROM comments "
                       "ORDER BY comment_id").fetchall()
    assert rows == [("c1", "UCviewer1", "Viewer One", None), ("c1.r1", "UCviewer2", "Viewer Two", "c1"),
                    ("c1.r2", "UCviewer3", "Viewer Three", "c1")]
    cols = [r[0] for r in con.execute("DESCRIBE comments").fetchall()]
    assert not any("text" in col for col in cols)
    assert "SECRET" not in str(con.execute("SELECT * FROM comments").fetchall())


def test_newest_year_first_and_budget_resume():
    con, c = make(budget=3)  # channels + playlist + 1 comment page
    c.run(once=True)
    first_vid = [p.get("videoId") for r, p in c.http.calls if r == "commentThreads"][0]
    assert first_vid == "v2026"
    assert con.execute("SELECT status, page_token FROM videos WHERE video_id='v2026'").fetchone() == ("partial", "p2")
    # next day: resumes from the saved page token, no duplicate rows
    c.budget = 100
    con.execute("DELETE FROM quota")
    c.run(once=True)
    assert con.execute("SELECT status FROM videos WHERE video_id='v2026'").fetchone()[0] == "done"
    assert con.execute("SELECT count(*) FROM comments").fetchone()[0] == 3
    resumed = [p for r, p in c.http.calls if r == "commentThreads" and p.get("pageToken") == "p2"]
    assert len(resumed) == 1
