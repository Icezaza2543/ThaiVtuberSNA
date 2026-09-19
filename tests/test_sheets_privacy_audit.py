"""Registry-aware privacy audit regression tests."""
from pathlib import Path

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog
from scripts import audit_sheets_privacy as audit


class FakeWorksheet:
    def __init__(self, records):
        self._records = records

    def get_all_records(self):
        return list(self._records)


class FakeSpreadsheet:
    def __init__(self, records):
        self._worksheet = FakeWorksheet(records)

    def worksheet(self, name):
        assert name == "VTUBERS"
        return self._worksheet


def test_known_vtuber_ids_come_from_creator_catalog():
    expected = {
        row["platform_id"]
        for row in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_accounts()
        if row.get("platform_id")
    }
    assert audit.load_known_vtuber_ids() == expected
    assert len(expected) >= 1370


def test_sheet_export_rejects_unknown_creator_id(monkeypatch):
    monkeypatch.setattr(
        audit,
        "audit_private_sheet",
        lambda *_args, **_kwargs: {"status": "PASS", "findings": []},
    )
    known = {"UC" + "A" * 22}
    unknown = "UC" + "B" * 22
    ok, findings = audit.audit_sheets(
        FakeSpreadsheet([{"channel_id": unknown}]),
        vtuber_ids=known,
    )
    assert ok is False
    assert any(
        row["reason"] == "SHEET_CHANNEL_OUTSIDE_CANONICAL_CATALOG"
        and row["status"] == "FAIL"
        for row in findings
    )


def test_sheet_export_can_be_subset_but_reports_warning(monkeypatch):
    monkeypatch.setattr(
        audit,
        "audit_private_sheet",
        lambda *_args, **_kwargs: {"status": "PASS", "findings": []},
    )
    first = "UC" + "A" * 22
    second = "UC" + "B" * 22
    ok, findings = audit.audit_sheets(
        FakeSpreadsheet([{"channel_id": first}]),
        vtuber_ids={first, second},
    )
    assert ok is True
    assert any(
        row["reason"] == "CANONICAL_CHANNEL_NOT_IN_SHEET_EXPORT"
        and row["status"] == "WARNING"
        for row in findings
    )


def test_active_privacy_audit_has_no_legacy_registry_path():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "audit_sheets_privacy.py").read_text(encoding="utf-8")
    assert "thai_vtuber_registry" not in source
    assert "registry_vtubers" not in source
