import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from scripts import build_reviewed_surface_cohort as cohort_builder

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'docs/evidence/expanded-v1/public-review-2026-09-10'

def test_review_covers_exact_queue_with_matching_sources():
    queue=list(csv.DictReader((REVIEW/'provisional_virtual_review_queue.csv').open(encoding='utf-8-sig')))
    review=json.loads((REVIEW/'provisional_resolution_v1.json').read_text(encoding='utf-8'))['rows']
    sources=json.loads((REVIEW/'provisional_resolution_sources_v1.json').read_text(encoding='utf-8'))
    source_map={r['source_url']:r for r in sources}
    assert len(review)==len({r['channel_id'] for r in review})==45
    assert {r['channel_id'] for r in review}=={r['channel_id'] for r in queue}
    assert Counter(r['review_priority'] for r in queue)=={'HIGH':8,'NORMAL':37}
    for row in review:
        assert row['old_status']=='PROVISIONAL_VIRTUAL'
        assert row['new_status'] in {'STRICT_VIRTUAL','HOLD_NEEDS_CHANNEL_REVIEW','EXCLUDE_NON_PERSONA_ACCOUNT','EXCLUDE_NON_VIRTUAL_CREATOR'}
        assert all(row[k] for k in ['entity_type','presentation_format','source_urls','evidence_summary','decision_reason','reviewer','reviewed_at'])
        for url in row['source_urls']:
            assert source_map[url]['observed_uploader_id']==row['channel_id']

def test_resolution_survives_rebuild_without_reclassifying_identity(tmp_path):
    shutil.copytree(REVIEW,tmp_path,dirs_exist_ok=True)
    original={p.name:p.read_bytes() for p in tmp_path.glob('identity_batch_*.json')}
    cohort_builder.build(tmp_path)
    data=json.loads((tmp_path/'channel_eligibility_v1.json').read_text(encoding='utf-8'))
    assert data['status_counts']=={'STRICT_VIRTUAL':274,'HOLD_NEEDS_CHANNEL_REVIEW':132,'EXCLUDE_NON_PERSONA_ACCOUNT':2}
    assert len(data['rows'])==408
    assert data['evidence_scope']
    assert 'never by itself excludes' in data['policy']['rejected_event_rule']
    decisions=json.loads((REVIEW/'provisional_resolution_v1.json').read_text(encoding='utf-8'))['rows']
    by_id={r['channel_id']:r for r in data['rows']}
    for decision in decisions:
        row=by_id[decision['channel_id']]
        assert row['eligibility_status']==decision['new_status']
        assert row['channel_review']==decision
    assert original=={p.name:p.read_bytes() for p in tmp_path.glob('identity_batch_*.json')}

@pytest.mark.parametrize('status',['HOLD_NEEDS_CHANNEL_REVIEW','EXCLUDE_NON_PERSONA_ACCOUNT','EXCLUDE_NON_VIRTUAL_CREATOR'])
def test_hold_and_exclusions_never_enter_strict_cohort(status):
    rows=[dict(channel_id='a',eligibility_status='PROVISIONAL_VIRTUAL',strict_surface=False)]
    resolutions=[dict(channel_id='a',old_status='PROVISIONAL_VIRTUAL',new_status=status,conflict_flag=False)]
    cohort_builder.apply_resolutions(rows,resolutions)
    assert rows[0]['eligibility_status']==status
    assert rows[0]['strict_surface'] is False

@pytest.mark.parametrize('bad',[
    [],
    [dict(channel_id='b',old_status='PROVISIONAL_VIRTUAL',new_status='STRICT_VIRTUAL')],
    [dict(channel_id='a',old_status='PROVISIONAL_VIRTUAL',new_status='PROVISIONAL_VIRTUAL')],
    [dict(channel_id='a',old_status='STRICT_VIRTUAL',new_status='STRICT_VIRTUAL')],
    [dict(channel_id='a',old_status='PROVISIONAL_VIRTUAL',new_status='STRICT_VIRTUAL')]*2,
    [dict(channel_id='a',old_status='PROVISIONAL_VIRTUAL',new_status='STRICT_VIRTUAL',conflict_flag=True)],
])
def test_invalid_or_incomplete_resolution_fails_closed(bad):
    rows=[dict(channel_id='a',eligibility_status='PROVISIONAL_VIRTUAL',strict_surface=False)]
    with pytest.raises(ValueError):cohort_builder.apply_resolutions(rows,bad)
