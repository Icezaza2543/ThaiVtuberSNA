"""
Thai VTuber Audience Network (SNA)
Privacy Hasher & Persistent Key Manager

Implements HMAC-SHA256 pseudonymization for YouTube viewer channel IDs.
Preserves longitudinal network continuity by enforcing a persistent, stable secret key:
- Reads key from config/secret.key (environment overrides are disabled).
- Fails loudly if key is missing or unexpectedly changed (fingerprint continuity check).
- NEVER auto-generates an ephemeral key on real data runs.

Security & Operational Requirements:
1. config/secret.key MUST be gitignored (never commit or export the raw key).
2. Fingerprint is a CONTINUITY CHECK to detect accidental key replacement across runs,
   not cryptographic integrity against an active attacker with local file access.
3. Recommend encrypted/offline backup: losing this key permanently breaks longitudinal
   viewer identity compatibility across all historical Parquet snapshots.
"""
import argparse
import hashlib
import hmac
import logging
import os
from pathlib import Path
import secrets
import sys
from typing import Optional

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import SECRET_KEY_PATH, SECRET_FINGERPRINT_PATH, SALT_SECRET

logger = logging.getLogger(__name__)


def compute_key_fingerprint(key_bytes: bytes) -> str:
    """Computes SHA-256 fingerprint for continuity checking."""
    return hashlib.sha256(key_bytes).hexdigest()


def init_persistent_secret_key(force: bool = False) -> str:
    """
    Explicitly initializes a NEW identity only; never overwrites existing identity records.
    Writes key to config/secret.key and fingerprint to config/secret.fingerprint.
    RECOMMENDATION: Keep an encrypted/offline backup of config/secret.key!
    """
    if SECRET_KEY_PATH.exists() or SECRET_FINGERPRINT_PATH.exists():
        raise RuntimeError(
            f"FATAL: Key already exists at {SECRET_KEY_PATH}. "
            "Overwriting will permanently break longitudinal viewer identity compatibility! "
            "Restore the original key; initialization cannot overwrite an existing identity."
        )

    # Generate 256-bit cryptographically secure secret
    new_key = secrets.token_hex(32)
    SECRET_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(os.open(SECRET_KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
        f.write(new_key.strip())

    fingerprint = compute_key_fingerprint(new_key.strip().encode("utf-8"))
    with open(SECRET_FINGERPRINT_PATH, "w", encoding="utf-8") as f:
        f.write(fingerprint.strip())

    logger.info(f"Initialized persistent secret key at {SECRET_KEY_PATH}")
    logger.info(f"Key continuity fingerprint recorded: {fingerprint[:16]}...")
    logger.warning("IMPORTANT: Backup config/secret.key to an encrypted offline location. Losing it breaks all historical viewer linkages!")
    return new_key


def load_persistent_secret_key() -> bytes:
    """
    Loads and validates the persistent secret key.
    FAILS LOUDLY if:
    1. Key is missing
    2. Key fingerprint mismatch (continuity check failure - accidental key swap detected)
    """
    # 2. Check persistent key file
    if not SECRET_KEY_PATH.exists():
        raise RuntimeError(
            "\n" + "=" * 65 + "\n"
            "FATAL ERROR: Persistent secret key missing!\n"
            f"File not found: {SECRET_KEY_PATH}\n\n"
            "To prevent breaking longitudinal network continuity, the system\n"
            "refuses to auto-generate an ephemeral secret for real data runs.\n\n"
            "To initialize a permanent key for this environment, run:\n"
            "    python -m core.hasher --init-key\n"
            "For existing data, restore the ORIGINAL key from encrypted offline backup.\n"
            + "=" * 65
        )

    with open(SECRET_KEY_PATH, "r", encoding="utf-8") as f:
        key_str = f.read().strip()

    if not key_str:
        raise RuntimeError(f"FATAL ERROR: Persistent key file {SECRET_KEY_PATH} is empty!")

    key_bytes = key_str.encode("utf-8")

    # 3. Continuity check: Verify fingerprint to catch accidental key swaps
    if not SECRET_FINGERPRINT_PATH.exists():
        raise RuntimeError("FATAL CONTINUITY CHECK ERROR: Missing key fingerprint; restore the continuity record.")
    if SECRET_FINGERPRINT_PATH.exists():
        with open(SECRET_FINGERPRINT_PATH, "r", encoding="utf-8") as f:
            expected_fp = f.read().strip()
        actual_fp = compute_key_fingerprint(key_bytes)
        if expected_fp != actual_fp:
            raise RuntimeError(
                "\n" + "=" * 65 + "\n"
                "FATAL CONTINUITY CHECK ERROR: Key fingerprint mismatch!\n"
                f"The key at {SECRET_KEY_PATH} does not match {SECRET_FINGERPRINT_PATH}.\n"
                f"Expected fingerprint: {expected_fp}\n"
                f"Actual fingerprint:   {actual_fp}\n\n"
                "An unexpected key replacement breaks historical viewer identity linkage across runs.\n"
                "Restore the original secret key from your offline backup.\n"
                + "=" * 65
            )

    return key_bytes


class PrivacyHasher:
    def __init__(self, secret_salt: Optional[str] = None):
        if secret_salt:
            self.secret_salt = secret_salt.encode("utf-8")
        else:
            self.secret_salt = load_persistent_secret_key()

    def hash_viewer_id(self, raw_channel_id: str) -> str:
        """
        Creates a deterministic one-way HMAC-SHA256 hash from a YouTube Channel ID.
        """
        if not raw_channel_id or not isinstance(raw_channel_id, str):
            raise ValueError("raw_channel_id must be a non-empty string")

        cleaned_id = raw_channel_id.strip()
        if not cleaned_id:
            raise ValueError("raw_channel_id must not be whitespace")
        h = hmac.new(self.secret_salt, cleaned_id.encode("utf-8"), hashlib.sha256)
        return h.hexdigest()

    def verify_hash(self, raw_channel_id: str, hashed_id: str) -> bool:
        """Verifies if a raw_channel_id matches the given hashed_id."""
        return hmac.compare_digest(self.hash_viewer_id(raw_channel_id), hashed_id)


def hash_viewer(channel_id: str) -> str:
    """Convenience helper using the persistent key."""
    hasher = PrivacyHasher()
    return hasher.hash_viewer_id(channel_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HMAC Key Management Tool")
    parser.add_argument("--init-key", action="store_true", help="Initialize persistent secret key")
    parser.add_argument("--verify-key", action="store_true", help="Verify persistent secret key continuity")
    parser.add_argument("--force", action="store_true", help="Deprecated; existing identities are never overwritten")

    args = parser.parse_args()

    if args.init_key:
        try:
            init_persistent_secret_key(force=args.force)
            print("Successfully created persistent secret key.")
        except RuntimeError as e:
            print(e)
            sys.exit(1)
    elif args.verify_key or len(sys.argv) == 1:
        try:
            k = load_persistent_secret_key()
            fp = compute_key_fingerprint(k)
            print(f"Key OK. Fingerprint: {fp[:16]}... ({len(k)} bytes)")
        except RuntimeError as e:
            print(e)
            sys.exit(1)
