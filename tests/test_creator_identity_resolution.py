"""Identity evidence is an ownership boundary, not a name-matching heuristic."""
import copy
import json
from pathlib import Path

import pytest

from scripts.resolve_creator_identities import main, merge_research, resolve_accounts

CHANNEL = 'UC' + 'a' * 22
OTHER_CHANNEL = 'UC' + 'b' * 22
YT = 'https://www.youtube.com/channel/' + CHANNEL
BASELINE = [{'channel_id': CHANNEL, 'channel_url': YT, 'person_id': 'vtuber_alpha', 'canonical_name': 'Alpha'}]
REVIEW = {'schema_version': 1, 'rows': [{'discovery_id': 'new_x', 'platform': 'x', 'url': 'https://x.com/alpha', 'display_name': 'Alpha', 'eligibility': 'vtuber'}]}


def researched(row=None):
    row = row or REVIEW['rows'][0]
    url = row['url']
    return {'discovery_id': row['discovery_id'], 'canonical_name': 'Alpha',
            'checked_urls': [url, YT], 'evidence_urls': [url], 'official_account_urls': [url],
            'evidence': [{'source_url': url, 'source_kind': 'official_profile',
                          'summary': 'Official profile identifies Alpha as this virtual persona.',
                          'supports': ['persona_identity', 'account_ownership'], 'observed_at': '2026-09-19T00:00:00Z'}],
            'no_existing_persona_match': True, 'reviewer': 'fixture:official-review', 'assertions': []}


def crosslink(persona='vtuber_alpha'):
    entry = researched()
    entry['no_existing_persona_match'] = False
    entry['official_account_urls'].append(YT)
    entry['evidence'][0]['summary'] = 'Official Alpha X profile links its YouTube channel.'
    entry['assertions'] = [{'method': 'official_crosslink', 'persona_id': persona, 'source_urls': [entry['evidence_urls'][0]]}]
    return {'rows': [entry]}


def trusted(status='verified'):
    return {'tables': {
        'personas': [{'id': 'registry_alpha', 'name': 'Alpha', 'review_status': 'verified'}],
        'accounts': [{'id': 'a_yt', 'platform': 'youtube', 'platform_id': CHANNEL, 'url': YT},
                     {'id': 'a_x', 'platform': 'x', 'platform_id': 'alpha', 'id_namespace': 'handle', 'url': 'https://x.com/alpha'}],
        'account_links': [{'account_id': key, 'persona_id': 'registry_alpha', 'review_status': status, 'evidence_id': 'ev'} for key in ('a_yt', 'a_x')],
        'evidence': [{'id': 'ev', 'url': YT + '/about', 'kind': 'official_profile', 'summary': 'Official YouTube profile links Alpha X account.', 'observed_at': '2026-09-19T00:00:00Z'}]}}


def test_verified_official_crosslink_attaches_existing_persona():
    row = resolve_accounts(BASELINE, REVIEW, {}, {}, crosslink())['resolutions'][0]
    assert (row['outcome'], row['persona_id'], row['method']) == ('existing_persona', 'vtuber_alpha', 'official_crosslink')
    assert row['conflict'] is False


def test_same_handle_on_two_platforms_does_not_merge_without_crosslink():
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha'))
    rows = resolve_accounts(BASELINE, review, {}, {}, {'rows': [researched(r) for r in review['rows']]})['resolutions']
    assert len({r['persona_id'] for r in rows}) == 2
    assert all(r['outcome'] == 'new_persona' for r in rows)


def test_conflicting_official_links_fail_closed_and_preserve_conflict_ledger():
    baseline = BASELINE + [{'channel_id': OTHER_CHANNEL, 'channel_url': 'https://www.youtube.com/channel/' + OTHER_CHANNEL, 'person_id': 'vtuber_beta', 'canonical_name': 'Beta'}]
    research = crosslink()
    research['rows'][0]['assertions'].append(dict(research['rows'][0]['assertions'][0], persona_id='vtuber_beta'))
    research['rows'][0]['official_account_urls'].append('https://www.youtube.com/channel/' + OTHER_CHANNEL)
    with pytest.raises(ValueError, match='conflicting persona') as exc:
        resolve_accounts(baseline, REVIEW, {}, {}, research)
    assert len(exc.value.ledger['conflicts']) == 1
    assert exc.value.ledger['resolutions'] == []


