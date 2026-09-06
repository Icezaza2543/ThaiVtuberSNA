"""
Thai VTuber Audience Network (SNA)
First Filter Engine

Evaluates candidate VTuber channels using rule-based heuristics.
Assigns status: ACCEPT, REVIEW, REJECT, DORMANT.
NO LLM is used as default classifier.
"""
import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from config.settings import FILTER_RULES


class FirstFilterEngine:
    # Known Thai VTuber agencies and groups
    KNOWN_THAI_AGENCIES = [
        "algorhythm project", "arp", "polygon", "pixela", "horganice",
        "myriad colors", "virtual union", "chocola", "daisy", "sorax"
    ]

    def __init__(self, rules: Dict[str, Any] = None):
        self.rules = rules or FILTER_RULES
        self.thai_char_pattern = re.compile(r"[\u0e00-\u0e7f]")

    def calculate_thai_confidence(self, name: str, description: str, handle: str) -> float:
        """
        Calculates confidence score (0.0 to 1.0) that the channel is Thai.
        """
        score = 0.0
        combined_text = f"{name} {description} {handle}".lower()

        # Thai character presence
        thai_chars = self.thai_char_pattern.findall(combined_text)
        if len(thai_chars) >= 5:
            score += 0.40
        elif len(thai_chars) >= 1:
            score += 0.20

        # Thai keywords / tokens check
        matched_keywords = [kw for kw in self.rules["thai_keywords"] if kw in combined_text]
        if matched_keywords:
            score += min(0.35, len(matched_keywords) * 0.15)

        # Agency match
        for agency in self.KNOWN_THAI_AGENCIES:
            if agency in combined_text:
                score += 0.30
                break

        # Handle suffix like "TH" or "OfficialTH"
        if re.search(r"(th|thai)$", handle.lower().replace("@", "")):
            score += 0.15

        return min(1.0, round(score, 2))

    def calculate_vtuber_signal(self, name: str, description: str) -> bool:
        """Checks for clear VTuber indicators."""
        combined_text = f"{name} {description}".lower()
        vtuber_terms = ["vtuber", "virtual youtuber", "วีทูปเบอร์", "live2d", "3d avatar", "virtual streamer"]
        return any(term in combined_text for term in vtuber_terms)

    def evaluate_candidate(self, candidate: Dict[str, Any]) -> Tuple[str, float, str]:
        """
        Evaluates a candidate VTuber.
        Returns: (status, thai_confidence, reason)
        Statuses: ACCEPT, REVIEW, REJECT, DORMANT
        """
        # Manual approval override
        if candidate.get("manual_approval") is True:
            return "ACCEPT", 1.0, "Manual approval granted"
        elif candidate.get("manual_approval") is False:
            return "REJECT", 0.0, "Manual rejection specified"

        name = candidate.get("name", "")
        desc = candidate.get("description", "")
        handle = candidate.get("handle", "")
        subs = candidate.get("subscriber_count", 0)
        source_count = candidate.get("source_count", 1)
        agency = candidate.get("agency", "").lower()

        thai_confidence = self.calculate_thai_confidence(name, desc, handle)
        is_vtuber = self.calculate_vtuber_signal(name, desc) or any(
            known in agency for known in self.KNOWN_THAI_AGENCIES
        )

        # Check Dormancy
        last_seen = candidate.get("last_seen")
        if last_seen:
            try:
                # Handle ISO format
                if isinstance(last_seen, str):
                    last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                else:
                    last_dt = last_seen
                days_since_seen = (datetime.now(timezone.utc) - last_dt).days
                if days_since_seen > self.rules["dormant_days_threshold"]:
                    return "DORMANT", thai_confidence, f"Inactive for {days_since_seen} days"
            except Exception:
                pass

        # Reject if no Thai confidence and no VTuber signal
        if thai_confidence < 0.2 and not is_vtuber:
            return "REJECT", thai_confidence, "No Thai language or VTuber signal detected"

        # Check Subscriber floor
        if subs < self.rules["min_subscribers"] and source_count < 2:
            return "REVIEW", thai_confidence, f"Low subscribers ({subs}) and single source"

        # Strong Thai agency affiliation -> Instant ACCEPT
        if any(known in agency for known in self.KNOWN_THAI_AGENCIES):
            return "ACCEPT", max(0.9, thai_confidence), "Verified Thai VTuber agency member"

        # High confidence Thai + confirmed VTuber + multi-directory source -> ACCEPT
        if thai_confidence >= self.rules["min_thai_confidence"] and is_vtuber:
            return "ACCEPT", thai_confidence, "High Thai confidence and verified VTuber signal"

        # Moderate signals -> REVIEW
        if thai_confidence >= 0.35 or is_vtuber:
            return "REVIEW", thai_confidence, "Moderate signals, needs manual verification"

        return "REJECT", thai_confidence, "Insufficient Thai VTuber indicators"
