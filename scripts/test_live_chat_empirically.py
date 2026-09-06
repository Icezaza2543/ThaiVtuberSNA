"""
Thai VTuber Audience Network (SNA)
Empirical Live Chat Replay Validation Script

Tests 3 real YouTube VODs with live chat replay to empirically determine:
1. Does yt-dlp expose a stable author channel ID (authorExternalChannelId)?
2. Does the author ID match the YouTube channel ID pattern (UC...)?
3. Does the same author ID appear consistently across multiple chat messages?
4. Can we immediately hash the ID with HMAC-SHA256 and discard raw message payloads?
"""
import glob
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.hasher import hash_viewer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LiveChatValidation")

TEST_VIDEOS = [
    {"video_id": "FASPZW15oSo", "vtuber": "Baabel Ch.【ARP】"},
    {"video_id": "5o4H5e3QLk0", "vtuber": "Dacapo Ch.【ARP】"},
    {"video_id": "6iPQ-V8a3E8", "vtuber": "Baku Ch.【ARP】"}
]

CHANNEL_ID_REGEX = re.compile(r"^UC[a-zA-Z0-9_-]{22}$")


def extract_live_chat_in_memory(video_id: str) -> List[Dict[str, Any]]:
    """
    Downloads live chat subtitle directly in memory/temporary file,
    extracts author IDs, hashes them immediately, and deletes raw file immediately.
    """
    import yt_dlp
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    temp_prefix = f"temp_live_chat_{video_id}"
    
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["live_chat"],
        "outtmpl": f"{temp_prefix}.%(ext)s",
        "quiet": True,
        "no_warnings": True
    }

    raw_matched_actions = []
    temp_file = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)
        
        # Locate generated subtitle file
        candidates = glob.glob(f"{temp_prefix}*live_chat.json")
        if not candidates:
            logger.warning(f"No live_chat subtitle file created for {video_id}.")
            return []
        
        temp_file = candidates[0]
        
        # Read lines in memory only
        with open(temp_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    actions = data.get("replayChatItemAction", {}).get("actions", [])
                    for a in actions:
                        item = a.get("addChatItemAction", {}).get("item", {})
                        # Check text renderer and paid message renderer
                        renderer = item.get("liveChatTextMessageRenderer") or item.get("liveChatPaidMessageRenderer")
                        if renderer:
                            raw_channel_id = renderer.get("authorExternalChannelId")
                            msg_id = renderer.get("id")
                            timestamp_usec = renderer.get("timestampUsec")
                            
                            # Verify existence of raw channel ID
                            if raw_channel_id:
                                # PRIVACY CRITICAL: Hash immediately in memory
                                v_hash = hash_viewer(raw_channel_id)
                                raw_matched_actions.append({
                                    "raw_author_id": raw_channel_id,
                                    "viewer_hash": v_hash,
                                    "msg_id": msg_id,
                                    "timestamp_usec": timestamp_usec
                                })
                except Exception:
                    continue
    finally:
        # Mandatory cleanup: remove any temporary raw chat files
        for f in glob.glob(f"{temp_prefix}*"):
            try:
                os.remove(f)
            except Exception:
                pass

    return raw_matched_actions


def run_empirical_validation():
    print("=" * 65)
    print(" EMPIRICAL LIVE CHAT REPLAY AUTHOR ID VALIDATION ")
    print("=" * 65)

    all_passed = True
    results = {}

    for item in TEST_VIDEOS:
        vid = item["video_id"]
        vtuber = item["vtuber"]
        print(f"\nTesting VOD: {vid} ({vtuber})...")

        events = extract_live_chat_in_memory(vid)
        print(f" -> Total chat items extracted: {len(events)}")

        if not events:
            print(f" [FAIL] No chat items or author IDs extracted for {vid}!")
            all_passed = False
            results[vid] = {"status": "FAIL", "reason": "No live chat items found"}
            continue

        # Check 1: Stable YouTube Channel ID format
        valid_ids = [e["raw_author_id"] for e in events if CHANNEL_ID_REGEX.match(e["raw_author_id"])]
        id_validity_ratio = len(valid_ids) / len(events)
        print(f" -> Valid 'UC...' Channel ID ratio: {id_validity_ratio * 100:.1f}% ({len(valid_ids)}/{len(events)})")

        if id_validity_ratio < 0.95:
            print(" [FAIL] Less than 95% of events contained a valid YouTube Channel ID!")
            all_passed = False
            results[vid] = {"status": "FAIL", "reason": "Invalid channel ID ratio"}
            continue

        # Check 2: Viewer consistency (same viewer appears multiple times in same chat stream)
        author_freq = {}
        for e in events:
            aid = e["raw_author_id"]
            author_freq[aid] = author_freq.get(aid, 0) + 1

        multi_event_authors = {aid: cnt for aid, cnt in author_freq.items() if cnt > 1}
        print(f" -> Unique authors: {len(author_freq)}, Authors with multiple messages: {len(multi_event_authors)}")

        # Check 3: HMAC-SHA256 consistency
        hash_check_passed = True
        for e in events[:50]:
            recomputed = hash_viewer(e["raw_author_id"])
            if recomputed != e["viewer_hash"] or len(e["viewer_hash"]) != 64:
                hash_check_passed = False
                break
        print(f" -> HMAC-SHA256 Deterministic Hash Verified: {hash_check_passed}")

        if len(multi_event_authors) > 0 and hash_check_passed:
            print(f" [PASS] Empirically confirmed stable authorExternalChannelId for {vid}!")
            results[vid] = {
                "status": "PASS",
                "events_count": len(events),
                "unique_authors": len(author_freq),
                "multi_message_authors": len(multi_event_authors)
            }
        else:
            print(f" [FAIL] Author consistency check failed for {vid}!")
            all_passed = False
            results[vid] = {"status": "FAIL", "reason": "Author consistency check failed"}

    print("\n" + "=" * 65)
    print(" EMPIRICAL TEST SUMMARY:")
    for vid, res in results.items():
        print(f" - Video {vid}: {res['status']}")

    if all_passed:
        print("\nCONCLUSION: EMPIRICALLY CONFIRMED.")
        print("YouTube live chat replay exposes a stable 'authorExternalChannelId' (UC...)")
        print("which represents the actual YouTube channel ID of the viewer.")
        print("Raw payloads can be safely discarded immediately in memory after HMAC-SHA256.")
    else:
        print("\nCONCLUSION: LIMITATION FOUND.")
        print("Stop and report limitation. Do NOT fall back to display_name.")
    print("=" * 65)

    return all_passed


if __name__ == "__main__":
    success = run_empirical_validation()
    sys.exit(0 if success else 1)
