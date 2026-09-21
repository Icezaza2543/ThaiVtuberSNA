"""
Thai VTuber Audience Network (SNA)
Registry Manager (Control Plane)

Google Sheets remains an optional external control plane.  The local creator
registry is the validated, read-only schema-v2 CreatorCatalog.
"""
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from config.settings import GOOGLE_SHEETS_CONFIG, DATA_DIR, CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog

logger = logging.getLogger(__name__)

VTUBERS_COLUMNS = [
    "channel_id",
    "handle",
    "name",
    "subscriber_count",
    "agency",
    "status",
    "thai_confidence",
    "priority",
    "source_count",
    "last_activity",
    "last_collected",
    "streams_collected",
    "enabled",
]

NETWORK_RESULT_COLUMNS = [
    "vtuber_a",
    "vtuber_b",
    "shared_viewers",
    "jaccard",
    "overlap_coefficient",
    "calculated_at",
]


class RegistryManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or GOOGLE_SHEETS_CONFIG
        self.catalog_path = Path(self.config.get("creator_registry_path", CREATOR_REGISTRY_PATH))
        self.local_system_path = DATA_DIR / "registry_system.json"
        self.local_network_path = DATA_DIR / "network_results.csv"
        self._gsheet_client = None
        self._spreadsheet = None
        self._init_gsheet_if_configured()

    def _init_gsheet_if_configured(self):
        """Attempt to initialize gspread when credentials and a sheet ID exist."""
        cred_path = Path(self.config.get("credentials_path", ""))
        sheet_id = self.config.get("spreadsheet_id", "")

        if cred_path.exists() and sheet_id:
            try:
                import gspread

                self._gsheet_client = gspread.service_account(filename=str(cred_path))
                self._spreadsheet = self._gsheet_client.open_by_key(sheet_id)
                logger.info("Connected to configured Google Sheets control plane.")
            except Exception as exc:
                logger.warning("Could not connect to Google Sheets; using canonical local catalog: %s", exc)
                self._gsheet_client = None
                self._spreadsheet = None
        else:
            logger.info("Using canonical local CreatorCatalog (Google Sheets not configured).")

    # ------------------ VTUBERS SHEET ------------------

    def _catalog_rows(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in CreatorCatalog.from_path(self.catalog_path).youtube_rows()]

    def load_vtubers(self) -> List[Dict[str, Any]]:
        """Load the external sheet when available, otherwise the canonical catalog."""
        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_vtubers"])
                return self._sanitize_records(worksheet.get_all_records())
            except Exception as exc:
                logger.error("Failed to read Google Sheet; falling back to canonical catalog: %s", exc)
        return self._catalog_rows()

    def save_vtubers(self, vtubers: List[Dict[str, Any]]):
        """Update only the configured external sheet.

        The local canonical catalog is immutable through this control-plane API;
        changes must enter through reviewed discovery/identity evidence and a
        deterministic catalog rebuild.
        """
        if not self._spreadsheet:
            raise RuntimeError(
                "local creator catalog is read-only; configure the external VTUBERS sheet "
                "or rebuild the canonical registry from reviewed evidence"
            )
        try:
            worksheet = self._spreadsheet.worksheet(self.config["sheet_vtubers"])
            rows = [VTUBERS_COLUMNS]
            for vtuber in vtubers:
                rows.append([str(vtuber.get(col, "")) for col in VTUBERS_COLUMNS])
            worksheet.clear()
            worksheet.update(rows)
        except Exception:
            logger.exception("Failed to sync VTUBERS sheet")
            raise

    def get_enabled_vtubers(self) -> List[Dict[str, Any]]:
        """Return eligible enabled rows from either external or canonical shape."""
        rows = self.load_vtubers()
        selected = []
        for row in rows:
            enabled = row.get("enabled", True)
            enabled = enabled if isinstance(enabled, bool) else str(enabled).strip().lower() in {"true", "1", "yes"}
            external_accept = row.get("status") == "ACCEPT"
            canonical_accept = row.get("vtuber_status") == "CONFIRMED"
            if enabled and (external_accept or canonical_accept):
                selected.append(row)
        return selected

    def update_vtuber(self, channel_id: str, updates: Dict[str, Any]):
        """Update an external control-plane row; local-only mode is read-only."""
        vtubers = self.load_vtubers()
        for row in vtubers:
            if row.get("channel_id") == channel_id:
                row.update(updates)
                self.save_vtubers(vtubers)
                return

    # ------------------ SYSTEM SHEET ------------------

    def update_system_status(self, updates: Dict[str, Any]):
        """Update non-identity system monitoring metadata."""
        current_status = {}
        if self.local_system_path.exists():
            try:
                with open(self.local_system_path, "r", encoding="utf-8") as handle:
                    current_status = json.load(handle)
            except Exception:
                current_status = {}

        current_status.update(updates)
        current_status["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(self.local_system_path, "w", encoding="utf-8") as handle:
            json.dump(current_status, handle, indent=2, ensure_ascii=False)

        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_system"])
                rows = [["Metric", "Value"]]
                for key, value in current_status.items():
                    rows.append([str(key), str(value)])
                worksheet.clear()
                worksheet.update(rows)
            except Exception as exc:
                logger.warning("Failed to sync SYSTEM sheet: %s", exc)

    # ------------------ NETWORK RESULT SHEET ------------------

    def save_network_results(self, results: List[Dict[str, Any]]):
        """Save derived aggregate network results; these are not creator identity data."""
        with open(self.local_network_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=NETWORK_RESULT_COLUMNS)
            writer.writeheader()
            for result in results:
                writer.writerow({col: result.get(col, "") for col in NETWORK_RESULT_COLUMNS})

        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_network"])
                rows = [NETWORK_RESULT_COLUMNS]
                for result in results:
                    rows.append([str(result.get(col, "")) for col in NETWORK_RESULT_COLUMNS])
                worksheet.clear()
                worksheet.update(rows)
            except Exception as exc:
                logger.warning("Failed to sync NETWORK_RESULT sheet: %s", exc)

    # ------------------ SANITIZATION HELPERS ------------------

    def _sanitize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._sanitize_row(record) for record in records]

    def _sanitize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize mutable external-sheet values without touching catalog bytes."""
        sanitized = dict(row)
        for field, default, converter in (
            ("subscriber_count", 0, int),
            ("thai_confidence", 0.0, float),
            ("source_count", 1, int),
            ("streams_collected", 0, int),
        ):
            try:
                sanitized[field] = converter(sanitized.get(field, default))
            except (ValueError, TypeError):
                sanitized[field] = default
        enabled_raw = str(sanitized.get("enabled", "true")).strip().lower()
        sanitized["enabled"] = enabled_raw in {"true", "1", "yes"}
        return sanitized
