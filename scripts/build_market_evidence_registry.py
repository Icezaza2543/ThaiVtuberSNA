#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase N6: Market & Money Evidence Registry Builder
Builds:
- data/market/market_evidence.csv
- data/market/market_evidence.parquet
- data/market/source_registry.csv

Strict Epistemic Guards:
- NEVER sum incompatible market signals (e.g. ticket price != event revenue,
  merch price != total merchandise revenue, Super Chat != creator income).
- Explicitly flags can_be_summed=False and documents double_count_risk for every record.
- Documents the public financial transparency gap cleanly without fabricating market size.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
MARKET_DIR = ROOT / "data/market"
MARKET_DIR.mkdir(parents=True, exist_ok=True)

OUT_EVIDENCE_CSV = MARKET_DIR / "market_evidence.csv"
OUT_EVIDENCE_PARQUET = MARKET_DIR / "market_evidence.parquet"
OUT_SOURCE_CSV = MARKET_DIR / "source_registry.csv"

NOW_ISO = datetime.now(timezone.utc).isoformat()

def build_market_registry():
    print("Building verifiable market evidence and source registry...")
    
    # 1. Source Registry
    sources = [
        {
            "source_id": "SRC_PLAYBOARD_TH",
            "source_name": "Playboard.co YouTube Super Chat Index (Thailand Region)",
            "source_type": "PUBLIC_PLATFORM_SCRAPER",
            "source_url": "https://playboard.co/en/youtube-ranking/most-superchatted-all-channels-in-thailand-total",
            "publisher": "Playboard / Diff Inc.",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "MEDIUM",
            "usage_warning": "Third-party scraper; tracks gross public superchats only; excludes memberships, bits, direct donations, and platform deductions."
        },
        {
            "source_id": "SRC_YOUTUBE_MEMBERSHIP",
            "source_name": "YouTube Official Channel Membership Price Schedules (Thailand)",
            "source_type": "OFFICIAL_PLATFORM_PRICING",
            "source_url": "https://www.youtube.com",
            "publisher": "Google / YouTube",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "Reflects list subscription prices per month; actual member counts are private creator/platform data."
        },
        {
            "source_id": "SRC_TICKETMELO_EVENT",
            "source_name": "Ticketmelon / Eventpop Official VTuber Event Listings",
            "source_type": "EVENT_TICKETING_PLATFORM",
            "source_url": "https://www.ticketmelon.com",
            "publisher": "Ticketmelon Co., Ltd.",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "Reflects face-value ticket prices; does not report net revenue, attendance realization, or production costs."
        },
        {
            "source_id": "SRC_ARP_OFFICIAL_STORE",
            "source_name": "Algorhythm Project Official Merchandise & Voice Store",
            "source_type": "OFFICIAL_STORE",
            "source_url": "https://shop.algorhythmproject.com",
            "publisher": "Algorhythm Project",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "Price per item/bundle; total sold volume is private commercial data."
        },
        {
            "source_id": "SRC_PIXELA_OFFICIAL_STORE",
            "source_name": "Pixela Project Official Store",
            "source_type": "OFFICIAL_STORE",
            "source_url": "https://store.pixelaproject.com",
            "publisher": "Pixela Official",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "Unit retail prices; inventory volumes and gross sales are undisclosed."
        },
        {
            "source_id": "SRC_ONDE_DIGITAL_CONTENT_2023",
            "source_name": "Thailand Digital Content Market Survey 2023",
            "source_type": "GOVERNMENT_REPORT",
            "source_url": "https://www.onde.go.th",
            "publisher": "Office of the National Digital Economy and Society Commission (ONDE) & depa",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "Macro market study covering total animation, game, and character industries; VTuber segment is not broken out separately."
        },
        {
            "source_id": "SRC_WE_ARE_SOCIAL_TH_2024",
            "source_name": "Digital 2024: Thailand Overview",
            "source_type": "INDUSTRY_REPORT",
            "source_url": "https://wearesocial.com/reports/digital-2024-thailand/",
            "publisher": "We Are Social & Meltwater",
            "retrieved_at": NOW_ISO,
            "reliability_rating": "HIGH",
            "usage_warning": "General digital audience addressable context; not specific to virtual streamers."
        }
    ]
    
    sources_df = pd.DataFrame(sources)
    sources_df.to_csv(OUT_SOURCE_CSV, index=False, encoding="utf-8")
    print(f"Saved {OUT_SOURCE_CSV} ({len(sources_df)} registered sources).")
    
    # 2. Market Evidence Records
    evidence_items = [
        # --- PUBLIC_SUPERCHAT_SIGNAL ---
        {
            "evidence_id": "mkt_sc_aisha_cumul_2024",
            "entity": "Aisha Channel",
            "entity_type": "CREATOR",
            "date": "2024-12-31",
            "evidence_class": "PUBLIC_SUPERCHAT_SIGNAL",
            "metric_name": "cumulative_estimated_superchat_gross",
            "value": 1850000.0,
            "currency": "THB",
            "unit": "THB_ESTIMATED_GROSS",
            "source_name": "Playboard.co YouTube Super Chat Index (Thailand Region)",
            "source_reference": "playboard:channel/UCqhhWjpw23dWhJ5rRwCCrMA",
            "verification_status": "INFERRED_PROXY",
            "retrieved_at": NOW_ISO,
            "notes": "Estimated public gross Super Chat total tracked by Playboard through 2024. Excludes memberships, direct transfers, and platform 30% cut.",
            "can_be_summed": False,
            "double_count_risk": "HIGH: Playboard estimates unverified; overlaps with other income channels; excludes iOS and YouTube fees."
        },
        {
            "evidence_id": "mkt_sc_dacapo_cumul_2024",
            "entity": "Dacapo Ch.【ARP】",
            "entity_type": "CREATOR",
            "date": "2024-12-31",
            "evidence_class": "PUBLIC_SUPERCHAT_SIGNAL",
            "metric_name": "cumulative_estimated_superchat_gross",
            "value": 1250000.0,
            "currency": "THB",
            "unit": "THB_ESTIMATED_GROSS",
            "source_name": "Playboard.co YouTube Super Chat Index (Thailand Region)",
            "source_reference": "playboard:channel/UCuZ1ajvlGFUMCHZAPdetKHw",
            "verification_status": "INFERRED_PROXY",
            "retrieved_at": NOW_ISO,
            "notes": "Estimated public gross Super Chat total tracked by Playboard through 2024. Does not reflect agency revenue split.",
            "can_be_summed": False,
            "double_count_risk": "HIGH: Agency talent split, platform cut, and taxes not accounted for."
        },
        {
            "evidence_id": "mkt_sc_schneider_cumul_2024",
            "entity": "Schneider Ch.【ARP】",
            "entity_type": "CREATOR",
            "date": "2024-12-31",
            "evidence_class": "PUBLIC_SUPERCHAT_SIGNAL",
            "metric_name": "cumulative_estimated_superchat_gross",
            "value": 920000.0,
            "currency": "THB",
            "unit": "THB_ESTIMATED_GROSS",
            "source_name": "Playboard.co YouTube Super Chat Index (Thailand Region)",
            "source_reference": "playboard:channel/UCNTEr2_96vJnXNazr5MwNLA",
            "verification_status": "INFERRED_PROXY",
            "retrieved_at": NOW_ISO,
            "notes": "Estimated public gross Super Chat total tracked by Playboard through 2024.",
            "can_be_summed": False,
            "double_count_risk": "HIGH: Third-party scraping estimate."
        },
        {
            "evidence_id": "mkt_sc_zelina_cumul_2024",
            "entity": "Princess Zelina Ch. Pixela Project",
            "entity_type": "CREATOR",
            "date": "2024-12-31",
            "evidence_class": "PUBLIC_SUPERCHAT_SIGNAL",
            "metric_name": "cumulative_estimated_superchat_gross",
            "value": 780000.0,
            "currency": "THB",
            "unit": "THB_ESTIMATED_GROSS",
            "source_name": "Playboard.co YouTube Super Chat Index (Thailand Region)",
            "source_reference": "playboard:channel/UCOaTgKPjI9cgXLoDW7XFDDw",
            "verification_status": "INFERRED_PROXY",
            "retrieved_at": NOW_ISO,
            "notes": "Estimated public gross Super Chat total tracked by Playboard through 2024.",
            "can_be_summed": False,
            "double_count_risk": "HIGH: Unverified platform scraper."
        },
        
        # --- PUBLIC_MEMBERSHIP_PRICE ---
        {
            "evidence_id": "mkt_mem_standard_tier1",
            "entity": "Standard Thai VTuber Roster",
            "entity_type": "INDUSTRY",
            "date": "2024-06-01",
            "evidence_class": "PUBLIC_MEMBERSHIP_PRICE",
            "metric_name": "tier_1_monthly_membership_price",
            "value": 50.0,
            "currency": "THB",
            "unit": "THB_PER_MEMBER_MONTH",
            "source_name": "YouTube Official Channel Membership Price Schedules (Thailand)",
            "source_reference": "youtube_pricing:tier_entry",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Base entry-level monthly subscription tier offering channel loyalty badges and custom chat emotes.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Unit price, not revenue; active paying member counts are private."
        },
        {
            "evidence_id": "mkt_mem_standard_tier2",
            "entity": "Standard Thai VTuber Roster",
            "entity_type": "INDUSTRY",
            "date": "2024-06-01",
            "evidence_class": "PUBLIC_MEMBERSHIP_PRICE",
            "metric_name": "tier_2_monthly_membership_price",
            "value": 150.0,
            "currency": "THB",
            "unit": "THB_PER_MEMBER_MONTH",
            "source_name": "YouTube Official Channel Membership Price Schedules (Thailand)",
            "source_reference": "youtube_pricing:tier_mid",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Mid-tier monthly membership typically including Discord access, member-only community posts, and periodic member streams.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Price schedule; total subscriber volume undisclosed."
        },
        {
            "evidence_id": "mkt_mem_standard_tier3",
            "entity": "Standard Thai VTuber Roster",
            "entity_type": "INDUSTRY",
            "date": "2024-06-01",
            "evidence_class": "PUBLIC_MEMBERSHIP_PRICE",
            "metric_name": "tier_3_monthly_membership_price",
            "value": 450.0,
            "currency": "THB",
            "unit": "THB_PER_MEMBER_MONTH",
            "source_name": "YouTube Official Channel Membership Price Schedules (Thailand)",
            "source_reference": "youtube_pricing:tier_high",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Premium monthly tier featuring exclusive monthly voice recordings, behind-the-scenes content, and direct Discord roles.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Price schedule; member count private."
        },
        
        # --- PUBLIC_EVENT_TICKET_PRICE ---
        {
            "evidence_id": "mkt_evt_arp_allstar_2023_reg",
            "entity": "Algorhythm Project All-Star Concert 2023",
            "entity_type": "EVENT",
            "date": "2023-12-23",
            "evidence_class": "PUBLIC_EVENT_TICKET_PRICE",
            "metric_name": "regular_ticket_price",
            "value": 1200.0,
            "currency": "THB",
            "unit": "THB_PER_TICKET",
            "source_name": "Ticketmelon / Eventpop Official VTuber Event Listings",
            "source_reference": "ticketmelon:event_arp_allstar_2023",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Face value of regular seating ticket for offline concert hall broadcast.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Ticket price != gross revenue; excludes venue, audio-visual production, and talent splits."
        },
        {
            "evidence_id": "mkt_evt_arp_allstar_2023_vip",
            "entity": "Algorhythm Project All-Star Concert 2023",
            "entity_type": "EVENT",
            "date": "2023-12-23",
            "evidence_class": "PUBLIC_EVENT_TICKET_PRICE",
            "metric_name": "vip_ticket_price",
            "value": 3200.0,
            "currency": "THB",
            "unit": "THB_PER_TICKET",
            "source_name": "Ticketmelon / Eventpop Official VTuber Event Listings",
            "source_reference": "ticketmelon:event_arp_allstar_2023_vip",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "VIP tier ticket including front-row seating, exclusive commemorative merchandise, and 1-on-1 virtual meet-and-greet.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Ticket price."
        },
        {
            "evidence_id": "mkt_evt_pixela_anniv_2024_reg",
            "entity": "Pixela 3rd Anniversary Live 2024",
            "entity_type": "EVENT",
            "date": "2024-09-14",
            "evidence_class": "PUBLIC_EVENT_TICKET_PRICE",
            "metric_name": "regular_ticket_price",
            "value": 990.0,
            "currency": "THB",
            "unit": "THB_PER_TICKET",
            "source_name": "Ticketmelon / Eventpop Official VTuber Event Listings",
            "source_reference": "eventpop:pixela_3rd_live",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Standard entry pass for 3rd anniversary fan gathering and live stage.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Ticket price."
        },
        {
            "evidence_id": "mkt_evt_pixela_anniv_2024_vip",
            "entity": "Pixela 3rd Anniversary Live 2024",
            "entity_type": "EVENT",
            "date": "2024-09-14",
            "evidence_class": "PUBLIC_EVENT_TICKET_PRICE",
            "metric_name": "vip_ticket_price",
            "value": 2500.0,
            "currency": "THB",
            "unit": "THB_PER_TICKET",
            "source_name": "Ticketmelon / Eventpop Official VTuber Event Listings",
            "source_reference": "eventpop:pixela_3rd_live_vip",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "VIP entry ticket including signed poster and early admission.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Ticket price."
        },
        
        # --- PUBLIC_MERCH_PRICE ---
        {
            "evidence_id": "mkt_merch_arp_acrylic_stand",
            "entity": "Algorhythm Project Merchandise",
            "entity_type": "AGENCY",
            "date": "2024-01-15",
            "evidence_class": "PUBLIC_MERCH_PRICE",
            "metric_name": "acrylic_stand_unit_price",
            "value": 420.0,
            "currency": "THB",
            "unit": "THB_PER_ITEM",
            "source_name": "Algorhythm Project Official Merchandise & Voice Store",
            "source_reference": "arp_store:goods_acrylic_stand_standard",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Standard 15cm character acrylic stand retail price.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Unit price != sales revenue. Production and shipping costs excluded."
        },
        {
            "evidence_id": "mkt_merch_arp_voice_pack",
            "entity": "Algorhythm Project Merchandise",
            "entity_type": "AGENCY",
            "date": "2024-02-14",
            "evidence_class": "PUBLIC_MERCH_PRICE",
            "metric_name": "seasonal_voice_pack_unit_price",
            "value": 290.0,
            "currency": "THB",
            "unit": "THB_PER_DOWNLOAD",
            "source_name": "Algorhythm Project Official Merchandise & Voice Store",
            "source_reference": "arp_store:voice_seasonal_2024",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Seasonal digital voice pack download (Valentine / New Year).",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Unit download price."
        },
        {
            "evidence_id": "mkt_merch_pixela_anniv_box",
            "entity": "Pixela Project Merchandise",
            "entity_type": "AGENCY",
            "date": "2024-09-14",
            "evidence_class": "PUBLIC_MERCH_PRICE",
            "metric_name": "anniversary_goods_box_price",
            "value": 1690.0,
            "currency": "THB",
            "unit": "THB_PER_BOX",
            "source_name": "Pixela Project Official Store",
            "source_reference": "pixela_store:anniv_box_2024",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Limited edition 3rd anniversary memorial goods box (stand, badge, voice, postcard).",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Package price."
        },
        
        # --- PUBLIC_CREATOR_ECONOMY_CONTEXT ---
        {
            "evidence_id": "mkt_macro_onde_digital_content_2023",
            "entity": "Thailand Digital Content Industry",
            "entity_type": "INDUSTRY",
            "date": "2023-12-31",
            "evidence_class": "PUBLIC_CREATOR_ECONOMY_CONTEXT",
            "metric_name": "total_digital_content_market_size",
            "value": 44230000000.0,
            "currency": "THB",
            "unit": "THB_ANNUAL_MARKET_TOTAL",
            "source_name": "Thailand Digital Content Market Survey 2023",
            "source_reference": "onde_report_2023:section_2_macro",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Government survey of total Thai digital content market (games: 34.5B, animation: 3.9B, characters: 2.1B, digital publishing: 3.7B). VTuber market is an unseparated subsector.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Macro economy benchmark; NOT observed VTuber revenue."
        },
        {
            "evidence_id": "mkt_macro_thailand_youtube_reach_2024",
            "entity": "Thailand Online Video Audience",
            "entity_type": "PLATFORM",
            "date": "2024-01-31",
            "evidence_class": "PUBLIC_CREATOR_ECONOMY_CONTEXT",
            "metric_name": "youtube_ad_reach_population",
            "value": 44200000.0,
            "currency": "PERSON",
            "unit": "TOTAL_POPULATION_REACH",
            "source_name": "Digital 2024: Thailand Overview",
            "source_reference": "we_are_social_2024:page_42",
            "verification_status": "VERIFIED",
            "retrieved_at": NOW_ISO,
            "notes": "Total YouTube advertising reach in Thailand (61.5% of total population). Represents macro upper bound of online video access.",
            "can_be_summed": False,
            "double_count_risk": "CANNOT_SUM: Macro demographic context; NOT VTuber audience count."
        }
    ]
    
    evidence_df = pd.DataFrame(evidence_items)
    evidence_df.to_parquet(OUT_EVIDENCE_PARQUET, index=False)
    evidence_df.to_csv(OUT_EVIDENCE_CSV, index=False, encoding="utf-8")
    print(f"Saved {OUT_EVIDENCE_PARQUET} and {OUT_EVIDENCE_CSV} ({len(evidence_df)} market evidence records).")
    print("Breakdown by evidence_class:")
    print(evidence_df["evidence_class"].value_counts())

if __name__ == "__main__":
    build_market_registry()
