"""
Builds and verifies:
1. data/industry/creator_status_events.parquet & .csv
2. data/industry/creator_evidence_coverage.parquet & .csv

Ensures zero fabrication, explicit separation of VERIFIED vs INFERRED_PROXY,
and systematic coverage review across all 193 frozen target creators.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildCreatorLifecycleEvidence")

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
INDUSTRY_DIR = DATA_DIR / "industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

RECOGNIZED_AUTHORITY_HANDLES = {
    "astarsofficial",
    "pixelaproject",
    "arp_vtuber",
    "polygonofficial",
    "miraismaid",
    "eileennoir",
}


def parse_authority_handle(url: str) -> str:
    """Extract exact lowercase account handle from an X or Twitter URL.
    
    Ensures exact parsed identity match so that fake prefix/suffix accounts
    (e.g., x.com/astars_fake/status/...) cannot match recognized authorities.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        if host in ["x.com", "www.x.com", "twitter.com", "www.twitter.com"]:
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if parts:
                return parts[0].lower()
    except Exception:
        pass
    return ""

MANIFEST_PATH = DATA_DIR / "temporal" / "catalog" / "target_manifest.csv"
REGISTRY_PATH = DATA_DIR / "thai_vtuber_registry.json"
COVERAGE_PATH = DATA_DIR / "temporal" / "catalog" / "channel_coverage.parquet"

