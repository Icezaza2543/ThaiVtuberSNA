"""
Unit & Integration Tests for the 3-Phase Pipeline:
Phase 1: Thai VTuber Criteria, Lifecycle & Registry Checkpointing
Phase 2: Video Inventory Cataloging
Phase 3: Balanced Video Collector, Source Separation & Privacy Audit
"""
import pytest
from pathlib import Path
from core.thai_vtuber_criteria import ThaiVtuberCriteriaEngine
from core.registry_checkpoint import PipelineCheckpointManager


def test_thai_vtuber_criteria_confirmed():
    engine = ThaiVtuberCriteriaEngine()
    eval_result = engine.evaluate_vtuber(
        channel_id="UCqhhWjpw23dWhJ5rRwCCrMA",
        name="Aisha Channel",
        description="Official channel of Aisha, Thai Virtual Idol / VTuber วีทูปเบอร์ไทย",
        handle="@AishaChannel",
        country="TH",
        sources=["Thai VTuber Ranking", "Virtual YouTuber Fandom Wiki"],
        last_published_video_at="2026-08-01T12:00:00Z"
    )
    assert eval_result["vtuber_status"] == "CONFIRMED"
    assert eval_result["person_id"] == "vtuber_aisha"
    assert eval_result["channel_type"] == "main"
    assert eval_result["activity_status"] in ["active", "hiatus"]
    assert eval_result["thai_confidence"] > 0.3


def test_thai_vtuber_criteria_unconfirmed_quarantine():
    engine = ThaiVtuberCriteriaEngine()
    eval_result = engine.evaluate_vtuber(
        channel_id="UCrandomunverifiedchannel123",
        name="Random Gamer",
        description="Just playing Minecraft with friends. Subscribe!",
        handle="@randomgamer",
        country="US",
        sources=["Random Directory"],
        last_published_video_at=None
    )
    # Weak signals, no Thai, no VTuber indicator -> UNCONFIRMED
    assert eval_result["vtuber_status"] == "UNCONFIRMED"
    assert eval_result["activity_status"] == "unknown"


def test_multi_channel_person_mapping():
    engine = ThaiVtuberCriteriaEngine()
    main_ch = engine.evaluate_vtuber(
        channel_id="UCqhhWjpw23dWhJ5rRwCCrMA",
        name="Aisha Channel",
        description="Aisha main",
        handle="@AishaChannel"
    )
    sub_ch = engine.evaluate_vtuber(
        channel_id="UC5VPIoY1j_x9UZSqkpwg8jw",
        name="Aisha Sub",
        description="Aisha clips and sub",
        handle="@AishaSub"
    )
    assert main_ch["person_id"] == sub_ch["person_id"] == "vtuber_aisha"
    assert main_ch["channel_type"] == "main"
    assert sub_ch["channel_type"] == "sub"
    assert main_ch["channel_id"] != sub_ch["channel_id"]


def test_checkpoint_manager_persistence(tmp_path):
    ckpt_file = tmp_path / "test_checkpoint.json"
    mgr = PipelineCheckpointManager(ckpt_file)
    mgr.mark_source_completed("Test Source", 42, {"meta": "ok"})
    mgr.mark_channel_processed("UCtestchannel123456789012", is_unconfirmed=False)
    mgr.log_inaccessible_source("Private API", "https://api.test", "HTTP 403", 403)
    mgr.save()

    # Reload from disk
    mgr2 = PipelineCheckpointManager(ckpt_file)
    assert "Test Source" in mgr2.state["completed_sources"]
    assert mgr2.is_channel_processed("UCtestchannel123456789012")
    assert len(mgr2.state["inaccessible_sources"]) == 1
    assert mgr2.state["inaccessible_sources"][0]["status_code"] == 403
