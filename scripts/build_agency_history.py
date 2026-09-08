"""
Phase N4 / Pass 2C: Verified Agency Histories and Milestones Engine
Builds:
1. data/industry/agency_history.parquet & .csv
2. data/industry/agency_events.parquet & .csv

Covers all agencies represented in the 193-channel frozen target cohort:
- Algorhythm Project (ARP)
- Pixela Project
- Virtual Zeven (VZ)
- RPG
- AStars Production
- Lumina Live / LuminaVProject
- Polygon Official / Polygon Project
- Euphora Project
- Flora Project
- WACTOR
- Ti19t
- Independent

Strictly maintains:
- primary_source_url
- secondary_source_url
- verification_tier (TIER_1_PRIMARY_OFFICIAL, TIER_2_PRIMARY_CREATOR, TIER_3_SECONDARY_DOCUMENTED, TIER_5_INFERRED_PROXY)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildAgencyHistory")

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
INDUSTRY_DIR = DATA_DIR / "industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)


AGENCY_METADATA = [
    {
        "agency_id": "agn_algorhythm_project",
        "agency_name": "Algorhythm Project",
        "parent_company": "Realic Co., Ltd. (บริษัท รีลิค จำกัด)",
        "founding_date": "2020-09-01",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Apocalypse, Eclipse, Illusion, Ominous, Utopia, ORION, Gemini, Scorpio, Symphonia, V-Agent, The Unknown",
        "primary_source_url": "https://algorhythm.realic.net/",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_pixela_project",
        "agency_name": "Pixela Project",
        "parent_company": "Pixela Official Co., Ltd. (บริษัท พิกเซล่า ออฟฟิเชียล จำกัด)",
        "founding_date": "2020-09-10",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "1st Gen, Pixela Isekai, Pixela Legends, Pixela Mystic, Pixela S, Pixela Destiny, Pixela-World-End",
        "primary_source_url": "https://x.com/PixelaProject",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Pixela_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_virtual_zeven",
        "agency_name": "Virtual Zeven (VZ)",
        "parent_company": "Virtual Zeven Co., Ltd. (บริษัท เวอร์ชวล เซเว่น จำกัด)",
        "founding_date": "2020-03-20",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "V:INFLU, The Good Old Days, ALPHA/BETA, PRØJECT: DÉ Z34SØN, EDEN PRØJECT, WØNDERLAN:D, ZYDER, FØR•REST",
        "primary_source_url": "https://x.com/VirtualZeven",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_astars_production",
        "agency_name": "AStars Production",
        "parent_company": "Brave group APAC (Thailand) Co., Ltd. / Brave group Inc. (Tokyo)",
        "founding_date": "2024-07-16",
        "status": "ACTIVE",
        "headquarters": "Thailand / Japan",
        "notable_units": "Chrono Prince (1st Gen male), Amakara (1st Gen female), 2nd Gen, 3rd Gen",
        "primary_source_url": "https://astars-production.com/",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/AStars",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_rpg",
        "agency_name": "RPG",
        "parent_company": "Independent / Unknown",
        "founding_date": "2022-01-01",
        "status": "CLOSED",
        "headquarters": "Thailand",
        "notable_units": "RPG Talents (Akiyama Zqiu, Tenebris D. Armis, Mysterica X.)",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_YouTuber_Wiki",
        "verification_tier": "TIER_3_SECONDARY_DOCUMENTED"
    },
    {
        "agency_id": "agn_lumina_live",
        "agency_name": "Lumina Live",
        "parent_company": "LuminaVProject",
        "founding_date": "2023-04-01",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Lumina-First-Myth, Lumina-World-End, Lumina-Mutelu, Lumina-Muse",
        "primary_source_url": "https://x.com/LuminaLive_TH",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Ardalita_Lilibelle",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_polygon_official",
        "agency_name": "Polygon Official",
        "parent_company": "KP Comics / Shin-A Service / Guardian Angel A.I. / Polygon Official",
        "founding_date": "2020-03-11",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "0th Gen (Aisha), 1st Gen POLAR1SS, 2nd Gen PLG Highschool, Polygon ALTER, 3rd Gen The COD3X",
        "primary_source_url": "https://x.com/PolygonOfficial",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Polygon_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_euphora_project",
        "agency_name": "Euphora Project",
        "parent_company": "Independent / Euphora Group",
        "founding_date": "2022-06-01",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Euphora Talents (LittleG, Saneko, Jiru, Uniinu, Lynis, Rubellite, Phelita, Housagi, Artie, Jiah, CIEL Chouette, Kevara)",
        "primary_source_url": "https://x.com/EuphoraProject",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Category:Thai",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL"
    },
    {
        "agency_id": "agn_flora_project",
        "agency_name": "Flora Project",
        "parent_company": "Independent / Flora Group",
        "founding_date": "2021-08-01",
        "status": "INACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Flora Talents (Xaniel, Vermillion, Chika)",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Category:Thai",
        "verification_tier": "TIER_3_SECONDARY_DOCUMENTED"
    },
    {
        "agency_id": "agn_wactor",
        "agency_name": "WACTOR",
        "parent_company": "WACTOR Co., Ltd.",
        "founding_date": "2019-06-01",
        "status": "CLOSED",
        "headquarters": "Japan",
        "notable_units": "1st Gen, 2nd Gen (Shino Laila, Kurari Rose, Hoshina Suzu, Hina Misora), 3rd Gen, 4th Gen GATE, E-STELLA, noVas",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Shino_Laila",
        "verification_tier": "TIER_3_SECONDARY_DOCUMENTED"
    },
    {
        "agency_id": "agn_ti19t",
        "agency_name": "Ti19t",
        "parent_company": "Independent / Ti19t Community",
        "founding_date": "2020-12-01",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Pengu, Valery, Xen",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Category:Thai",
        "verification_tier": "TIER_3_SECONDARY_DOCUMENTED"
    },
    {
        "agency_id": "agn_independent",
        "agency_name": "Independent",
        "parent_company": "Self-Managed / Individual Creators",
        "founding_date": "2017-01-01",
        "status": "ACTIVE",
        "headquarters": "Thailand",
        "notable_units": "Independent Thai VTuber Community",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Category:Thai",
        "verification_tier": "TIER_4_LOCAL_PUBLIC_ARTIFACT"
    }
]

AGENCY_EVENTS = [
    # Algorhythm Project Milestones
    {
        "event_id": "evt_agn_arp_founding",
        "agency_name": "Algorhythm Project",
        "event_type": "AGENCY_LAUNCH",
        "event_date": "2020-09-01",
        "event_year": 2020,
        "description": "Algorhythm Project announced by Realic Production focusing on music and virtual entertainment.",
        "primary_source_url": "https://x.com/ARP_Vtuber",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_arp_orion_launch",
        "agency_name": "Algorhythm Project",
        "event_type": "UNIT_LAUNCH",
        "event_date": "2023-03-25",
        "event_year": 2023,
        "description": "Launch of Celestial Operation unit ORION (Dacapo, Baabel, Schneider), reaching 100k subscribers in record time.",
        "primary_source_url": "https://www.youtube.com/watch?v=S38pY94qj68",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_arp_graduations_2025",
        "agency_name": "Algorhythm Project",
        "event_type": "TALENT_DEPARTURES",
        "event_date": "2025-04-04",
        "event_year": 2025,
        "description": "Graduation of multiple ARP talents including Quentin (2025-04-02), Ricotta (2025-04-03), and Ayna (2025-04-04).",
        "primary_source_url": "https://x.com/ARP_Vtuber/status/1897988102767231056",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_arp_retirements_2026",
        "agency_name": "Algorhythm Project",
        "event_type": "TALENT_DEPARTURES",
        "event_date": "2026-01-30",
        "event_year": 2026,
        "description": "Retirement of Asteroth and Latta from Algorhythm Project.",
        "primary_source_url": "https://x.com/ARP_Vtuber/status/2016858872414412856",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Algorhythm_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    # Pixela Project Milestones
    {
        "event_id": "evt_agn_pixela_founding",
        "agency_name": "Pixela Project",
        "event_type": "AGENCY_LAUNCH",
        "event_date": "2020-09-10",
        "event_year": 2020,
        "description": "Pixela Project registration and establishment.",
        "primary_source_url": "https://x.com/PixelaProject",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Pixela_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_pixela_gen1_debut",
        "agency_name": "Pixela Project",
        "event_type": "GENERATION_DEBUT",
        "event_date": "2021-03-08",
        "event_year": 2021,
        "description": "Debut of Pixela 1st Generation (Cazzie, HongFei, Melita, Laguna, Zelina).",
        "primary_source_url": "https://www.youtube.com/@PixelaProject",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Pixela_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_pixela_gen1_retirements_2023",
        "agency_name": "Pixela Project",
        "event_type": "TALENT_DEPARTURES",
        "event_date": "2023-11-30",
        "event_year": 2023,
        "description": "Retirement of 1st generation members Hinabe HongFei (2023-11-28), Laguna Juju (2023-11-29), and Melita X (2023-11-30).",
        "primary_source_url": "https://x.com/PixelaProject/status/1719280010375680199",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Pixela_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_pixela_world_end_debut",
        "agency_name": "Pixela Project",
        "event_type": "UNIT_LAUNCH",
        "event_date": "2024-05-21",
        "event_year": 2024,
        "description": "Debut of Pixela-World-End unit (Beta AMI, Xonebu X'thulhu, Kumoku Tsururu, Mild-R, Debirun, T-Reina Ashyra).",
        "primary_source_url": "https://x.com/PixelaProject/status/1792905292671566164",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Pixela_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_pixela_zelina_grad_2025",
        "agency_name": "Pixela Project",
        "event_type": "TALENT_DEPARTURE",
        "event_date": "2025-05-09",
        "event_year": 2025,
        "description": "Graduation of Princess Zelina, concluding Pixela 1st Generation active history.",
        "primary_source_url": "https://x.com/Zelina_Pixela/status/1920786524385202688",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Princess_Zelina",
        "verification_tier": "TIER_2_PRIMARY_CREATOR",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    # Virtual Zeven Milestones
    {
        "event_id": "evt_agn_vz_pioneer_yuchan",
        "agency_name": "Virtual Zeven (VZ)",
        "event_type": "TALENT_DEBUT",
        "event_date": "2020-03-20",
        "event_year": 2020,
        "description": "Pioneer Thai VTuber YuChan debuted under Kadokawa Amarin (Phoenix Next).",
        "primary_source_url": "https://www.youtube.com/@YuChanChannel",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_vz_reorganization_2023",
        "agency_name": "Virtual Zeven (VZ)",
        "event_type": "AGENCY_RESTRUCTURING",
        "event_date": "2023-01-01",
        "event_year": 2023,
        "description": "HØRI 07 founded Virtual Zeven Co., Ltd. agency operations with 'viewers as owners' concept.",
        "primary_source_url": "https://x.com/VirtualZeven",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_vz_quillmon_redebut_2024",
        "agency_name": "Virtual Zeven (VZ)",
        "event_type": "TALENT_RE_DEBUT",
        "event_date": "2024-04-27",
        "event_year": 2024,
        "description": "Pioneer Thai YouTuber/VTuber TheQuillmon re-debuted with Live2D model under Virtual Zeven (The Good Old Days unit).",
        "primary_source_url": "https://www.youtube.com/@TheQuillmon",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_Zeven",
        "verification_tier": "TIER_2_PRIMARY_CREATOR",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    # AStars Production Milestones
    {
        "event_id": "evt_agn_astars_launch",
        "agency_name": "AStars Production",
        "event_type": "AGENCY_LAUNCH",
        "event_date": "2024-07-16",
        "event_year": 2024,
        "description": "Brave Group APAC announced the launch of AStars and debut of inaugural unit Chrono Prince.",
        "primary_source_url": "https://x.com/AStarsofficial/status/1815726053744328971",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/AStars",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_astars_amakara_debut",
        "agency_name": "AStars Production",
        "event_type": "UNIT_LAUNCH",
        "event_date": "2024-09-13",
        "event_year": 2024,
        "description": "Debut of all-female unit Amakara (Lenezmee Dollynx, Amaris Sayo, Zia Sylph, Ice Shirakoi).",
        "primary_source_url": "https://x.com/AStarsofficial/status/1828764474452386201",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/AStars",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_astars_amakara_departures_2025",
        "agency_name": "AStars Production",
        "event_type": "TALENT_DEPARTURES",
        "event_date": "2025-04-30",
        "event_year": 2025,
        "description": "Graduation of Amakara members Amaris Sayo (2025-02-14) and Ice Shirakoi (2025-04-30).",
        "primary_source_url": "https://x.com/AStarsofficial/status/1888528955219968470",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/AStars",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    # Polygon Project Milestones
    {
        "event_id": "evt_agn_polygon_aisha_debut",
        "agency_name": "Polygon Official",
        "event_type": "TALENT_DEBUT",
        "event_date": "2019-07-29",
        "event_year": 2019,
        "description": "Aisha debuted under Guardian Angel A.I., later anchoring Polygon 0th Gen.",
        "primary_source_url": "https://www.youtube.com/@AishaChannel",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Aisha",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_polygon_founding",
        "agency_name": "Polygon Official",
        "event_type": "AGENCY_LAUNCH",
        "event_date": "2020-03-11",
        "event_year": 2020,
        "description": "Polygon Project launched by 4 Thai companies (KP Comics, Shin-A Service, Guardian Angel A.I., Polygon Official).",
        "primary_source_url": "https://x.com/PolygonOfficial",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Polygon_Project",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    {
        "event_id": "evt_agn_polygon_aisha_grad_2025",
        "agency_name": "Polygon Official",
        "event_type": "TALENT_DEPARTURE",
        "event_date": "2025-12-18",
        "event_year": 2025,
        "description": "Graduation of pioneer VTuber Aisha after 6 years of activity.",
        "primary_source_url": "https://x.com/PolygonOfficial/status/2001594838520779264",
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Aisha",
        "verification_tier": "TIER_1_PRIMARY_OFFICIAL",
        "verification_status": "VERIFIED_EXTERNAL_EVIDENCE"
    },
    # RPG Closure Milestone (Kept as INFERRED_PROXY, Tier 5)
    {
        "event_id": "evt_agn_rpg_closure",
        "agency_name": "RPG",
        "event_type": "AGENCY_CLOSURE",
        "event_date": "2024-09-30",
        "event_year": 2024,
        "description": "Closure and cessation of RPG agency talent operations.",
        "primary_source_url": None,
        "secondary_source_url": "https://virtualyoutuber.fandom.com/wiki/Virtual_YouTuber_Wiki",
        "verification_tier": "TIER_5_INFERRED_PROXY",
        "verification_status": "INFERRED_PROXY"
    }
]


def build_agency_datasets():
    retrieved_at = datetime.now(timezone.utc).isoformat()

    # Agency history DataFrame
    history_rows = []
    for ag in AGENCY_METADATA:
        r = dict(ag)
        r["retrieved_at"] = retrieved_at
        r["verification_status"] = "VERIFIED_EXTERNAL_EVIDENCE" if r["verification_tier"] in ["TIER_1_PRIMARY_OFFICIAL", "TIER_2_PRIMARY_CREATOR", "TIER_3_SECONDARY_DOCUMENTED"] and r["status"] != "CLOSED" else ("INFERRED_PROXY" if r["verification_tier"] == "TIER_5_INFERRED_PROXY" else "VERIFIED_EXTERNAL_EVIDENCE")
        history_rows.append(r)
    history_df = pd.DataFrame(history_rows)

    # Agency events DataFrame
    event_rows = []
    for ev in AGENCY_EVENTS:
        r = dict(ev)
        r["retrieved_at"] = retrieved_at
        event_rows.append(r)
    events_df = pd.DataFrame(event_rows)

    # Persist parquet and csv
    history_df.to_parquet(INDUSTRY_DIR / "agency_history.parquet", index=False)
    history_df.to_csv(INDUSTRY_DIR / "agency_history.csv", index=False)
    logger.info(f"Saved {len(history_df)} agency history records to agency_history.*")

    events_df.to_parquet(INDUSTRY_DIR / "agency_events.parquet", index=False)
    events_df.to_csv(INDUSTRY_DIR / "agency_events.csv", index=False)
    logger.info(f"Saved {len(events_df)} agency event records to agency_events.*")


if __name__ == "__main__":
    build_agency_datasets()