def test_every_accepted_account_requires_positive_evidence():
    with pytest.raises(ValueError, match='missing identity evidence'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, {})


def test_exact_channel_id_precedes_official_crosslink():
    review = copy.deepcopy(REVIEW)
    review['rows'][0].update(platform='youtube', channel_id=CHANNEL, url=YT)
    entry = researched(review['rows'][0])
    entry['no_existing_persona_match'] = False
    entry['assertions'] = [{'method': 'official_crosslink', 'persona_id': 'vtuber_alpha', 'source_urls': [YT]}]
    row = resolve_accounts(BASELINE, review, {}, {}, {'rows': [entry]})['resolutions'][0]
    assert row['method'] == 'exact_platform_id'
    assert row['persona_id'] == 'vtuber_alpha'


def test_trusted_verified_link_preserves_baseline_persona_id():
    row = resolve_accounts(BASELINE, REVIEW, trusted(), {}, {})['resolutions'][0]
    assert (row['method'], row['persona_id']) == ('verified_registry_link', 'vtuber_alpha')
    assert row['evidence_urls'] == [YT + '/about']


@pytest.mark.parametrize('change', ['unverified', 'missing_evidence', 'secondary_evidence'])
def test_unverified_registry_material_cannot_establish_ownership(change):
    registry = trusted('needs_evidence' if change == 'unverified' else 'verified')
    if change == 'missing_evidence':
        registry['tables']['evidence'] = []
    elif change == 'secondary_evidence':
        registry['tables']['evidence'][0]['kind'] = 'secondary_source'
    with pytest.raises(ValueError, match='missing identity evidence'):
        resolve_accounts(BASELINE, REVIEW, registry, {}, {})


def test_legacy_decision_cannot_overrule_final_exclusion():
    review = copy.deepcopy(REVIEW)
    review['rows'][0]['eligibility'] = 'exclude_non_persona'
    legacy = {'decisions': [{'discovery_id': 'new_x', 'decision': 'same_persona', 'candidate_persona_id': 'vtuber_alpha'}]}
    assert resolve_accounts(BASELINE, review, {}, legacy, {})['resolutions'] == []
    with pytest.raises(ValueError, match='excluded|ineligible'):
        resolve_accounts(BASELINE, review, {}, legacy, crosslink())


def test_legacy_visual_match_alone_is_not_identity_evidence():
    legacy = {'decisions': [{'discovery_id': 'new_x', 'decision': 'same_persona', 'candidate_persona_id': 'vtuber_alpha'}]}
    with pytest.raises(ValueError, match='missing identity evidence'):
        resolve_accounts(BASELINE, REVIEW, {}, legacy, {})


def test_new_persona_is_deterministic_across_order_and_name_spacing():
    entry = researched()
    first = resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})['resolutions'][0]
    entry['canonical_name'] = '  ALPHA  '
    second = resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})['resolutions'][0]
    assert first['persona_id'] == second['persona_id']
    assert first['persona_id'].startswith('persona_')


def test_evidence_urls_are_deduplicated_and_checked():
    entry = researched()
    entry['evidence_urls'] *= 2
    row = resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})['resolutions'][0]
    assert row['evidence_urls'] == ['https://x.com/alpha']
    entry['checked_urls'] = [YT]
    with pytest.raises(ValueError, match='checked'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})


@pytest.mark.parametrize('url', ['file:///private.json', 'https://user:secret@example.com/a', 'http://127.0.0.1/a', 'https://example.com/?api_key=secret'])
def test_unsafe_evidence_urls_rejected(url):
    entry = researched()
    entry['evidence'][0]['source_url'] = url
    entry['evidence_urls'] = entry['checked_urls'] = [url]
    with pytest.raises(ValueError, match='unsafe|invalid'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})


@pytest.mark.parametrize('field,value', [('evidence', []), ('no_existing_persona_match', False), ('canonical_name', '')])
def test_new_persona_requires_positive_official_identity_and_documented_search(field, value):
    entry = researched()
    entry[field] = value
    with pytest.raises(ValueError, match='identity|evidence|search|name'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, {'rows': [entry]})


