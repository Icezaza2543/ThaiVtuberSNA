import csv,json
from pathlib import Path
from scripts import build_surface_analytics as surface_builder

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'docs/evidence/expanded-v1/public-review-2026-09-10'

def test_surface_rebuild_preserves_audit_and_withholds_private_totals(tmp_path,monkeypatch):
    monkeypatch.setattr(surface_builder,'OUT',tmp_path/'surface.json')
    data=surface_builder.build()
    assert data['cohort']['strict_virtual_channels']==274
    assert data['cohort']['provisional_virtual_channels']==0
    assert data['audit']['provisional_review_queue']==0
    assert data['audit']['resolved_from_provisional']==45
    assert data['audit']['still_unresolved_from_provisional']==0
    assert data['audit']['strict_channels_flagged_for_spot_check']==27
    assert data['limitations']
    assert data['timeline']['note']
    assert data['audience']['clean_unique_pseudonyms'] is None
    assert data['audience']['clean_interactions'] is None
    strict=set(json.loads((REVIEW/'surface_virtual_cohort_v1.json').read_text(encoding='utf-8'))['strict_channel_ids'])
    coverage=list(csv.DictReader((surface_builder.DOWNTIME/'channel_coverage.csv').open(encoding='utf-8-sig')))
    assert data['content']['catalog_videos']==sum(int(r['video_count']) for r in coverage if r['channel_id'] in strict)
    graph=json.loads(surface_builder.GRAPH.read_text(encoding='utf-8'))
    edges=[e for e in graph['edges'] if e['source'] in strict and e['target'] in strict]
    assert data['network']['edges']==len(edges)
    assert data['network']['density']==round(2*len(edges)/(274*273),6)

def test_surface_web_copy_has_no_stale_denominator():
    assert '229' not in (ROOT/'web/research.js').read_text(encoding='utf-8')
    assert '229-channel' not in (ROOT/'web/index.html').read_text(encoding='utf-8')
