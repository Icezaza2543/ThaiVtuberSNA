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
    review = {'eligibility_counts': {'vtuber': 393}, 'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
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
    review = {'eligibility_counts': {'vtuber': 393}, 'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
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
    args = cli_files(tmp_path, {'eligibility_counts': {'vtuber': 393}, 'rows': rows}, {'rows': [researched(r) for r in rows[:batch_size]]})
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
    review = {'eligibility_counts': {'vtuber': 393}, 'rows': [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(393)]}
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in review['rows']]})
    assert main(args + ['--platform', 'typo', '--validate-only']) == 1


def linked_chain():
    xrow = dict(REVIEW['rows'][0])
    twitch = dict(xrow, discovery_id='new_twitch', platform='twitch', url='https://www.twitch.tv/alpha', platform_id='12345')
    youtube = dict(xrow, discovery_id='new_youtube', platform='youtube', url=YT, channel_id=CHANNEL)
    entries = [researched(xrow), researched(twitch)]
    for entry, target in zip(entries, [twitch, youtube]):
        entry['no_existing_persona_match'] = False
        entry['official_account_urls'].append(target['url'])
        entry['assertions'] = [{'method': 'official_crosslink', 'target_discovery_id': target['discovery_id'], 'source_urls': entry['evidence_urls']}]
    return {'rows': [xrow, twitch, youtube]}, {'rows': entries}


@pytest.mark.parametrize('field,value', [('url', 'https://www.twitch.tv/alpha'), ('canonical_url', 'https://www.twitch.tv/alpha'), ('platform_id', '12345')])
def test_merge_cannot_substitute_peer_account_identity(tmp_path, capsys, field, value):
    review, research = linked_chain()
    args = cli_files(tmp_path, review, research)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    prior = json.loads(out.read_text())
    row = next(r for r in prior['resolutions'] if r['discovery_id'] == 'new_x')
    row[field] = value
    out.write_text(json.dumps(prior))
    unchanged = out.read_bytes()
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 1
    assert out.read_bytes() == unchanged


@pytest.mark.parametrize('path', [
    ['new_x', 'new_twitch', 'new_x'],
    ['new_x', 'new_youtube'],
    ['new_x', 'new_youtube', 'new_twitch'],
    ['new_x', 'new_twitch'],
])
def test_merge_requires_simple_verified_path_ending_at_identity_root(tmp_path, capsys, path):
    review, research = linked_chain()
    args = cli_files(tmp_path, review, research)
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    prior = json.loads(out.read_text())
    row = next(r for r in prior['resolutions'] if r['discovery_id'] == 'new_x')
    assert row['identity_path'] == ['new_x', 'new_twitch', 'new_youtube']
    row['identity_path'] = path
    out.write_text(json.dumps(prior))
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 1


def test_tied_verified_claims_are_byte_stable_when_trusted_arrays_reverse(tmp_path, capsys):
    registry = trusted()
    registry['tables']['evidence'].append(dict(registry['tables']['evidence'][0], id='ev_other', url='https://alpha.example/accounts'))
    registry['tables']['account_links'].append(dict(registry['tables']['account_links'][1], evidence_id='ev_other'))
    first = resolve_accounts(BASELINE, REVIEW, registry, {}, {})
    reversed_registry = {'tables': {key: list(reversed(rows)) for key, rows in registry['tables'].items()}}
    second = resolve_accounts(BASELINE, REVIEW, reversed_registry, {}, {})
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    args = cli_files(tmp_path, research={'rows': []})
    registry_path = tmp_path / 'trusted-registry.json'
    registry_path.write_text(json.dumps(registry))
    out = tmp_path / 'ledger.json'
    assert main(args + ['--output', str(out)]) == 0
    expected = out.read_bytes()
    registry_path.write_text(json.dumps(reversed_registry))
    assert main(args + ['--merge-existing', str(out), '--output', str(out)]) == 0
    assert out.read_bytes() == expected



