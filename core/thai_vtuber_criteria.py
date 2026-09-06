"""
Thai VTuber Audience Network (SNA)
Thai VTuber Criteria & Identity Verification Engine

Defines explicit, objective criteria for classifying Thai VTubers:
1. Criteria for Thai VTuber confirmation vs unconfirmed quarantine.
2. Channel activity lifecycle: active, hiatus, graduated, unknown.
3. Person vs Multi-Channel mapping (1 person multiple channels vs distinct persons).
"""
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List

# Known Thai VTuber agencies and professional groups
KNOWN_THAI_AGENCIES = [
    "Algorhythm Project", "ARP",
    "Polygon Official", "Polygon Project", "Polygon Production",
    "Pixela Project", "Pixela Isekai", "Pixela Retro",
    "Lumina Live", "Lumina",
    "Euphora Project", "Euphora",
    "Myriad Colors",
    "Virtual Union",
    "Chocola", "Daisy", "Sorax", "Horganice",
    "A-Live", "Mori Project", "Genesis VT",
    # Audited Thai Agencies & Groups
    "OAL", "V.W.Y", "ATX", "DPX", "EXia", "ALF", "Autumnia",
    "Flora Project", "Paralist", "VZ", "RPG", "Pandora", "Ti19t",
    "Vtopia", "WACTOR", "HZ", "EYLZ"
]

# Canonical multi-channel person mappings (Known cases where 1 person has multiple channels)
KNOWN_PERSON_CHANNELS = {
    # Aisha Channel (Main) & Aisha Sub/Music
    "UCqhhWjpw23dWhJ5rRwCCrMA": {"person_id": "vtuber_aisha", "canonical_name": "Aisha", "channel_type": "main"},
    "UC5VPIoY1j_x9UZSqkpwg8jw": {"person_id": "vtuber_aisha", "canonical_name": "Aisha", "channel_type": "sub"},
    # Baabel ARP
    "UCAr4U_HGMYXn1EZjdWiGSLQ": {"person_id": "vtuber_baabel", "canonical_name": "Baabel ARP", "channel_type": "main"},
    # Dacapo ARP
    "UCuZ1ajvlGFUMCHZAPdetKHw": {"person_id": "vtuber_dacapo", "canonical_name": "Dacapo ARP", "channel_type": "main"},
    # Schneider ARP
    "UCNTEr2_96vJnXNazr5MwNLA": {"person_id": "vtuber_schneider", "canonical_name": "Schneider ARP", "channel_type": "main"},
    # Hoku Polygon
    "UCZilc7jP-X_92Fii1uTIs0Q": {"person_id": "vtuber_hoku", "canonical_name": "Hoku Polygon", "channel_type": "main"},
    # Tiara Rexa Polygon
    "UCfcNIwkAhHcDTP1rQg2n5nw": {"person_id": "vtuber_tiara_rexa", "canonical_name": "Tiara Rexa", "channel_type": "main"},
    # Minami Cera Polygon
    "UCEvyDOkcGkzCTo62d9BrhkA": {"person_id": "vtuber_minami_cera", "canonical_name": "Minami Cera", "channel_type": "main"},
    # Baku ARP
    "UCO6R8Pc5g2R7ObJQPBGppdg": {"person_id": "vtuber_baku", "canonical_name": "Baku ARP", "channel_type": "main"},
    # Shimonz
    "UCt8vlwt6qi6P1mz5uuStJCA": {"person_id": "vtuber_shimonz", "canonical_name": "Shimonz", "channel_type": "main"},
    # Shino Laila (WACTOR Gen 2)
    "UCFSkExeBcqI4nb_ArHeByNw": {"person_id": "vtuber_shino_laila", "canonical_name": "Shino Laila", "channel_type": "main"},
}

THAI_CHAR_REGEX = re.compile(r"[\u0e00-\u0e7f]")
VTUBER_KEYWORDS = [
    "vtuber", "virtual youtuber", "วีทูปเบอร์", "วีทูบเบอร์", "วีทูป", "virtual streamer",
    "live2d", "3d avatar", "virtual idol", "vtuberth", "thaivtuber", "thai vtuber"
]