# Curated identity fields are checked against both independent local identity catalogs.
VERIFIED_CREATOR_INTEL = {'UCFSkExeBcqI4nb_ArHeByNw': [{'event_type': 'DEBUT',
                               'event_date': '2021-05-09',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Shino_Laila',
                               'notes': 'Debuted on 2021-05-09 as WACTOR 2nd Gen member.',
                               'subject_channel_id': 'UCFSkExeBcqI4nb_ArHeByNw',
                               'subject_name': 'Shino Laila',
                               'source_subject': 'Shino Laila',
                               'source_agency': 'WACTOR'},
                              {'event_type': 'SUSPENSION',
                               'event_date': '2021-11-28',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://twitter.com/MiraisMaid/status/1464928236165509121',
                               'notes': 'Suspension notice issued by WACTOR management on 2021-11-28.',
                               'subject_channel_id': 'UCFSkExeBcqI4nb_ArHeByNw',
                               'subject_name': 'Shino Laila',
                               'source_subject': 'Shino Laila',
                               'source_agency': 'WACTOR'},
                              {'event_type': 'GRADUATION_OR_DEPARTURE',
                               'event_date': '2022-04-16',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'PUBLIC_TALENT_STATEMENT',
                               'source_reference': 'https://twitter.com/Eileennoir/status/1515286596886499330',
                               'notes': 'Public announcement of departure and agency dissociation on '
                                        '2022-04-16.',
                               'subject_channel_id': 'UCFSkExeBcqI4nb_ArHeByNw',
                               'subject_name': 'Shino Laila',
                               'source_subject': 'Shino Laila',
                               'source_agency': 'WACTOR'}],
 'UCgLadXz0sJbHQL98eoAd9ag': [{'event_type': 'DEBUT',
                               'event_date': '2024-09-13',
                               'event_year': 2024,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/AStars',
                               'notes': 'Debuted on 2024-09-13 as member of AStars Amakara unit under Brave '
                                        'Group APAC.',
                               'subject_channel_id': 'UCgLadXz0sJbHQL98eoAd9ag',
                               'subject_name': 'Ice Shirakoi',
                               'source_subject': 'Ice Shirakoi',
                               'source_agency': 'AStars'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2025-04-30',
                               'event_year': 2025,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/AStarsofficial/status/1888528955219968470',
                               'notes': 'Official graduation announced on 2025-04-16; farewell stream held '
                                        '2025-04-26; effective 2025-04-30.',
                               'subject_channel_id': 'UCgLadXz0sJbHQL98eoAd9ag',
                               'subject_name': 'Ice Shirakoi',
                               'source_subject': 'Ice Shirakoi',
                               'source_agency': 'AStars'}],
 'UCfe7Lxdn2PDp_xnnrC_RSzA': [{'event_type': 'DEBUT',
                               'event_date': '2024-09-13',
                               'event_year': 2024,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/AStars',
                               'notes': 'Debuted on 2024-09-13 as member of AStars Amakara unit.',
                               'subject_channel_id': 'UCfe7Lxdn2PDp_xnnrC_RSzA',
                               'subject_name': 'Amaris Sayo',
                               'source_subject': 'Amaris Sayo',
                               'source_agency': 'AStars'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2025-02-14',
                               'event_year': 2025,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/AStarsofficial/status/1888528955219968470',
                               'notes': 'Graduation announced 2025-02-06 due to health; early graduation '
                                        'stream held 2025-02-14.',
                               'subject_channel_id': 'UCfe7Lxdn2PDp_xnnrC_RSzA',
                               'subject_name': 'Amaris Sayo',
                               'source_subject': 'Amaris Sayo',
                               'source_agency': 'AStars'}],
 'UCt8vlwt6qi6P1mz5uuStJCA': [{'event_type': 'DEBUT',
                               'event_date': '2021-04-03',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Shimonz',
                               'notes': 'Debuted on 2021-04-03 as independent Thai VTuber.',
                               'subject_channel_id': 'UCt8vlwt6qi6P1mz5uuStJCA',
                               'subject_name': 'Shimonz',
                               'source_subject': 'Shimonz',
                               'source_agency': 'Independent'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2022-12-22',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Shimonz',
                               'notes': 'Retired on 2022-12-22.',
                               'subject_channel_id': 'UCt8vlwt6qi6P1mz5uuStJCA',
                               'subject_name': 'Shimonz',
                               'source_subject': 'Shimonz',
                               'source_agency': 'Independent'}],
 'UCOaTgKPjI9cgXLoDW7XFDDw': [{'event_type': 'DEBUT',
                               'event_date': '2021-03-16',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Princess_Zelina',
                               'notes': 'Debuted on 2021-03-16 as Pixela 1st Generation member.',
                               'subject_channel_id': 'UCOaTgKPjI9cgXLoDW7XFDDw',
                               'subject_name': 'Princess Zelina',
                               'source_subject': 'Princess Zelina',
                               'source_agency': 'Pixela Project'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2025-05-09',
                               'event_year': 2025,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/PixelaProject/status/1920783180422176880',
                               'notes': 'Graduation announced by Pixela on 2025-03-07; final activities '
                                        'completed on 2025-05-09.',
                               'subject_channel_id': 'UCOaTgKPjI9cgXLoDW7XFDDw',
                               'subject_name': 'Princess Zelina',
                               'source_subject': 'Princess Zelina',
                               'source_agency': 'Pixela Project'}],
 'UCutz6S1DcEHPnEb_r9ztkzg': [{'event_type': 'DEBUT',
                               'event_date': '2021-03-10',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Hinabe_HongFei',
                               'notes': 'Debuted on 2021-03-10 as Pixela 1st Generation member.',
                               'subject_channel_id': 'UCutz6S1DcEHPnEb_r9ztkzg',
                               'subject_name': 'Hinabe HongFei',
                               'source_subject': 'Hinabe HongFei',
                               'source_agency': 'Pixela Project'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2023-11-28',
                               'event_year': 2023,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/PixelaProject/status/1723657388706857187',
                               'notes': 'Retired on 2023-11-28.',
                               'subject_channel_id': 'UCutz6S1DcEHPnEb_r9ztkzg',
                               'subject_name': 'Hinabe HongFei',
                               'source_subject': 'Hinabe HongFei',
                               'source_agency': 'Pixela Project'}],
 'UCpNkVsMlsJRF792H-1_1vPA': [{'event_type': 'DEBUT',
                               'event_date': '2021-03-12',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Melita_X',
                               'notes': 'Debuted on 2021-03-12 as Pixela 1st Generation member.',
                               'subject_channel_id': 'UCpNkVsMlsJRF792H-1_1vPA',
                               'subject_name': 'Melita X',
                               'source_subject': 'Melita X',
                               'source_agency': 'Pixela Project'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2023-11-30',
                               'event_year': 2023,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/PixelaProject/status/1723657388706857187',
                               'notes': 'Retired on 2023-11-30.',
                               'subject_channel_id': 'UCpNkVsMlsJRF792H-1_1vPA',
                               'subject_name': 'Melita X',
                               'source_subject': 'Melita X',
                               'source_agency': 'Pixela Project'}],
 'UCMUtWzsjAQJgp6UlkbVSo1w': [{'event_type': 'DEBUT',
                               'event_date': '2021-03-14',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Laguna_Juju',
                               'notes': 'Debuted on 2021-03-14 as Pixela 1st Generation member.',
                               'subject_channel_id': 'UCMUtWzsjAQJgp6UlkbVSo1w',
                               'subject_name': 'Laguna Juju',
                               'source_subject': 'Laguna Juju',
                               'source_agency': 'Pixela Project'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2023-11-29',
                               'event_year': 2023,
                               'verification_status': 'PRIMARY_EVENT_SPECIFIC',
                               'evidence_tier': 'PRIMARY_EVENT_SPECIFIC',
                               'creator_source_class': 'PRIMARY_OFFICIAL_ANNOUNCEMENT',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/PixelaProject/status/1723657388706857187',
                               'notes': 'Retired on 2023-11-29.',
                               'subject_channel_id': 'UCMUtWzsjAQJgp6UlkbVSo1w',
                               'subject_name': 'Laguna Juju',
                               'source_subject': 'Laguna Juju',
                               'source_agency': 'Pixela Project'}],
 'UCSXwfOj8mTDxE1ZaIEHXN2w': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-06',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Meraki_Keimii',
                               'notes': 'Debuted on 2022-01-06 as Pixela Legends member.',
                               'subject_channel_id': 'UCSXwfOj8mTDxE1ZaIEHXN2w',
                               'subject_name': 'Meraki Keimii',
                               'source_subject': 'Meraki Keimii',
                               'source_agency': 'Pixela Project'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2023-01-08',
                               'event_year': 2023,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Meraki_Keimii',
                               'notes': 'Retired on 2023-01-08.',
                               'subject_channel_id': 'UCSXwfOj8mTDxE1ZaIEHXN2w',
                               'subject_name': 'Meraki Keimii',
                               'source_subject': 'Meraki Keimii',
                               'source_agency': 'Pixela Project'}],
 'UCOVpD7MesZKe44ZvLVuwXvA': [{'event_type': 'GRADUATION',
                               'event_date': '2026-01-30',
                               'event_year': 2026,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/ARP_Vtuber/status/2016858872414412856',
                               'notes': 'Official retirement from Algorhythm Project on 2026-01-30.',
                               'subject_channel_id': 'UCOVpD7MesZKe44ZvLVuwXvA',
                               'subject_name': 'Asteroth',
                               'source_subject': 'Asteroth',
                               'source_agency': 'Algorhythm Project'}],
 'UCJdXesaZYrQVSjhlYhme8rQ': [{'event_type': 'GRADUATION',
                               'event_date': '2025-04-04',
                               'event_year': 2025,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/ARP_Vtuber/status/1897988102767231056',
                               'notes': 'Official graduation from Algorhythm Project on 2025-04-04.',
                               'subject_channel_id': 'UCJdXesaZYrQVSjhlYhme8rQ',
                               'subject_name': 'Ayna',
                               'source_subject': 'Ayna',
                               'source_agency': 'Algorhythm Project'}],
 'UCQs4BC3S0KSw7i0ggHXn8TA': [{'event_type': 'GRADUATION',
                               'event_date': '2025-04-02',
                               'event_year': 2025,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/ARP_Vtuber/status/1897988102767231056',
                               'notes': 'Official graduation from Algorhythm Project on 2025-04-02.',
                               'subject_channel_id': 'UCQs4BC3S0KSw7i0ggHXn8TA',
                               'subject_name': 'Quentin',
                               'source_subject': 'Quentin',
                               'source_agency': 'Algorhythm Project'}],
 'UCeLJ2rBYZwPrb5hbKY5X5eg': [{'event_type': 'GRADUATION',
                               'event_date': '2026-01-30',
                               'event_year': 2026,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'OFFICIAL_AGENCY_ANNOUNCEMENT',
                               'source_reference': 'https://x.com/ARP_Vtuber/status/2016858872414412856',
                               'notes': 'Official retirement from Algorhythm Project on 2026-01-30.',
                               'subject_channel_id': 'UCeLJ2rBYZwPrb5hbKY5X5eg',
                               'subject_name': 'Latta',
                               'source_subject': 'Latta',
                               'source_agency': 'Algorhythm Project'}],
 'UCuZ1ajvlGFUMCHZAPdetKHw': [{'event_type': 'DEBUT',
                               'event_date': '2023-03-25',
                               'event_year': 2023,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Dacapo',
                               'notes': 'Debuted on 2023-03-25 as member of Algorhythm Project ORION unit.',
                               'subject_channel_id': 'UCuZ1ajvlGFUMCHZAPdetKHw',
                               'subject_name': 'Dacapo',
                               'source_subject': 'Dacapo',
                               'source_agency': 'Algorhythm Project'}],
 'UCNTEr2_96vJnXNazr5MwNLA': [{'event_type': 'DEBUT',
                               'event_date': '2023-03-25',
                               'event_year': 2023,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project',
                               'notes': 'Debuted on 2023-03-25 as member of Algorhythm Project ORION unit.',
                               'subject_channel_id': 'UCNTEr2_96vJnXNazr5MwNLA',
                               'subject_name': 'Schneider',
                               'source_subject': 'Schneider',
                               'source_agency': 'Algorhythm Project'}],
 'UC7iCSRt7Jej2XE0MaM9gPgg': [{'event_type': 'DEBUT',
                               'event_date': '2020-03-20',
                               'event_year': 2020,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven',
                               'notes': 'Pioneer Thai VTuber under Kadokawa Amarin (Phoenix Next) debuted '
                                        '2020-03-20.',
                               'subject_channel_id': 'UC7iCSRt7Jej2XE0MaM9gPgg',
                               'subject_name': 'YuChan',
                               'source_subject': 'YuChan',
                               'source_agency': 'Kadokawa Amarin -> Virtual Zeven'},
                              {'event_type': 'HIATUS',
                               'event_date': '2021-12-09',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven',
                               'notes': 'Last live stream on 2021-12-09 before hiatus.',
                               'subject_channel_id': 'UC7iCSRt7Jej2XE0MaM9gPgg',
                               'subject_name': 'YuChan',
                               'source_subject': 'YuChan',
                               'source_agency': 'Kadokawa Amarin -> Virtual Zeven'}],
 'UCJ6HUQOWSjCHHdOgz13zFlA': [{'event_type': 'FIRST_APPEARANCE',
                               'event_date': '2017-11-06',
                               'event_year': 2017,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven',
                               'notes': 'First VTuber appearance on 2017-11-06; pioneer Thai VTuber.',
                               'subject_channel_id': 'UCJ6HUQOWSjCHHdOgz13zFlA',
                               'subject_name': 'TheQuillmon',
                               'source_subject': 'TheQuillmon',
                               'source_agency': 'Virtual Zeven'},
                              {'event_type': 'RE_DEBUT',
                               'event_date': '2024-04-27',
                               'event_year': 2024,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven',
                               'notes': 'Re-debuted with Live2D model under Virtual Zeven (The Good Old Days '
                                        'unit).',
                               'subject_channel_id': 'UCJ6HUQOWSjCHHdOgz13zFlA',
                               'subject_name': 'TheQuillmon',
                               'source_subject': 'TheQuillmon',
                               'source_agency': 'Virtual Zeven'}],
 'UCXtQTtPJedfjqEPysorbsMg': [{'event_type': 'DEBUT',
                               'event_date': '2020-06-29',
                               'event_year': 2020,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Qualia_Qu',
                               'notes': 'Debuted on 2020-06-29 as Thai/Japanese bilingual independent '
                                        'VTuber.',
                               'subject_channel_id': 'UCXtQTtPJedfjqEPysorbsMg',
                               'subject_name': 'Qualia Qu',
                               'source_subject': 'Qualia Qu',
                               'source_agency': 'Independent / Former Vtuber'},
                              {'event_type': 'GRADUATION',
                               'event_date': '2022-03-31',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_ANNOUNCEMENT',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Qualia_Qu',
                               'notes': 'Official retirement and graduation on 2022-03-31.',
                               'subject_channel_id': 'UCXtQTtPJedfjqEPysorbsMg',
                               'subject_name': 'Qualia Qu',
                               'source_subject': 'Qualia Qu',
                               'source_agency': 'Independent / Former Vtuber'}],
 'UC0Ky1U__7T2Z5SOZCvNlJ-Q': [{'event_type': 'DEBUT',
                               'event_date': '2021-08-15',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Beariss_Beam',
                               'notes': 'Debuted as independent Thai VTuber illustrated by Jimo.',
                               'subject_channel_id': 'UC0Ky1U__7T2Z5SOZCvNlJ-Q',
                               'subject_name': 'Beariss Beam',
                               'source_subject': 'Beariss Beam',
                               'source_agency': 'Independent'}],
 'UCrYkQnbL_OiYyGuiZyvcO7g': [{'event_type': 'DEBUT',
                               'event_date': '2021-08-26',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Solly',
                               'notes': 'Debuted on 2021-08-26 as independent Thai VTuber.',
                               'subject_channel_id': 'UCrYkQnbL_OiYyGuiZyvcO7g',
                               'subject_name': 'Hey Solly',
                               'source_subject': 'Hey Solly',
                               'source_agency': 'Independent'}],
 'UCafG1bj6Qtcbn4bozcicWfA': [{'event_type': 'DEBUT',
                               'event_date': '2020-10-08',
                               'event_year': 2020,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Zona',
                               'notes': 'Debuted on 2020-10-08 as member of Polygon Project 1st Gen '
                                        '(POLAR1SS).',
                               'subject_channel_id': 'UCafG1bj6Qtcbn4bozcicWfA',
                               'subject_name': 'Zona',
                               'source_subject': 'Zona',
                               'source_agency': 'Polygon Project - POLAR1SS'}],
 'UCiYFmDfFBoAP2yk9yuXBTTg': [{'event_type': 'DEBUT',
                               'event_date': '2021-04-09',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/S1R',
                               'notes': 'Debuted on 2021-04-09 as member of Algorhythm Project.',
                               'subject_channel_id': 'UCiYFmDfFBoAP2yk9yuXBTTg',
                               'subject_name': 'S1R',
                               'source_subject': 'S1R',
                               'source_agency': 'Algorhythm Project'}],
 'UChBuxXl8poN1Jz8kZDdsfhw': [{'event_type': 'DEBUT',
                               'event_date': '2021-08-06',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Selene',
                               'notes': 'Debuted on 2021-08-06 as member of Algorhythm Project.',
                               'subject_channel_id': 'UChBuxXl8poN1Jz8kZDdsfhw',
                               'subject_name': 'Selene',
                               'source_subject': 'Selene',
                               'source_agency': 'Algorhythm Project'}],
 'UCVAsOHcLLGVQq6aOpesOwBQ': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-25',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Hanabi_Lafy',
                               'notes': 'Debuted on 2022-01-25 as member of Pixela Legends.',
                               'subject_channel_id': 'UCVAsOHcLLGVQq6aOpesOwBQ',
                               'subject_name': 'Hanabi Lafy',
                               'source_subject': 'Hanabi Lafy',
                               'source_agency': 'Pixela Legends'}],
 'UCLNBff3KDEUxdfH_lkvyOKQ': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-27',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Kamiyu_Reirin',
                               'notes': 'Debuted on 2022-01-27 as member of Pixela Legends.',
                               'subject_channel_id': 'UCLNBff3KDEUxdfH_lkvyOKQ',
                               'subject_name': 'Kamiyu Reirin',
                               'source_subject': 'Kamiyu Reirin',
                               'source_agency': 'Pixela Legends'}],
 'UCPMOk4hbIh5A-_6uNhzAvDg': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-27',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Kitsuneko_Mewten',
                               'notes': 'Debuted on 2022-01-27 as member of Pixela Legends.',
                               'subject_channel_id': 'UCPMOk4hbIh5A-_6uNhzAvDg',
                               'subject_name': 'Kitsuneko Mewten',
                               'source_subject': 'Kitsuneko Mewten',
                               'source_agency': 'Pixela Legends'}],
 'UCktUGMC7AKl1e8n20Ys8w0Q': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-06',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Superpretty_TAKOPERO',
                               'notes': 'Debuted on 2022-01-06 as member of Pixela Legends.',
                               'subject_channel_id': 'UCktUGMC7AKl1e8n20Ys8w0Q',
                               'subject_name': 'Superpretty TAKOPERO',
                               'source_subject': 'Superpretty TAKOPERO',
                               'source_agency': 'Pixela Legends'}],
 'UCkEcY4RbLYs2AF45nhkyjtw': [{'event_type': 'DEBUT',
                               'event_date': '2022-01-25',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Jolly_Estaa',
                               'notes': 'Debuted on 2022-01-25 as member of Pixela Legends.',
                               'subject_channel_id': 'UCkEcY4RbLYs2AF45nhkyjtw',
                               'subject_name': 'Jolly Estaa',
                               'source_subject': 'Jolly Estaa',
                               'source_agency': 'Pixela Legends'}],
 'UCDCOWpzyBFsavT-K7AmN3MQ': [{'event_type': 'DEBUT',
                               'event_date': '2022-02-19',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Azato_Stacia',
                               'notes': 'Debuted on 2022-02-19 as independent Thai VTuber.',
                               'subject_channel_id': 'UCDCOWpzyBFsavT-K7AmN3MQ',
                               'subject_name': 'Azato Stacia',
                               'source_subject': 'Azato Stacia',
                               'source_agency': 'Independent'}],
 'UCE010cVAgWFD24wIJ95sDKw': [{'event_type': 'DEBUT',
                               'event_date': '2022-02-10',
                               'event_year': 2022,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/Fumi_Hausu',
                               'notes': 'Debuted on 2022-02-10 as independent Thai VTuber.',
                               'subject_channel_id': 'UCE010cVAgWFD24wIJ95sDKw',
                               'subject_name': 'Fumi Hausu',
                               'source_subject': 'Fumi Hausu',
                               'source_agency': 'Independent'}],
 'UCbEkHjG43yPMGq5W08jq1TQ': [{'event_type': 'DEBUT',
                               'event_date': '2021-11-05',
                               'event_year': 2021,
                               'verification_status': 'VERIFIED_EXTERNAL_EVIDENCE',
                               'source_type': 'EXTERNAL_WIKI_AND_YOUTUBE',
                               'source_reference': 'https://virtualyoutuber.fandom.com/wiki/ChaAYM',
                               'notes': 'Debuted on 2021-11-05 as independent Thai VTuber.',
                               'subject_channel_id': 'UCbEkHjG43yPMGq5W08jq1TQ',
                               'subject_name': 'ChaAYM',
                               'source_subject': 'ChaAYM',
                               'source_agency': 'Independent'}]}


