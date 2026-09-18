from scripts.compact_campaign_review import classify


def candidate(title):
    return classify({'title':title,'published_at':'2024-01-01','video_id':'synthetic'})


def test_predebut_is_not_redebut_and_is_penalized():
    row=candidate('Pre-Debut Introducing [VTuberTH]')
    assert row['candidate_type']=='identity_start_candidate'
    assert 'pre_debut_or_test' in row['uncertainty_flags']
    assert row['review_score']<candidate('VTuber debut')['review_score']


def test_event_types_are_separate():
    assert candidate('RE-DEBUT')['candidate_type']=='redebut_candidate'
    assert candidate('เปิดตัวโมเดลใหม่')['candidate_type']=='model_change_candidate'
    assert candidate('初配信')['candidate_type']=='identity_start_candidate'
    assert candidate('VTuberTH gaming')['candidate_type']=='weak_virtual_terminology'


def test_context_does_not_become_assigned_date():
    row=candidate('debut anniversary reaction')
    assert row['review_score']<candidate('debut')['review_score']
    assert not {'identity_start','vtuber_debut_at','redebut'} & row.keys()
