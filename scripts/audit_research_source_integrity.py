"""Source-semantic guards supplement cross-artifact equality checks."""
import json
import re
from pathlib import Path
import pandas as pd
from analytics.research_integrity import validate_scope, reactivation_series, is_ratio_key
ROOT = Path(__file__).resolve().parents[1]

def audit_source_integrity():
    data=json.loads((ROOT/'web/research/data/research_v2.json').read_text(encoding='utf8'))
    def walk(value):
        if isinstance(value,list):
            for child in value: walk(child)
        elif isinstance(value,dict):
            if any(is_ratio_key(k) for k in value) or is_ratio_key(str(value.get('metric', ''))) or 'numerator_scope' in value:
                validate_scope(value)
            for child in value.values(): walk(child)
    walk(data)
    assert data['source_integrity']['reactivation_series']==reactivation_series()
    assert data['source_integrity']['supply_saturation']['status']=='INSUFFICIENT_EVIDENCE'
    for row in pd.read_parquet(ROOT/'data/industry/outlook_indicators.parquet').to_dict('records'): validate_scope(row)
    snap=pd.read_parquet(ROOT/'data/industry/creator_public_snapshot.parquet')
    assert data['creator_ecosystem']['inactive_unavailable'] == int((snap.activity_status == 'HIATUS_OBSERVED').sum())
    assert not (snap.verification_status=='VERIFIED').any()
    assert (snap.activity_status_source=='MANIFEST_AT_SELECTION').all()
    events=pd.read_parquet(ROOT/'data/industry/creator_status_events.parquet')
    curated = events[events.subject_channel_id.notna()]
    assert (curated.subject_channel_id == curated.creator_channel_id).all()
    assert (curated.subject_name == curated.source_subject).all()
    from scripts.build_creator_lifecycle_evidence import VERIFIED_CREATOR_INTEL
    assert len(curated) == sum(map(len, VERIFIED_CREATOR_INTEL.values()))
    for row in curated.itertuples():
        assert any(e['subject_name'] == row.subject_name and e['source_reference'] == row.source_reference and e['event_type'] == row.event_type and e['event_date'] == row.event_date for e in VERIFIED_CREATOR_INTEL[row.creator_channel_id])
    for row in snap.itertuples():
        tiers=set(events.loc[events.creator_channel_id==row.channel_id,'evidence_tier'])
        assert row.lifecycle_evidence_tier in tiers or row.lifecycle_evidence_tier=='UNKNOWN'
    for name in ('OUTLOOK_MODEL.md','OUTLOOK_HYPOTHESES.md','LONG_RUNNING_RESEARCH_REPORT.md'):
        text=(ROOT/'docs/research_v2'/name).read_text(encoding='utf8')
        assert not re.search(r'700[–-]950|WACTOR Thailand (?:dissolved|collapsed)|RPG ceased (?:operations|talent ops)|1,370\+.*compet',text)
        assert 'numerator_scope=' in text and 'denominator_scope=' in text
        assert 'HYPOTHESIS / INSUFFICIENT_EVIDENCE' in text
        for row in reactivation_series():
            assert f"{row['year']}{' YTD' if row['partial_window'] else ''}: {row['accounts']}" in text
    print('PASS: denominator compatibility, reactivation series, organizational wording and snapshot semantics')