def test_cli_validation_uses_corrected_declared_count_and_excludes_group(tmp_path, capsys):
    rows = [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(392)]
    rows.append(dict(REVIEW['rows'][0], discovery_id='corrected_group', eligibility='exclude_virtual_group', url='https://x.com/group'))
    review = {'eligibility_counts': {'vtuber': 392, 'exclude_virtual_group': 1}, 'rows': rows}
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in rows[:-1]]})
    assert main(args + ['--validate-only']) == 0
    assert json.loads(capsys.readouterr().out)['resolved'] == 392


@pytest.mark.parametrize('counts', [None, {'vtuber': 393}, {'vtuber': 392, 'unavailable': 1}])
def test_cli_validation_rejects_missing_or_inaccurate_declared_eligibility_counts(tmp_path, capsys, counts):
    rows = [dict(REVIEW['rows'][0], discovery_id=f'new_{i:03}', url=f'https://x.com/alpha{i}') for i in range(392)]
    review = {'rows': rows}
    if counts is not None: review['eligibility_counts'] = counts
    args = cli_files(tmp_path, review, {'rows': [researched(r) for r in rows]})
    assert main(args + ['--platform', 'x', '--validate-only']) == 1


def trusted_link_correction_fixture():
    import hashlib
    registry = trusted()
    for link in registry['tables']['account_links']:
        link['id'] = 'link_' + link['account_id']
    link = registry['tables']['account_links'][1]
    account = registry['tables']['accounts'][1]
    evidence = registry['tables']['evidence'][0]
    def digest(record):
        return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    correction = {'link_id': link['id'], 'account_id': account['id'], 'asserted_persona_id': link['persona_id'],
                  'evidence_id': evidence['id'], 'disposition': 'reject_identity_link',
                  'link_sha256': digest(link), 'account_sha256': digest(account), 'evidence_sha256': digest(evidence),
                  'source_urls': [evidence['url'], 'https://x.com/alpha'],
                  'summary': 'The cited site lists a separate client, not the owner account.',
                  'observed_at': '2026-09-19T15:00:00Z', 'reviewer': 'fixture:correction'}
    return registry, {'schema_version': 1, 'corrections': [correction]}


def test_explicit_trusted_link_correction_rejects_only_named_link_and_preserves_audit():
    registry, corrections = trusted_link_correction_fixture()
    before = copy.deepcopy(registry)
    result = resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [researched()]}, trusted_link_corrections=[corrections])
    assert result['resolutions'][0]['outcome'] == 'new_persona'
    assert result['resolutions'][0]['persona_id'] != 'vtuber_alpha'
    assert result['trusted_link_corrections_applied'][0]['correction'] == corrections['corrections'][0]
    assert result['trusted_link_corrections_applied'][0]['original_link'] == registry['tables']['account_links'][1]
    assert registry == before
    # Rejecting the X ownership edge must not remove the valid channel/persona edge.
    assert resolve_accounts(BASELINE, REVIEW, registry, {}, crosslink(), trusted_link_corrections=[corrections])['resolutions'][0]['persona_id'] == 'vtuber_alpha'


@pytest.mark.parametrize('change', ['unknown_link', 'wrong_account', 'wrong_persona', 'wrong_evidence', 'stale_link', 'stale_account', 'stale_evidence', 'uncited_evidence', 'unverified', 'unsafe_source', 'duplicate_conflict'])
def test_invalid_or_stale_trusted_link_corrections_fail_closed(change):
    registry, corrections = trusted_link_correction_fixture()
    correction = corrections['corrections'][0]
    if change == 'unknown_link': correction['link_id'] = 'missing'
    elif change == 'wrong_account': correction['account_id'] = 'a_yt'
    elif change == 'wrong_persona': correction['asserted_persona_id'] = 'someone_else'
    elif change == 'wrong_evidence': correction['evidence_id'] = 'missing'
    elif change == 'stale_link': registry['tables']['account_links'][1]['reviewed_at'] = 'changed'
    elif change == 'stale_account': registry['tables']['accounts'][1]['url'] = 'https://x.com/reassigned'
    elif change == 'stale_evidence': registry['tables']['evidence'][0]['summary'] = 'Updated evidence'
    elif change == 'uncited_evidence': correction['source_urls'] = ['https://x.com/alpha']
    elif change == 'unverified': registry['tables']['account_links'][1]['review_status'] = 'needs_evidence'
    elif change == 'unsafe_source': correction['source_urls'].append('file:///private')
    else:
        corrections['corrections'].append(dict(correction, summary='Conflicting correction'))
    with pytest.raises(ValueError, match='correction|unsafe'):
        resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [researched()]}, trusted_link_corrections=[corrections])