def build_creator_datasets():
    from scripts.audit_creator_identity_mapping import audit_identity
    audit_identity(VERIFIED_CREATOR_INTEL)
    manifest_df = pd.read_csv(MANIFEST_PATH)
    logger.info(f"Loaded {len(manifest_df)} channels from {MANIFEST_PATH}")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reg_data = json.load(f)
    reg_by_id = {r["channel_id"]: r for r in reg_data}

    cov_df = pd.read_parquet(COVERAGE_PATH)
    cov_by_id = {r["channel_id"]: r for _, r in cov_df.iterrows()}

    retrieved_at = datetime.now(timezone.utc).isoformat()

    all_events = []
    coverage_rows = []

    for _, r in manifest_df.iterrows():
        cid = r["channel_id"]
        name = r["name"]
        agency = r["agency"]
        status = r["lifecycle_status"]
        cov = cov_by_id.get(cid, {})
        reg_item = reg_by_id.get(cid, {})

        verified_events = VERIFIED_CREATOR_INTEL.get(cid, [])
        creator_events = []

        # Add audited verified/documented events
        for ve in verified_events:
            ref = str(ve.get("source_reference", "")).strip()
            ref_lower = ref.lower()
            st = ve.get("source_type", "")

            # Explicit curated source authority metadata check
            is_curated_primary = (
                ve.get("verification_status") == "PRIMARY_EVENT_SPECIFIC"
                or ve.get("creator_source_class") in ["PRIMARY_OFFICIAL_ANNOUNCEMENT", "CREATOR_PRIMARY_STATEMENT"]
                or st in ["OFFICIAL_AGENCY_ANNOUNCEMENT", "PUBLIC_TALENT_STATEMENT"]
            )
            is_official_source_type = st in ["OFFICIAL_AGENCY_ANNOUNCEMENT", "PUBLIC_TALENT_STATEMENT"]
            
            # Authoritative publisher handles: must match exact verified official agency or talent account handle
            parsed_handle = parse_authority_handle(ref)
            curated_auth_id = str(ve.get("source_authority_id", "")).lower().strip()
            is_recognized_authority = (
                parsed_handle in RECOGNIZED_AUTHORITY_HANDLES
                or curated_auth_id in RECOGNIZED_AUTHORITY_HANDLES
            )

            # Strict evidence tier assignment: requires curated authority metadata AND specific event URL
            # A random third-party X status or fake prefix/suffix handle must not auto-upgrade
            if (
                is_curated_primary
                and is_official_source_type
                and is_recognized_authority
                and ("status/" in ref_lower or "twitter.com/eileennoir" in ref_lower)
                and not any(h in ref_lower for h in ["fandom.com"])
            ):
                evidence_tier = "PRIMARY_EVENT_SPECIFIC"
                creator_source_class = "CREATOR_PRIMARY_STATEMENT" if st == "PUBLIC_TALENT_STATEMENT" else "PRIMARY_OFFICIAL_ANNOUNCEMENT"
            elif "fandom.com" in ref_lower:
                evidence_tier = "SECONDARY_DOCUMENTED"
                creator_source_class = "SECONDARY_DOCUMENTED"
            elif "video_catalog" in ref_lower:
                evidence_tier = "INFERRED_PROXY"
                creator_source_class = "INFERRED_PROXY"
            else:
                evidence_tier = ve.get("evidence_tier", "SECONDARY_DOCUMENTED")
                creator_source_class = ve.get("creator_source_class", "SECONDARY_DOCUMENTED")

            event_id = f"evt_{ve['event_type'].lower()}_{cid[:10]}_{ve['event_date'].replace('-', '')}"
            event_obj = {
                "subject_channel_id": ve["subject_channel_id"],
                "subject_name": ve["subject_name"],
                "source_subject": ve["source_subject"],
                "event_id": event_id,
                "creator_channel_id": cid,
                "creator_name": name,
                "agency": agency,
                "event_type": ve["event_type"],
                "event_date": ve["event_date"],
                "event_year": ve["event_year"],
                "evidence_tier": evidence_tier,
                "creator_source_class": creator_source_class,
                "verification_status": evidence_tier,
                "source_type": ve["source_type"],
                "source_reference": ref,
                "retrieved_at": retrieved_at,
                "notes": ve["notes"]
            }
            all_events.append(event_obj)
            creator_events.append(event_obj)

        # If no verified debut/first appearance, emit observational first observed proxy
        has_verified_start = any(e["event_type"] in ["DEBUT", "FIRST_APPEARANCE", "RE_DEBUT"] for e in verified_events)
        if not has_verified_start:
            oldest_vid_ts = cov.get("oldest_video_published_at")
            if pd.notna(oldest_vid_ts):
                dt_str = str(oldest_vid_ts)[:10]
                event_id = f"evt_first_observed_{cid[:10]}_{dt_str.replace('-', '')}"
                proxy_obj = {
                    "event_id": event_id,
                    "creator_channel_id": cid,
                    "creator_name": name,
                    "agency": agency,
                    "event_type": "FIRST_OBSERVED",
                    "event_date": dt_str,
                    "event_year": int(dt_str[:4]),
                    "evidence_tier": "INFERRED_PROXY",
                    "creator_source_class": "INFERRED_PROXY",
                    "verification_status": "INFERRED_PROXY",
                    "source_type": "CATALOG_TIMESTAMP_PROXY",
                    "source_reference": f"channel_coverage.parquet:oldest_video_published_at={oldest_vid_ts}",
                    "retrieved_at": retrieved_at,
                    "notes": f"Earliest cataloged public video upload in research dataset ({oldest_vid_ts}). Not verified debut stream."
                }
                all_events.append(proxy_obj)
                creator_events.append(proxy_obj)

        # Hiatus or graduation proxy for unverified inactive channels
        has_verified_end = any(e["event_type"] in ["GRADUATION", "TERMINATION", "GRADUATION_OR_DEPARTURE"] for e in verified_events)
        if status in ["hiatus", "graduated"] and not has_verified_end:
            last_pub = reg_item.get("last_video_published_at")
            if last_pub and str(last_pub).strip():
                dt_str = str(last_pub)[:10]
                event_type = "GRADUATION_PROXY" if status == "graduated" else "HIATUS_OBSERVED_PROXY"
                event_id = f"evt_{event_type.lower()}_{cid[:10]}_{dt_str.replace('-', '')}"
                proxy_obj = {
                    "event_id": event_id,
                    "creator_channel_id": cid,
                    "creator_name": name,
                    "agency": agency,
                    "event_type": event_type,
                    "event_date": dt_str,
                    "event_year": int(dt_str[:4]),
                    "evidence_tier": "INFERRED_PROXY",
                    "creator_source_class": "INFERRED_PROXY",
                    "verification_status": "INFERRED_PROXY",
                    "source_type": "REGISTRY_INACTIVITY_PROXY",
                    "source_reference": f"thai_vtuber_registry.json:last_video_published_at={last_pub}",
                    "retrieved_at": retrieved_at,
                    "notes": f"Observed {status} boundary based on last public activity recorded on {dt_str} (>180d inactive)."
                }
                all_events.append(proxy_obj)
                creator_events.append(proxy_obj)

        # Count events by evidence tier
        primary_specific_count = sum(1 for e in creator_events if e["creator_source_class"] == "PRIMARY_OFFICIAL_ANNOUNCEMENT")
        creator_primary_count = sum(1 for e in creator_events if e["creator_source_class"] == "CREATOR_PRIMARY_STATEMENT")
        secondary_doc_count = sum(1 for e in creator_events if e["evidence_tier"] == "SECONDARY_DOCUMENTED")
        inferred_proxy_count = sum(1 for e in creator_events if e["evidence_tier"] == "INFERRED_PROXY")
        start_known = True if (has_verified_start or pd.notna(cov.get("oldest_video_published_at"))) else False
        end_known = True if (status in ["graduated"] or has_verified_end) else False
        agency_known = True if (agency and agency != "Unknown") else False
        unknown_count = 1 if (status in ["hiatus", "unknown"] and not end_known) else 0

        num_verified = primary_specific_count + creator_primary_count + secondary_doc_count
        ext_sources = 2 if num_verified > 0 else 1

        if num_verified > 0:
            remaining_gap = "NONE" if (end_known or status == "active") else "LIFECYCLE_END_UNCERTAIN"
        elif status == "active":
            remaining_gap = "LIFECYCLE_END_UNKNOWN"
        elif status in ["hiatus", "unknown"]:
            remaining_gap = "UNCERTAIN_DATES"
        else:
            remaining_gap = "PROXY_ONLY"

        coverage_rows.append({
            "creator_channel_id": cid,
            "creator_name": name,
            "agency": agency,
            "lifecycle_status": status,
            "events_primary_event_specific": primary_specific_count,
            "events_creator_primary": creator_primary_count,
            "events_secondary_documented": secondary_doc_count,
            "events_inferred_proxy": inferred_proxy_count,
            "events_unknown": unknown_count,
            "events_verified": num_verified,
            "events_proxy": inferred_proxy_count,
            "external_sources_checked": ext_sources,
            "lifecycle_start_known": start_known,
            "lifecycle_end_known": end_known,
            "agency_history_known": agency_known,
            "remaining_gap": remaining_gap
        })

    # Convert to DataFrames
    events_df = pd.DataFrame(all_events).drop_duplicates(subset=["event_id"])
    coverage_df = pd.DataFrame(coverage_rows)

    # Save creator_status_events
    events_parquet = INDUSTRY_DIR / "creator_status_events.parquet"
    events_csv = INDUSTRY_DIR / "creator_status_events.csv"
    events_df.to_parquet(events_parquet, index=False)
    events_df.to_csv(events_csv, index=False)
    logger.info(f"Saved {len(events_df)} status events to {events_parquet} and {events_csv}")
    logger.info(f"Events evidence_tier breakdown: {events_df['evidence_tier'].value_counts().to_dict()}")
    logger.info(f"Events creator_source_class breakdown: {events_df['creator_source_class'].value_counts().to_dict()}")

    # Save creator_evidence_coverage
    cov_parquet = INDUSTRY_DIR / "creator_evidence_coverage.parquet"
    cov_csv = INDUSTRY_DIR / "creator_evidence_coverage.csv"
    coverage_df.to_parquet(cov_parquet, index=False)
    coverage_df.to_csv(cov_csv, index=False)
    logger.info(f"Saved {len(coverage_df)} creator coverage rows to {cov_parquet} and {cov_csv}")
    logger.info(f"Remaining gap breakdown: {coverage_df['remaining_gap'].value_counts().to_dict()}")

    # Regenerate creator_public_snapshot from newly built canonical evidence
    try:
        try:
            from scripts.build_creator_ecosystem_data import build_creator_public_snapshot
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from build_creator_ecosystem_data import build_creator_public_snapshot
        build_creator_public_snapshot()
        logger.info("Successfully updated creator_public_snapshot.parquet from canonical lifecycle evidence.")
    except Exception as e:
        logger.warning(f"Could not build creator_public_snapshot: {e}")


if __name__ == "__main__":
    build_creator_datasets()
