#!/usr/bin/env python3
"""
Test script for visual identity review server.
"""

import sys
import json
import time
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.visual_identity_review.server import ReviewRequestHandler, DECISIONS_FILE, load_decisions, save_decisions

def test_server():
    server_address = ("127.0.0.1", 8765)
    httpd = HTTPServer(server_address, ReviewRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    base_url = "http://127.0.0.1:8765"
    print(f"[TEST] Server started on {base_url}")

    # 1. Test index / redirect
    req = urllib.request.Request(f"{base_url}/", headers={"User-Agent": "TestClient"})
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
    with opener.open(req) as resp:
        content = resp.read().decode("utf-8")
        assert "ThaiVtuberSNA" in content and "การตรวจสอบอัตลักษณ์ตัวละคร" in content, "Review UI HTML not returned"
        print("  [PASS] GET / -> serves visual identity review UI")

    # 2. Test master_creators.json endpoint
    req = urllib.request.Request(f"{base_url}/data/master_creators.json")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data.get("master_records", [])) == 4481, f"Expected 4481 records, got {len(data.get('master_records', []))}"
        assert len(data.get("unresolved_discovery_accounts", [])) == 884, f"Expected 884 discoveries, got {len(data.get('unresolved_discovery_accounts', []))}"
        print(f"  [PASS] GET /data/master_creators.json -> 4,481 records, 884 unresolved discoveries loaded")

    # 3. Test decisions endpoint
    req = urllib.request.Request(f"{base_url}/api/decisions")
    with urllib.request.urlopen(req) as resp:
        decisions = json.loads(resp.read().decode("utf-8"))
        assert isinstance(decisions, list), "Expected list of decisions"
        print(f"  [PASS] GET /api/decisions -> returned {len(decisions)} decisions")

    # 4. Test decision POST endpoint
    test_decision = {
        "discovery_id": "disc_test_001",
        "candidate_persona_id": "test_persona",
        "decision": "uncertain",
        "notes": "Test verification note",
        "reviewed_at": "2026-09-19T09:00:00Z"
    }
    req = urllib.request.Request(
        f"{base_url}/api/decision",
        data=json.dumps(test_decision).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        post_resp = json.loads(resp.read().decode("utf-8"))
        assert post_resp.get("status") == "ok"
        print(f"  [PASS] POST /api/decision -> recorded decision")

    # 5. Verify persistence
    loaded = load_decisions()
    assert any(d.get("discovery_id") == "disc_test_001" for d in loaded), "Decision not persisted to file"
    print(f"  [PASS] Decision persistence confirmed in {DECISIONS_FILE}")

    # Clean up test decision
    clean_decisions = [d for d in loaded if d.get("discovery_id") != "disc_test_001"]
    save_decisions(clean_decisions)
    print(f"  [PASS] Cleaned up test record, {len(clean_decisions)} decisions remaining.")

    httpd.shutdown()
    print("[ALL TESTS PASSED SUCCESSFULLY]")

if __name__ == "__main__":
    test_server()