def test_repeated_identical_trusted_corrections_are_deterministic():
    registry, corrections = trusted_link_correction_fixture()
    first = resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [researched()]}, trusted_link_corrections=[corrections])
    second = resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [researched()]}, trusted_link_corrections=[corrections, corrections])
    assert first == second


def test_cli_repeated_trusted_corrections_and_merge_require_retained_audit(tmp_path):
    registry, corrections = trusted_link_correction_fixture()
    inputs = {'baseline': BASELINE, 'review-bundle': dict(REVIEW, eligibility_counts={'vtuber': 1}),
              'trusted-registry': registry, 'legacy-decisions': {}, 'researched': {'rows': [researched()]},
              'trusted-link-corrections': corrections}
    args = []
    for flag, payload in inputs.items():
        path = tmp_path / (flag + '.json')
        path.write_text(json.dumps(payload), encoding='utf-8')
        args += ['--' + flag, str(path)]
    output = tmp_path / 'ledger.json'
    repeated = ['--trusted-link-corrections', str(tmp_path / 'trusted-link-corrections.json')]
    assert main(args + repeated + ['--output', str(output)]) == 0
    original = output.read_bytes()
    ledger = json.loads(original)
    assert len(ledger['trusted_link_corrections_applied']) == 1
    assert main(args + ['--merge-existing', str(output), '--output', str(output)]) == 0
    assert output.read_bytes() == original
    correction_flag = args.index('--trusted-link-corrections')
    without = args[:correction_flag] + args[correction_flag + 2:]
    assert main(without + ['--merge-existing', str(output), '--output', str(output)]) == 1
    assert output.read_bytes() == original


def required_corrections_fixture():
    """Two independent corrections; the selected X row only uses one of them."""
    from scripts.resolve_creator_identities import _record_sha256
    registry, corrections = trusted_link_correction_fixture()
    link = registry['tables']['account_links'][0]
    account = registry['tables']['accounts'][0]
    corrections['corrections'].append(dict(
        corrections['corrections'][0], link_id=link['id'], account_id=account['id'],
        link_sha256=_record_sha256(link), account_sha256=_record_sha256(account)))
    manifest = sorted(({'link_id': row['link_id'], 'correction_sha256': _record_sha256(row)}
                       for row in corrections['corrections']), key=lambda row: row['link_id'])
    return registry, corrections, manifest


def required_correction_cli(tmp_path, source):
    registry, corrections, manifest = required_corrections_fixture()
    review = dict(REVIEW, eligibility_counts={'vtuber': 1})
    research = {'rows': [researched()]}
    (review if source == 'review' else research)['required_trusted_link_corrections'] = manifest
    args = cli_files(tmp_path, review, research)
    (tmp_path / 'trusted-registry.json').write_text(json.dumps(registry), encoding='utf-8')
    path = tmp_path / 'corrections.json'
    path.write_text(json.dumps(corrections), encoding='utf-8')
    return args, path, corrections, manifest