def test_trusted_baseline_discovery_is_deduplicated_not_resolved_again():
    review = {'rows': [{'discovery_id': 'old', 'platform': 'youtube', 'url': YT, 'channel_id': CHANNEL, 'eligibility': 'trusted_baseline'}]}
    ledger = resolve_accounts(BASELINE, review, {}, {}, {})
    assert ledger['resolutions'] == []
    assert ledger['trusted_baseline_verified'] == ['old']
    review['rows'][0]['channel_id'] = OTHER_CHANNEL
    review['rows'][0]['url'] = 'https://www.youtube.com/channel/' + OTHER_CHANNEL
    with pytest.raises(ValueError, match='trusted_baseline'):
        resolve_accounts(BASELINE, review, {}, {}, {})


def test_official_crosslink_can_join_two_new_accounts_without_order_dependence():
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha'))
    entries = [researched(r) for r in review['rows']]
    entries[0]['no_existing_persona_match'] = False
    entries[0]['official_account_urls'].append(review['rows'][1]['url'])
    entries[0]['assertions'] = [{'method': 'official_crosslink', 'target_discovery_id': 'new_twitch', 'source_urls': ['https://x.com/alpha']}]
    first = resolve_accounts(BASELINE, review, {}, {}, {'rows': entries})
    second = resolve_accounts(BASELINE, {'rows': list(reversed(review['rows']))}, {}, {}, {'rows': list(reversed(entries))})
    assert first == second
    assert len({r['persona_id'] for r in first['resolutions']}) == 1


def test_crosslink_to_excluded_discovery_fails_closed():
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='excluded', platform='twitch', url='https://www.twitch.tv/alpha', eligibility='exclude_non_persona'))
    entry = researched()
    entry['assertions'] = [{'method': 'official_crosslink', 'target_discovery_id': 'excluded', 'source_urls': entry['evidence_urls']}]
    with pytest.raises(ValueError, match='excluded|ineligible'):
        resolve_accounts(BASELINE, review, {}, {}, {'rows': [entry]})


def test_explicit_identity_merge_requires_two_official_sources():
    research = crosslink()
    research['rows'][0]['assertions'][0]['method'] = 'explicit_official_identity'
    with pytest.raises(ValueError, match='two official sources'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, research)
    entry = research['rows'][0]
    entry['evidence'].append(dict(entry['evidence'][0], source_url=YT))
    entry['evidence_urls'].append(YT)
    entry['assertions'][0]['source_urls'].append(YT)
    assert resolve_accounts(BASELINE, REVIEW, {}, {}, research)['resolutions'][0]['persona_id'] == 'vtuber_alpha'


def test_duplicate_review_ids_and_research_disagreement_rejected():
    with pytest.raises(ValueError, match='duplicate discovery'):
        resolve_accounts(BASELINE, {'rows': REVIEW['rows'] * 2}, {}, {}, {})
    first = {'rows': [researched()]}
    assert merge_research([first, first]) == first
    second = copy.deepcopy(first)
    second['rows'][0]['canonical_name'] = 'Beta'
    with pytest.raises(ValueError, match='conflicting research'):
        merge_research([first, second])


def cli_files(tmp_path, review=REVIEW, research=None):
    values = {'review-bundle': review, 'baseline': BASELINE, 'trusted-registry': {}, 'legacy-decisions': {}, 'researched': research or {'rows': [researched()]}}
    args = []
    for name, value in values.items():
        path = tmp_path / (name + '.json')
        path.write_text(json.dumps(value), encoding='utf-8')
        args += ['--' + name, str(path)]
    return args


def test_cli_repeatable_research_validates_count_without_writing(tmp_path, capsys):
    args = cli_files(tmp_path)
    output = tmp_path / 'ledger.json'
    status = main(args + ['--researched', str(tmp_path / 'researched.json'), '--output', str(output), '--validate-only'])
    assert status == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary['accepted'] == 1
    assert summary['by_platform'] == {'x': 1}
    assert summary['unresolved'] == summary['conflicts'] == 0
    assert not output.exists()


