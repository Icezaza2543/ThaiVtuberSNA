#!/usr/bin/env python3
"""
Temporary Visual Identity Review Server for ThaiVtuberSNA
Serves the visual review UI and handles decision persistence.

Run with:
    python tools/visual_identity_review/server.py [port]
Default URL: http://127.0.0.1:8080/
"""

import os
import sys
import json
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DIR = REPO_ROOT / "tools" / "visual_identity_review"
DATA_DIR = REPO_ROOT / "data"
DECISIONS_FILE = REPO_ROOT / "data" / "entity_resolution" / "visual_identity_review.json"


def load_decisions():
    if not DECISIONS_FILE.exists():
        return []
    try:
        with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "decisions" in data:
                return data["decisions"]
            return []
    except Exception as e:
        print(f"[WARN] Error reading decisions file: {e}")
        return []


def save_decisions(decisions_list):
    DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "policy": "1 persona / 1 character form = 1 VTuber entity",
        "description": "Visual identity review decisions for unresolved discovery VTubers",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_decisions": len(decisions_list),
        "decisions": decisions_list,
    }
    temp_file = DECISIONS_FILE.with_suffix(".json.tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, DECISIONS_FILE)


class ReviewRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # API: get decisions
        if path == "/api/decisions":
            decisions = load_decisions()
            body = json.dumps(decisions, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Redirect root to review UI
        if path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/tools/visual_identity_review/")
            self.end_headers()
            return

        # Map path to local filesystem
        if path.startswith("/tools/visual_identity_review/"):
            rel_path = path[len("/tools/visual_identity_review/"):]
            if not rel_path or rel_path == "index.html":
                file_path = REVIEW_DIR / "index.html"
            else:
                file_path = REVIEW_DIR / rel_path
        elif path.startswith("/data/"):
            file_path = REPO_ROOT / path.lstrip("/")
        else:
            file_path = REPO_ROOT / path.lstrip("/")

        if file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = "application/octet-stream"
            if file_path.suffix == ".json":
                mime_type = "application/json"

            try:
                content = file_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "json" in mime_type else mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error reading file: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")

    def do_POST(self):
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            body_json = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode("utf-8"))
            return

        if path == "/api/decision":
            discovery_id = body_json.get("discovery_id")
            if not discovery_id:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Missing discovery_id"}')
                return

            decisions = load_decisions()
            # Find and replace, or append
            idx = next((i for i, d in enumerate(decisions) if d.get("discovery_id") == discovery_id), -1)
            if idx >= 0:
                decisions[idx] = body_json
            else:
                decisions.append(body_json)

            save_decisions(decisions)
            resp = json.dumps({"status": "ok", "total_decisions": len(decisions)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        elif path == "/api/save_all":
            new_list = body_json.get("decisions", [])
            save_decisions(new_list)
            resp = json.dumps({"status": "ok", "count": len(new_list)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'{"error": "Not found"}')


def run(port=8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, ReviewRequestHandler)
    print(f"==================================================")
    print(f"ThaiVtuberSNA Visual Identity Review Server")
    print(f"==================================================")
    print(f"Local URL:  http://127.0.0.1:{port}/")
    print(f"Master:     {DATA_DIR / 'master_creators.json'}")
    print(f"Decisions:  {DECISIONS_FILE}")
    print(f"Press Ctrl+C to stop.")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