@pytest.mark.parametrize('source', ['review', 'research'])
@pytest.mark.parametrize('mode', ['fresh', 'filtered_validate', 'full_validate', 'merge'])
@pytest.mark.parametrize('supplied', ['omitted', 'partial', 'stale', 'extra_conflicting'])
def test_required_corrections_fail_before_output_in_every_cli_mode(tmp_path, capsys, source, mode, supplied):
    args, path, corrections, _ = required_correction_cli(tmp_path, source)
    output = tmp_path / 'ledger.json'
    original = None
    if mode == 'merge':
        assert main(args + ['--trusted-link-corrections', str(path), '--output', str(output)]) == 0
        original = output.read_bytes()
        args += ['--merge-existing', str(output)]
    elif mode == 'filtered_validate':
        args += ['--platform', 'x', '--validate-only']
    elif mode == 'full_validate':
        args += ['--validate-only']
    else:
        args += ['--queue']
    if supplied != 'omitted':
        if supplied == 'partial':
            corrections['corrections'] = corrections['corrections'][:1]
        elif supplied == 'stale':
            corrections['corrections'][0]['summary'] += ' Changed after approval.'
        else:
            corrections['corrections'].append(dict(corrections['corrections'][0], summary='Conflicting extra record.'))
        path.write_text(json.dumps(corrections), encoding='utf-8')
        args += ['--trusted-link-corrections', str(path)]
    capsys.readouterr()
    assert main(args + ['--output', str(output)]) == 1
    captured = capsys.readouterr()
    assert 'correction' in json.loads(captured.err)['error']
    assert captured.out == ''  # No count/validation success before the dependency check.
    if original is not None:
        assert output.read_bytes() == original
    else:
        assert not output.exists()


@pytest.mark.parametrize('source', ['review', 'research'])
@pytest.mark.parametrize('mode', ['fresh', 'filtered_validate', 'full_validate', 'merge'])
def test_complete_required_corrections_succeed_in_every_cli_mode(tmp_path, source, mode):
    args, path, _, manifest = required_correction_cli(tmp_path, source)
    args += ['--trusted-link-corrections', str(path)]
    output = tmp_path / 'ledger.json'
    if mode == 'merge':
        assert main(args + ['--output', str(output)]) == 0
        original = output.read_bytes()
        args += ['--merge-existing', str(output)]
    elif mode == 'filtered_validate':
        args += ['--platform', 'x', '--validate-only']
    elif mode == 'full_validate':
        args += ['--validate-only']
    assert main(args + ['--output', str(output)]) == 0
    if 'validate' in mode:
        assert not output.exists()
    else:
        ledger = json.loads(output.read_text(encoding='utf-8'))
        assert ledger['required_trusted_link_corrections'] == manifest
        assert len(ledger['trusted_link_corrections_applied']) == 2
        assert ledger['resolutions'][0]['outcome'] == 'new_persona'
        if mode == 'merge':
            assert output.read_bytes() == original


def test_merged_research_preserves_sorted_correction_requirements_and_rejects_conflicts():
    _, _, manifest = required_corrections_fixture()
    first = {'rows': [researched()], 'required_trusted_link_corrections': manifest[:1]}
    second = {'rows': [], 'required_trusted_link_corrections': manifest[1:]}
    merged = merge_research([second, first, first])
    assert merged == {'rows': [researched()], 'required_trusted_link_corrections': manifest}
    second['required_trusted_link_corrections'] = [dict(manifest[0], correction_sha256='0' * 64)]
    with pytest.raises(ValueError, match='conflicting required trusted link correction'):
        merge_research([first, second])


@pytest.mark.parametrize('manifest', [None, {}, ['link_a_x'], [{'link_id': 'link_a_x'}],
                                     [{'link_id': 'link_a_x', 'correction_sha256': 'invalid'}],
                                     [{'link_id': '', 'correction_sha256': '0' * 64}]])
def test_malformed_required_correction_manifest_fails_closed(manifest):
    with pytest.raises(ValueError, match='required trusted link correction'):
        resolve_accounts(BASELINE, dict(REVIEW, required_trusted_link_corrections=manifest),
                         {}, {}, {'rows': [researched()]})


def test_research_rejected_link_references_require_applied_corrections_even_without_manifest():
    registry, corrections = trusted_link_correction_fixture()
    entry = researched()
    entry['existing_persona_search'] = {'rejected_trusted_link_corrections': ['link_a_x']}
    with pytest.raises(ValueError, match='required trusted link correction'):
        resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [entry]})
    ledger = resolve_accounts(BASELINE, REVIEW, registry, {}, {'rows': [entry]}, trusted_link_corrections=[corrections])
    assert ledger['resolutions'][0]['outcome'] == 'new_persona'