def test_cli_full_393_validation_passes(tmp_path, capsys):
    review = {'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in review['rows']]})
    assert main(args + ['--validate-only']) == 0
    assert json.loads(capsys.readouterr().out)['accepted'] == 393


def test_cli_queue_reports_missing_evidence_and_platform_filter(tmp_path, capsys):
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha'))
    args = cli_files(tmp_path, review)
    out = tmp_path / 'queue.json'
    assert main(args + ['--platform', 'twitch', '--queue', '--output', str(out)]) == 1
    ledger = json.loads(out.read_text())
    assert ledger['resolutions'] == []
    assert [r['discovery_id'] for r in ledger['unresolved']] == ['new_twitch']


def test_cli_merges_platform_batches_deterministically(tmp_path, capsys):
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha'))
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in review['rows']]})
    out = tmp_path / 'ledger.json'
    assert main(args + ['--platform', 'x', '--output', str(out)]) == 0
    assert main(args + ['--platform', 'twitch', '--merge-existing', str(out), '--output', str(out)]) == 0
    assert [r['discovery_id'] for r in json.loads(out.read_text())['resolutions']] == ['new_twitch', 'new_x']


def test_committed_fixtures_are_a_resolved_review_pair():
    root = Path(__file__).parent / 'fixtures' / 'creator_registry'
    review = json.loads((root / 'review_bundle.json').read_text())
    ledger = json.loads((root / 'identity_resolutions.json').read_text())
    assert ledger['schema_version'] == 1
    assert {r['discovery_id'] for r in review['rows'] if r['eligibility'] == 'vtuber'} == {r['discovery_id'] for r in ledger['resolutions']}
    assert all(r['evidence_urls'] and r['checked_urls'] and r['conflict'] is False for r in ledger['resolutions'])


def test_official_account_url_cannot_smuggle_excluded_discovery_into_persona():
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='excluded', url='https://x.com/alpha_clips', eligibility='exclude_non_persona'))
    entry = researched()
    entry['official_account_urls'].append('https://x.com/alpha_clips')
    with pytest.raises(ValueError, match='excluded|ineligible'):
        resolve_accounts(BASELINE, review, {}, {}, {'rows': [entry]})


def test_duplicate_accepted_platform_accounts_fail_closed():
    review = copy.deepcopy(REVIEW)
    review['rows'].append(dict(review['rows'][0], discovery_id='duplicate'))
    with pytest.raises(ValueError, match='duplicate accepted account'):
        resolve_accounts(BASELINE, review, {}, {}, {'rows': [researched(r) for r in review['rows']]})


def test_researched_channel_id_resolves_youtube_handle_to_exact_baseline():
    row = dict(REVIEW['rows'][0], platform='youtube', url='https://www.youtube.com/@alpha')
    entry = researched(row)
    entry.update(platform_id=CHANNEL, canonical_url=YT, no_existing_persona_match=False)
    entry['official_account_urls'].append(YT)
    result = resolve_accounts(BASELINE, {'rows': [row]}, {}, {}, {'rows': [entry]})['resolutions'][0]
    assert result['platform_id'] == CHANNEL
    assert result['url'] == YT
    assert result['method'] == 'exact_platform_id'
    assert result['persona_id'] == 'vtuber_alpha'


def test_researched_channel_id_cannot_contradict_review_channel_id():
    row = dict(REVIEW['rows'][0], platform='youtube', channel_id=CHANNEL, url=YT)
    entry = researched(row)
    entry.update(platform_id=OTHER_CHANNEL, canonical_url='https://www.youtube.com/channel/' + OTHER_CHANNEL)
    entry['official_account_urls'].append(entry['canonical_url'])
    with pytest.raises(ValueError, match='conflicting persona|identifier'):
        resolve_accounts(BASELINE, {'rows': [row]}, {}, {}, {'rows': [entry]})


def test_cli_refuses_tampered_previous_batch(tmp_path, capsys):
    args = cli_files(tmp_path)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    payload = json.loads(out.read_text())
    payload['resolutions'][0]['persona_id'] = 'made_up'
    out.write_text(json.dumps(payload))
    original = out.read_bytes()
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 1
    assert out.read_bytes() == original


