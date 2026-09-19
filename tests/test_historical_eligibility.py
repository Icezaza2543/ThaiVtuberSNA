from scripts.build_historical_eligibility import classify, youtube_id, build


def test_registry_labels_and_persona_matches_never_grant_eligibility():
    for row in [dict(vtuber_status='CONFIRMED'), dict(has_verified_persona=True),
                dict(review_status='verified'), dict(name='VTuberTH')]:
        assert classify(row, {})[0] == 'HOLD_NEEDS_CHANNEL_REVIEW'


def test_only_exact_youtube_channel_ids_inherit_reviews():
    cid = 'UC' + 'a' * 22
    reviews = {cid: {'eligibility_status': 'STRICT_VIRTUAL'}}
    assert classify({'platform': 'youtube', 'platform_id': cid}, reviews)[0] == 'STRICT_VIRTUAL'
    assert classify({'platform': 'x', 'platform_id': cid}, reviews)[0].startswith('HOLD')
    assert classify({'platform': 'youtube', 'url': 'https://youtube.com/@VTuber'}, reviews)[0].startswith('HOLD')
    assert youtube_id({'platform': 'youtube', 'url': 'https://example.com/channel/' + cid}) is None


def test_all_historical_records_are_accounted_for_and_exports_fail_closed(tmp_path):
    result = build(tmp_path)
    assert sum(s['records'] for s in result['sources']) == sum(len(r['origins']) for r in result['rows'])
    assert len({r['account_key'] for r in result['rows']}) == len(result['rows'])
    assert all(r['included'] == (r['eligibility_status'] == 'STRICT_VIRTUAL') for r in result['rows'])
    assert sum(r['included'] for r in result['rows']) == 274
    assert any(s['records'] == 884 for s in result['sources'])
    assert any(s['records'] == 1370 for s in result['sources'])
    assert all(r['channel_id'] and r['platform'] == 'youtube' for r in result['rows'] if r['included'])
