import duckdb

from collector import yt_metrics
from collector.yt_comment_census import Census


class Resp:
    def __init__(self, code, body):
        self.status_code, self._body, self.content = code, body, b"x"

    def json(self):
        return self._body


class FakeChannels:
    def get(self, url, params, headers, timeout):
        assert url.endswith("/channels")
        items = [{"id": "UCa", "snippet": {"title": "A ch.", "customUrl": "@a"},
                  "statistics": {"subscriberCount": "1500", "viewCount": "90000", "videoCount": "12"}},
                 {"id": "UChidden", "snippet": {"title": "H"},
                  "statistics": {"hiddenSubscriberCount": True, "subscriberCount": "0", "viewCount": "5"}}]
        return Resp(200, {"items": [i for i in items if i["id"] in params["id"].split(",")]})


def test_collect_once_per_day_and_hidden_counts():
    con = duckdb.connect(":memory:")
    c = Census(con, "k", 100, session=FakeChannels())
    con.execute("INSERT INTO channels (channel_id) VALUES ('UCa'), ('UChidden'), ('UCgone')")
    assert yt_metrics.collect(c) is True
    assert yt_metrics.collect(c) is False  # everyone has today's row or is marked missing
    rows = dict((r[0], r[1:]) for r in con.execute(
        "SELECT channel_id, title, subscribers, views, videos FROM channel_metrics").fetchall())
    assert rows == {"UCa": ("A ch.", 1500, 90000, 12), "UChidden": ("H", None, 5, None)}
    assert c.used() == 1


def test_growth_deltas_use_nearest_earlier_point():
    con = duckdb.connect(":memory:")
    yt_metrics.ensure(con)
    for day, subs, views in [("2026-06-25", 1000, 10), ("2026-08-20", 1300, 40), ("2026-09-19", 1400, 70),
                             ("2026-09-26", 1500, 100)]:
        con.execute("INSERT INTO channel_metrics VALUES ('UCa', ?, 'A', NULL, ?, ?, NULL, '', 'youtube_api')",
                    [day, subs, views])
    row = dict(zip(yt_metrics.GROWTH_COLUMNS, yt_metrics.growth_rows(con)["UCa"]))
    assert row["subscribers_delta_7d"] == "100" and row["baseline_7d"] == "2026-09-19"
    assert row["subscribers_delta_30d"] == "200" and row["baseline_30d"] == "2026-08-20"
    assert row["subscribers_delta_90d"] == "500" and row["baseline_90d"] == "2026-06-25"
    assert row["views_delta_30d"] == "60" and row["history_points"] == "4"


def test_growth_leaves_delta_blank_when_no_point_near_the_window():
    con = duckdb.connect(":memory:")
    yt_metrics.ensure(con)
    for day, subs in [("2026-09-12", 1000), ("2026-09-26", 1100)]:
        con.execute("INSERT INTO channel_metrics VALUES ('UCa', ?, 'A', NULL, ?, NULL, NULL, '', 'youtube_api')",
                    [day, subs])
    row = dict(zip(yt_metrics.GROWTH_COLUMNS, yt_metrics.growth_rows(con)["UCa"]))
    assert row["subscribers_delta_7d"] == "" and row["baseline_7d"] == ""  # 14 days is not a 7-day delta


def test_description_links_are_captured_and_exported(tmp_path):
    class Desc:
        def get(self, url, params, headers, timeout):
            return Resp(200, {"items": [{"id": "UCa", "snippet": {
                "title": "A", "description": "โดเนท https://easydonate.app/foo。 X: https://x.com/a_vt)"},
                "statistics": {"subscriberCount": "1"}}]})

    con = duckdb.connect(":memory:")
    c = Census(con, "k", 100, session=Desc())
    con.execute("INSERT INTO channels (channel_id) VALUES ('UCa')")
    yt_metrics.collect(c)
    assert sorted(con.execute("SELECT url, domain FROM channel_links").fetchall()) == [
        ("https://easydonate.app/foo", "easydonate.app"), ("https://x.com/a_vt", "x.com")]
    out = tmp_path / "links.jsonl"
    assert yt_metrics.export_links(con, out) == 2
    assert "easydonate.app/foo" in out.read_text(encoding="utf-8")