def test_cli_validation_cannot_hide_extra_accepted_accounts_with_platform_filter(tmp_path, capsys):
    review = {'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
    review['rows'].append(dict(REVIEW['rows'][0], discovery_id='extra_twitch', platform='twitch', url='https://www.twitch.tv/alpha'))
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in review['rows']]})
    assert main(args + ['--platform', 'x', '--validate-only']) == 1


def test_excluded_account_cannot_supply_positive_persona_evidence():
    review = copy.deepcopy(REVIEW)
    excluded_url = 'https://x.com/alpha_clips'
    review['rows'].append(dict(review['rows'][0], discovery_id='excluded', url=excluded_url, eligibility='exclude_non_persona'))
    entry = researched()
    entry['evidence'][0]['source_url'] = excluded_url
    entry['evidence_urls'] = [excluded_url]
    entry['checked_urls'].append(excluded_url)
    with pytest.raises(ValueError, match='excluded|ineligible'):
        resolve_accounts(BASELINE, review, {}, {}, {'rows': [entry]})


def test_explicit_identity_requires_distinct_sources_not_http_aliases():
    research = crosslink()
    entry = research['rows'][0]
    entry['assertions'][0]['method'] = 'explicit_official_identity'
    duplicate = 'http://x.com/alpha'
    entry['evidence'].append(dict(entry['evidence'][0], source_url=duplicate))
    entry['evidence_urls'].append(duplicate)
    entry['checked_urls'].append(duplicate)
    entry['assertions'][0]['source_urls'].append(duplicate)
    with pytest.raises(ValueError, match='two official sources'):
        resolve_accounts(BASELINE, REVIEW, {}, {}, research)


@pytest.mark.parametrize('batch_size', [117, 126, 150])
def test_cli_validates_complete_platform_batch_with_global_393(tmp_path, capsys, batch_size):
    rows = [dict(REVIEW['rows'][0], discovery_id=f'x_{i}', url=f'https://x.com/alpha{i}') for i in range(batch_size)]
    rows += [dict(REVIEW['rows'][0], discovery_id=f'twitch_{i}', platform='twitch', url=f'https://www.twitch.tv/alpha{i}') for i in range(393 - batch_size)]
    args = cli_files(tmp_path, {'rows': rows}, {'rows': [researched(r) for r in rows[:batch_size]]})
    assert main(args + ['--platform', 'x', '--validate-only']) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['accepted'] == summary['resolved'] == batch_size
    assert summary['unresolved'] == summary['conflicts'] == 0


