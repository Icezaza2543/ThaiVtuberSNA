"""
Thai VTuber Audience Network (SNA)
Registry Manager (Control Plane)

Implements Google Sheets Registry integration with seamless Local Fallback (CSV/JSON).
Manages sheets: VTUBERS, SYSTEM, NETWORK_RESULT.
"""
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import GOOGLE_SHEETS_CONFIG, DATA_DIR

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
    "enabled"
]

NETWORK_RESULT_COLUMNS = [
    "vtuber_a",
    "vtuber_b",
    "shared_viewers",
    "jaccard",
    "overlap_coefficient",
    "calculated_at"
]


class RegistryManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or GOOGLE_SHEETS_CONFIG
        self.local_csv_path = Path(self.config["local_fallback_path"])
        self.local_system_path = DATA_DIR / "registry_system.json"
        self.local_network_path = DATA_DIR / "network_results.csv"
        self._gsheet_client = None
        self._spreadsheet = None
        self._init_gsheet_if_configured()

    def _init_gsheet_if_configured(self):
        """Attempts to initialize gspread connection if credentials exist."""
        cred_path = Path(self.config.get("credentials_path", ""))
        sheet_id = self.config.get("spreadsheet_id", "")
        
        if cred_path.exists() and sheet_id:
            try:
                import gspread
                self._gsheet_client = gspread.service_account(filename=str(cred_path))
                self._spreadsheet = self._gsheet_client.open_by_key(sheet_id)
                logger.info(f"Connected to Google Sheets: {sheet_id}")
            except Exception as e:
                logger.warning(f"Could not connect to Google Sheets, using local fallback: {e}")
                self._gsheet_client = None
        else:
            logger.info("Using local CSV/JSON registry (Google Sheets credentials not set).")

    # ------------------ VTUBERS SHEET ------------------

    def load_vtubers(self) -> List[Dict[str, Any]]:
        """Loads all VTubers from Google Sheet or Local CSV."""
        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_vtubers"])
                records = worksheet.get_all_records()
                return self._sanitize_records(records)
            except Exception as e:
                logger.error(f"Failed to read from Google Sheet: {e}. Falling back to local CSV.")

        # Local fallback
        if not self.local_csv_path.exists():
            return []

        vtubers = []
        with open(self.local_csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vtubers.append(self._sanitize_row(row))
        return vtubers

    def save_vtubers(self, vtubers: List[Dict[str, Any]]):
        """Saves VTubers list to Local CSV and Google Sheet if available."""
        # Always write to local CSV for resilience
        self.local_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=VTUBERS_COLUMNS)
            writer.writeheader()
            for v in vtubers:
                row = {col: v.get(col, "") for col in VTUBERS_COLUMNS}
                writer.writerow(row)

        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_vtubers"])
                rows = [VTUBERS_COLUMNS]
                for v in vtubers:
                    rows.append([str(v.get(col, "")) for col in VTUBERS_COLUMNS])
                worksheet.clear()
                worksheet.update(rows)
            except Exception as e:
                logger.error(f"Failed to sync with Google Sheets: {e}")

    def get_enabled_vtubers(self) -> List[Dict[str, Any]]:
        """Returns only VTubers that are ACCEPTED and enabled=True."""
        all_vtubers = self.load_vtubers()
        return [
            v for v in all_vtubers
            if str(v.get("enabled", "")).lower() in ["true", "1", "yes"] and v.get("status") == "ACCEPT"
        ]

    def update_vtuber(self, channel_id: str, updates: Dict[str, Any]):
        """Updates attributes of a specific VTuber in registry."""
        vtubers = self.load_vtubers()
        updated = False
        for v in vtubers:
            if v.get("channel_id") == channel_id:
                v.update(updates)
                updated = True
                break
        if updated:
            self.save_vtubers(vtubers)

    # ------------------ SYSTEM SHEET ------------------

    def update_system_status(self, updates: Dict[str, Any]):
        """Updates system monitoring metadata."""
        current_status = {}
        if self.local_system_path.exists():
            try:
                with open(self.local_system_path, "r", encoding="utf-8") as f:
                    current_status = json.load(f)
            except Exception:
                current_status = {}

        current_status.update(updates)
        current_status["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(self.local_system_path, "w", encoding="utf-8") as f:
            json.dump(current_status, f, indent=2, ensure_ascii=False)

        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_system"])
                rows = [["Metric", "Value"]]
                for k, val in current_status.items():
                    rows.append([str(k), str(val)])
                worksheet.clear()
                worksheet.update(rows)
            except Exception as e:
                logger.warning(f"Failed to sync SYSTEM sheet: {e}")

    # ------------------ NETWORK RESULT SHEET ------------------

    def save_network_results(self, results: List[Dict[str, Any]]):
        """Saves SNA Overlap matrix results to local CSV and Google Sheet."""
        with open(self.local_network_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=NETWORK_RESULT_COLUMNS)
            writer.writeheader()
            for r in results:
                row = {col: r.get(col, "") for col in NETWORK_RESULT_COLUMNS}
                writer.writerow(row)

        if self._spreadsheet:
            try:
                worksheet = self._spreadsheet.worksheet(self.config["sheet_network"])
                rows = [NETWORK_RESULT_COLUMNS]
                for r in results:
                    rows.append([str(r.get(col, "")) for col in NETWORK_RESULT_COLUMNS])
                worksheet.clear()
                worksheet.update(rows)
            except Exception as e:
                logger.warning(f"Failed to sync NETWORK_RESULT sheet: {e}")

    # ------------------ SANITIZATION HELPERS ------------------

    def _sanitize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._sanitize_row(r) for r in records]

    def _sanitize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures proper types for numerical and boolean fields."""
        sanitized = dict(row)
        try:
            sanitized["subscriber_count"] = int(sanitized.get("subscriber_count", 0))
        except (ValueError, TypeError):
            sanitized["subscriber_count"] = 0

        try:
            sanitized["thai_confidence"] = float(sanitized.get("thai_confidence", 0.0))
        except (ValueError, TypeError):
            sanitized["thai_confidence"] = 0.0

        try:
            sanitized["source_count"] = int(sanitized.get("source_count", 1))
        except (ValueError, TypeError):
            sanitized["source_count"] = 1

        try:
            sanitized["streams_collected"] = int(sanitized.get("streams_collected", 0))
        except (ValueError, TypeError):
            sanitized["streams_collected"] = 0

        enabled_raw = str(sanitized.get("enabled", "true")).strip().lower()
        sanitized["enabled"] = enabled_raw in ["true", "1", "yes"]

        return sanitized
