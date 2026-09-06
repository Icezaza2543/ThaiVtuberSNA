"""Legacy replay probe disabled: its downloader persisted raw chat to temporary files.

Deleting raw files afterward does not satisfy the no-persistence requirement.
A future bounded, memory-only live-chat adapter must be validated before use.
"""

def extract_live_chat_in_memory(video_id):
    raise NotImplementedError(
        "Replay collection disabled: previous implementation wrote raw chat to disk. "
        "No network request or raw file write was performed."
    )

if __name__ == "__main__":
    raise SystemExit("BLOCKED: memory-only live-chat replay adapter is not implemented")