def test_review_and_research_correction_requirements_cannot_disagree():
    registry, corrections, manifest = required_corrections_fixture()
    review = dict(REVIEW, required_trusted_link_corrections=manifest)
    research = {'rows': [researched()], 'required_trusted_link_corrections':
                [dict(manifest[0], correction_sha256='0' * 64)]}
    with pytest.raises(ValueError, match='conflicting required trusted link correction'):
        resolve_accounts(BASELINE, review, registry, {}, research, trusted_link_corrections=[corrections])


REAL_EVIDENCE = Path(__file__).resolve().parents[1] / 'docs/evidence/creator-registry-review-2026-09-19'
REAL_LEDGER = Path(__file__).resolve().parents[1] / 'data/registry/identity_resolutions.json'


def test_linked_production_batch_has_complete_selected_evidence_and_no_group_leak():
    from collections import Counter
    review = json.loads((REAL_EVIDENCE / 'review_bundle.json').read_text(encoding='utf-8'))
    research = json.loads((REAL_EVIDENCE / 'identity_research_linked.json').read_text(encoding='utf-8'))
    ledger = json.loads(REAL_LEDGER.read_text(encoding='utf-8'))
    platforms = {'youtube', 'tiktok', 'website', 'instagram', 'facebook', 'ganknow'}
    selected = {r['discovery_id']: r for r in review['rows'] if r['eligibility'] == 'vtuber' and r['platform'] in platforms}
    assert len(selected) == 116
    assert Counter(r['platform'] for r in selected.values()) == {'youtube': 25, 'tiktok': 58, 'website': 17, 'instagram': 7, 'facebook': 6, 'ganknow': 3}
    assert {r['discovery_id'] for r in research['rows']} == set(selected)
    resolved = {r['discovery_id']: r for r in ledger['resolutions']}
    assert set(selected) <= set(resolved)
    assert not ledger['unresolved'] and not ledger['conflicts']
    assert 'candidate_e75fe4be2e942a6f1d0d' not in resolved
    assert review['eligibility_counts']['vtuber'] == 392
    assert review['eligibility_counts']['exclude_virtual_group'] == 3
    for row in research['rows']:
        assert row['evidence'] and row['reviewer']
        if row.get('no_existing_persona_match'):
            assert row['existing_persona_search']['corpora']
            assert row['existing_persona_search']['official_urls_checked']
            assert row['existing_persona_search']['result']


def test_every_linked_youtube_resolution_agrees_with_api_confirmed_video_or_channel_owner():
    import re
    review = json.loads((REAL_EVIDENCE / 'review_bundle.json').read_text(encoding='utf-8'))
    research = {r['discovery_id']: r for r in json.loads((REAL_EVIDENCE / 'identity_research_linked.json').read_text(encoding='utf-8'))['rows']}
    resolved = {r['discovery_id']: r for r in json.loads(REAL_LEDGER.read_text(encoding='utf-8'))['resolutions']}
    selected = [r for r in review['rows'] if r['platform'] == 'youtube' and r['eligibility'] == 'vtuber']
    assert len(selected) == 25
    for row in selected:
        evidence = [e for e in research[row['discovery_id']]['evidence'] if e['source_kind'] == 'youtube_api']
        assert evidence
        target = resolved[row['discovery_id']]
        assert re.fullmatch(r'UC[A-Za-z0-9_-]{22}', target['platform_id'])
        assert {e['owner_channel_id'] for e in evidence} == {target['platform_id']}
        assert {e['owner_canonical_url'] for e in evidence} == {'https://www.youtube.com/channel/' + target['platform_id']}
        if '/shorts/' in row['url'] or 'watch?v=' in row['url']:
            assert any(e['source_resource'].startswith('video:') for e in evidence)
    assert resolved['candidate_4ad08d3510b0052de1c8']['canonical_name'].startswith('Derya')
    assert resolved['candidate_4ad08d3510b0052de1c8']['platform_id'] == 'UCLMlKgN_f39Ex0pFZ4e5oUQ'
    assert resolved['candidate_b297c147542c164a05a3']['canonical_name'] == 'CzarBooHan'
    assert resolved['candidate_b297c147542c164a05a3']['platform_id'] == 'UCiuLi0DkmZQAH4fy_XhFUuA'