def test_cli_reconciles_prior_x_persona_after_later_twitch_crosslink(tmp_path, capsys):
    review = copy.deepcopy(REVIEW)
    twitch = dict(review['rows'][0], discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha')
    review['rows'].append(twitch)
    args = cli_files(tmp_path, review)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--platform', 'x', '--output', str(out)]) == 0
    original_persona = json.loads(out.read_text())['resolutions'][0]['persona_id']
    entry = researched(twitch)
    entry['official_account_urls'].append(REVIEW['rows'][0]['url'])
    entry['assertions'] = [{'method': 'official_crosslink', 'target_discovery_id': 'new_x', 'source_urls': [twitch['url']]}]
    new_file = tmp_path / 'twitch.json'
    new_file.write_text(json.dumps({'rows': [entry]}))
    combined = args + ['--researched', str(new_file)]
    assert main(combined + ['--platform', 'twitch', '--merge-existing', str(out), '--output', str(out)]) == 0
    rows = json.loads(out.read_text())['resolutions']
    assert {r['discovery_id'] for r in rows} == {'new_x', 'new_twitch'}
    assert len({r['persona_id'] for r in rows}) == 1
    assert rows[0]['persona_id'] != original_persona
    expected = tmp_path / 'all-at-once.json'
    assert main(combined + ['--output', str(expected)]) == 0
    assert out.read_bytes() == expected.read_bytes()


def test_cli_allows_evidence_enrichment_but_rejects_invented_prior_source(tmp_path, capsys):
    args = cli_files(tmp_path)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    entry = researched()
    more = 'https://alpha.example/about'
    entry['evidence'].append(dict(entry['evidence'][0], source_url=more, source_kind='official_website'))
    entry['evidence_urls'].append(more)
    entry['checked_urls'].append(more)
    (tmp_path / 'researched.json').write_text(json.dumps({'rows': [entry]}))
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 0
    prior = json.loads(out.read_text())
    assert more in prior['resolutions'][0]['evidence_urls']
    prior['resolutions'][0]['evidence'][0]['summary'] = 'Invented provenance.'
    out.write_text(json.dumps(prior))
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 1


@pytest.mark.parametrize('method,blocked_field', [('exact', 'url'), ('exact', 'evidence_urls'), ('trusted', 'url'), ('trusted', 'evidence_urls')])
def test_exclusions_apply_to_exact_and_trusted_claim_provenance(method, blocked_field):
    review = copy.deepcopy(REVIEW)
    registry = trusted() if method == 'trusted' else {}
    blocked = YT + '/about' if method == 'trusted' else YT
    if method == 'exact':
        review['rows'][0].update(platform='youtube', channel_id=CHANNEL, url='https://www.youtube.com/@alpha')
    excluded = dict(REVIEW['rows'][0], discovery_id='excluded', eligibility='exclude_associated_account', url='https://x.com/alpha_clips')
    excluded[blocked_field] = blocked if blocked_field == 'url' else [blocked]
    review['rows'].append(excluded)
    with pytest.raises(ValueError, match='excluded|ineligible'):
        resolve_accounts(BASELINE, review, registry, {}, {})


@pytest.mark.parametrize('table', ['personas', 'accounts', 'evidence'])
@pytest.mark.parametrize('contradictory', [False, True])
def test_duplicate_trusted_ids_fail_independently_of_order(table, contradictory):
    registry = trusted()
    duplicate = copy.deepcopy(registry['tables'][table][0])
    if contradictory:
        duplicate['review_status' if table == 'personas' else 'url'] = 'needs_evidence' if table == 'personas' else 'https://unrelated.example/profile'
    registry['tables'][table].append(duplicate)
    for rows in [registry['tables'][table], list(reversed(registry['tables'][table]))]:
        candidate = copy.deepcopy(registry)
        candidate['tables'][table] = rows
        with pytest.raises(ValueError, match='duplicate.*ID'):
            resolve_accounts(BASELINE, REVIEW, candidate, {}, {})


def test_incoming_crosslink_uses_own_attachment_method_not_peer_exact_id():
    review = copy.deepcopy(REVIEW)
    ytrow = dict(review['rows'][0], discovery_id='new_youtube', platform='youtube', channel_id=CHANNEL, url=YT)
    review['rows'].append(ytrow)
    entry = researched(ytrow)
    entry['official_account_urls'].append(REVIEW['rows'][0]['url'])
    entry['assertions'] = [{'method': 'official_crosslink', 'target_discovery_id': 'new_x', 'source_urls': [YT]}]
    ledger = resolve_accounts(BASELINE, review, {}, {}, {'rows': [researched(), entry]})
    rows = {r['discovery_id']: r for r in ledger['resolutions']}
    assert rows['new_youtube']['method'] == 'exact_platform_id'
    assert rows['new_x']['method'] == 'official_crosslink'
    assert rows['new_x']['method_evidence_urls'] == [YT]
    assert ledger['counts']['by_method'] == {'exact_platform_id': 1, 'official_crosslink': 1}


def test_merge_rejects_tampered_attachment_evidence_urls(tmp_path, capsys):
    research = crosslink()
    entry = research['rows'][0]
    entry['evidence'].append(dict(entry['evidence'][0], source_url=YT, summary='Official persona introduction.'))
    entry['evidence_urls'].append(YT)
    args = cli_files(tmp_path, research=research)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    prior = json.loads(out.read_text())
    prior['resolutions'][0]['method_evidence_urls'] = [YT]
    out.write_text(json.dumps(prior))
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 1


def test_platform_validation_rejects_empty_selection(tmp_path, capsys):
    review = {'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in review['rows']]})
    assert main(args + ['--platform', 'typo', '--validate-only']) == 1