class ThaiVtuberCriteriaEngine:
    def __init__(self, active_days_threshold: int = 180):
        self.active_days_threshold = active_days_threshold

    def calculate_thai_confidence(self, name: str, description: str, handle: str, country: str = "") -> float:
        """
        Evaluates linguistic and geographic evidence that the channel is Thai.
        Returns confidence score between 0.0 and 1.0.
        """
        score = 0.0
        combined = f"{name} {description} {handle}".lower()

        # Thai character count
        thai_chars = THAI_CHAR_REGEX.findall(combined)
        if len(thai_chars) >= 10:
            score += 0.45
        elif len(thai_chars) >= 3:
            score += 0.30
        elif len(thai_chars) >= 1:
            score += 0.15

        # Country specified as TH
        if country.upper() == "TH":
            score += 0.35

        # Suffix or keyword like "TH", "Thai", "Thailand"
        if re.search(r"(\bth\b|thai|thailand|officialth)", combined):
            score += 0.20

        # Handle ending in th
        if handle.lower().replace("@", "").endswith("th"):
            score += 0.15

        return min(1.0, round(score, 2))

    def detect_vtuber_signal(self, name: str, description: str, agency: str = "") -> Tuple[bool, List[str]]:
        """
        Checks for explicit VTuber persona declarations in title, description, or agency.
        """
        combined = f"{name} {description}".lower()
        matched_signals = []

        for kw in VTUBER_KEYWORDS:
            if kw in combined:
                matched_signals.append(kw)

        # Agency match
        for ag in KNOWN_THAI_AGENCIES:
            if ag.lower() in combined or ag.lower() in agency.lower():
                matched_signals.append(f"agency:{ag}")
                break

        is_vtuber = len(matched_signals) > 0
        return is_vtuber, matched_signals

    def determine_agency(self, name: str, description: str, existing_agency: str = "") -> str:
        """
        Infers or normalizes agency affiliation from title, description, or existing tag.
        """
        if existing_agency and existing_agency not in ["Independent", "Other", "None", ""]:
            return existing_agency

        combined = f"{name} {description}".lower()
        if "arp" in combined or "algorhythm" in combined:
            return "Algorhythm Project"
        elif "polygon" in combined:
            return "Polygon Official"
        elif "pixela" in combined:
            return "Pixela Project"
        elif "lumina" in combined:
            return "Lumina Live"
        elif "euphora" in combined:
            return "Euphora Project"
        elif "myriad colors" in combined:
            return "Myriad Colors"
        elif "virtual union" in combined:
            return "Virtual Union"
        elif "horganice" in combined:
            return "Horganice"

        return "Independent"

    def determine_activity_status(
        self,
        last_published_video_at: Optional[str],
        channel_status: str = "public",
        is_graduated: bool = False,
        now_dt: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Determines activity lifecycle: active, hiatus, graduated, unknown.
        """
        if is_graduated:
            return "graduated", "Formally graduated / retired"

        if channel_status in ["closed", "terminated", "unavailable", "private"]:
            return "unknown", f"Channel unavailable ({channel_status})"

        if not last_published_video_at:
            return "unknown", "No public video history recorded"

        now = now_dt or datetime.now(timezone.utc)
        try:
            if isinstance(last_published_video_at, str):
                ts = last_published_video_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
            else:
                dt = last_published_video_at

            days_diff = (now - dt).days
            if days_diff <= self.active_days_threshold:
                return "active", f"Active (last video published {days_diff} days ago)"
            else:
                return "hiatus", f"Hiatus / Inactive for {days_diff} days (> {self.active_days_threshold}d)"
        except Exception as e:
            return "unknown", f"Unable to parse publication timestamp: {e}"

    def resolve_person_identity(self, channel_id: str, name: str, handle: str) -> Tuple[str, str, str]:
        """
        Maps a channel to canonical person ID, canonical name, and channel type.
        Separates 1 person multiple channels from distinct persons.
        """
        if channel_id in KNOWN_PERSON_CHANNELS:
            info = KNOWN_PERSON_CHANNELS[channel_id]
            return info["person_id"], info["canonical_name"], info["channel_type"]

        # Default: 1 channel maps to 1 person
        clean_handle = handle.replace("@", "").strip()
        slug = clean_handle if clean_handle else re.sub(r"[^a-zA-Z0-9_]", "", name.lower())
        if not slug:
            slug = channel_id[-8:]
        person_id = f"vtuber_{slug.lower()}"
        channel_type = "main"

        # Detect subchannel / music channel indicators
        name_lower = name.lower()
        if any(sub_term in name_lower for sub_term in ["ch.2", "sub", "music", "shorts", "clips", "archive"]):
            channel_type = "sub"

        return person_id, name, channel_type

    def evaluate_vtuber(
        self,
        channel_id: str,
        name: str,
        description: str,
        handle: str,
        country: str = "",
        sources: Optional[List[str]] = None,
        last_published_video_at: Optional[str] = None,
        is_graduated_hint: bool = False,
        channel_status: str = "public"
    ) -> Dict[str, Any]:
        """
        Full evaluation of a candidate channel according to project requirements.
        Returns a dict conforming to Phase 1 Registry schema.
        """
        sources = sources or []
        agency = self.determine_agency(name, description)
        thai_conf = self.calculate_thai_confidence(name, description, handle, country)
        is_vtuber, signals = self.detect_vtuber_signal(name, description, agency)

        # Activity lifecycle
        activity_status, activity_reason = self.determine_activity_status(
            last_published_video_at, channel_status, is_graduated_hint
        )

        # Person identity separation
        person_id, canonical_name, channel_type = self.resolve_person_identity(channel_id, name, handle)

        # Criteria decision:
        # 1. Stated VTuber / agency + Thai language/sources -> CONFIRMED
        # 2. Strong Thai directory source (Chuysan or Fandom) + Thai confidence -> CONFIRMED
        # 3. Weak signals / ambiguous -> UNCONFIRMED (quarantine for manual audit)
        is_from_verified_directory = any(s in ["Thai VTuber Ranking", "Virtual YouTuber Fandom Wiki", "Seed List"] for s in sources)
        
        evidence_notes = []
        if is_vtuber:
            evidence_notes.append(f"VTuber signals: {', '.join(signals)}")
        if agency != "Independent":
            evidence_notes.append(f"Agency: {agency}")
        if thai_conf >= 0.3:
            evidence_notes.append(f"Thai confidence: {thai_conf:.2f}")
        if sources:
            evidence_notes.append(f"Sources: {', '.join(sources)}")
        evidence_notes.append(activity_reason)

        is_confirmed = False
        if agency in [a for a in KNOWN_THAI_AGENCIES]:
            is_confirmed = True
        elif is_vtuber and (thai_conf >= 0.25 or is_from_verified_directory):
            is_confirmed = True
        elif is_from_verified_directory and (thai_conf >= 0.30 or country == "TH"):
            is_confirmed = True
        elif is_from_verified_directory and len(sources) >= 2:
            is_confirmed = True

        vtuber_status = "CONFIRMED" if is_confirmed else "UNCONFIRMED"

        return {
            "channel_id": channel_id,
            "name": name,
            "handle": handle,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "agency": agency,
            "activity_status": activity_status,
            "vtuber_status": vtuber_status,
            "person_id": person_id,
            "canonical_name": canonical_name,
            "channel_type": channel_type,
            "thai_confidence": thai_conf,
            "reference_sources": "; ".join(sources),
            "checked_date": datetime.now(timezone.utc).isoformat(),
            "evidence_notes": "; ".join(evidence_notes),
            "enabled": (vtuber_status == "CONFIRMED" and activity_status in ["active", "hiatus"])
        }