def test_real_client_personas_remain_distinct_from_nyeeeon_with_retained_corrections():
    ledger = json.loads(REAL_LEDGER.read_text(encoding='utf-8'))
    rows = {r['discovery_id']: r for r in ledger['resolutions']}
    clients = [rows[did] for did in ('candidate_5d85ad1e31dc7fd520a9', 'candidate_d4ffc2fcb4bd1133ae5a')]
    assert len({r['persona_id'] for r in clients}) == 2
    assert all(r['persona_id'] != 'vtuber_nyeeeon' for r in clients)
    audit = ledger['trusted_link_corrections_applied']
    assert {a['original_account']['handle'] for a in audit} == {'scythringe', 'reiquasar0', 'tpastry', 'BlueMage_VT', 'zerobusterxz', 'theclumsynoob'}
    assert all(a['correction']['disposition'] == 'reject_identity_link' for a in audit)
    assert 'link_61b87c391961a5735fad' not in {a['original_link']['id'] for a in audit}
    assert all('VTUBER CHILD' in a['correction']['summary'] for a in audit)


def test_production_inputs_pin_all_six_reviewed_corrections():
    from scripts.resolve_creator_identities import _record_sha256
    corrections = json.loads((REAL_EVIDENCE / 'trusted_link_corrections.json').read_text(encoding='utf-8'))
    expected = sorted(({'link_id': r['link_id'], 'correction_sha256': _record_sha256(r)}
                       for r in corrections['corrections']), key=lambda r: r['link_id'])
    assert len(expected) == 6
    for path in [REAL_EVIDENCE / 'review_bundle.json', REAL_EVIDENCE / 'identity_research_linked.json', REAL_LEDGER]:
        assert json.loads(path.read_text(encoding='utf-8'))['required_trusted_link_corrections'] == expected


@pytest.mark.parametrize('supplied', ['omitted', 'partial', 'complete'])
def test_merge_replay_keeps_requirements_from_prior_ledger(tmp_path, capsys, supplied):
    args, path, corrections, _ = required_correction_cli(tmp_path, 'review')
    output = tmp_path / 'ledger.json'
    assert main(args + ['--trusted-link-corrections', str(path), '--output', str(output)]) == 0
    original = output.read_bytes()
    review_path = tmp_path / 'review-bundle.json'
    review = json.loads(review_path.read_text(encoding='utf-8'))
    del review['required_trusted_link_corrections']
    review_path.write_text(json.dumps(review), encoding='utf-8')
    if supplied != 'omitted':
        if supplied == 'partial':
            corrections['corrections'] = corrections['corrections'][:1]
            path.write_text(json.dumps(corrections), encoding='utf-8')
        args += ['--trusted-link-corrections', str(path)]
    capsys.readouterr()
    status = main(args + ['--merge-existing', str(output), '--output', str(output)])
    assert status == (0 if supplied == 'complete' else 1)
    if supplied != 'complete':
        captured = capsys.readouterr()
        assert 'missing required trusted link corrections' in json.loads(captured.err)['error']
        assert captured.out == ''
    assert output.read_bytes() == original


def test_additional_valid_correction_can_extend_a_required_set():
    registry, corrections, manifest = required_corrections_fixture()
    review = dict(REVIEW, required_trusted_link_corrections=manifest[:1])
    ledger = resolve_accounts(BASELINE, review, registry, {}, {'rows': [researched()]},
                              trusted_link_corrections=[corrections])
    assert len(ledger['trusted_link_corrections_applied']) == 2
    assert ledger['required_trusted_link_corrections'] == manifest[:1]
