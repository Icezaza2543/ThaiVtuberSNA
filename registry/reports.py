"""Date-qualified counts; account inventory and verified personas use separate denominators."""

from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import hashlib
import json

from .store import PLATFORMS, payload, rows, validate

STATES = ('active_streaming', 'active_posting', 'pre_debut', 'hiatus', 'graduated',
          'no_recent_evidence', 'unknown', 'conflict_needs_review')
STATE_EVENTS = {'debut', 'redebut', 'return', 'hiatus', 'graduation'}


def temporal_summary(db, as_of, active_days=90):
    cutoff = date.fromisoformat(as_of)
    if active_days <= 0:
        raise ValueError('active_days must be positive')
    validate(db)
    personas = {r['id']: r for r in rows(db, 'personas') if r['review_status'] == 'verified'}
    accounts = {r['id']: r for r in rows(db, 'accounts')}
    events, observations = defaultdict(list), defaultdict(list)
    verified_events = [e for e in rows(db, 'lifecycle_events') if e['review_status'] == 'verified' and e['persona_id'] in personas]
    for event in verified_events:
        if event['date_precision'] == 'day':
            events[event['persona_id']].append(event)
    for observation in rows(db, 'activity_observations'):
        if observation['review_status'] == 'verified' and observation['activity_date'] <= as_of:
            observations[observation['persona_id']].append(observation)
    states = {state: 0 for state in STATES}
    persona_states = {}
    for pid in personas:
        occurred = [e for e in events[pid] if e['event_date'] <= as_of and e['event_type'] in STATE_EVENTS]
        latest_date = max((e['event_date'] for e in occurred), default=None)
        latest = [e for e in occurred if e['event_date'] == latest_date]
        event_type = latest[0]['event_type'] if latest else None
        activity = observations[pid]
        recent = [a for a in activity if date.fromisoformat(a['activity_date']) >= cutoff - timedelta(days=active_days - 1)]
        state = 'unknown'
        if len({e['event_type'] for e in latest}) > 1:
            state = 'conflict_needs_review'
        elif event_type == 'graduation':
            # Publication alone does not silently reverse an announced graduation.
            state = 'conflict_needs_review' if any(a['activity_date'] > latest_date for a in activity) else 'graduated'
        elif event_type == 'hiatus':
            state = 'conflict_needs_review' if any(a['activity_date'] > latest_date for a in activity) else 'hiatus'
        elif recent:
            state = 'active_streaming' if any(a['activity_type'] == 'live' for a in recent) else 'active_posting'
        elif activity:
            state = 'no_recent_evidence'
        elif not occurred and any(e['event_type'] == 'debut' and e['event_date'] > as_of for e in events[pid]):
            state = 'pre_debut'
        states[state] += 1
        persona_states[pid] = state
    platform_personas = {p: set() for p in PLATFORMS}
    eligible_links = []
    for link in rows(db, 'account_links'):
        if link['review_status'] == 'verified' and link['persona_id'] in personas and \
                link['valid_from'] and link['valid_to'] and link['valid_from'] <= as_of <= link['valid_to']:
            platform_personas[accounts[link['account_id']]['platform']].add(link['persona_id'])
            eligible_links.append(link)
    memberships = Counter()
    for pid in personas:
        memberships[str(sum(pid in value for value in platform_personas.values()))] += 1
    yearly = defaultdict(Counter)
    event_personas = defaultdict(set)
    for event in verified_events:
        if event['event_date'] and event['event_date'][:4] <= as_of[:4]:
            # Only include dates certainly on/before cutoff. Coarse dates remain separate.
            if event['date_precision'] == 'day' and event['event_date'] <= as_of:
                yearly[event['event_date'][:4]][event['event_type']] += 1
                event_personas[event['event_type']].add(event['persona_id'])
    discoveries = defaultdict(set)
    runs = {r['id']: r for r in rows(db, 'discovery_runs')}
    for hit in rows(db, 'discovery_hits'):
        run = runs[hit['run_id']]
        discoveries[run['platform'] + ':' + run['method']].add(hit['account_id'] or hit['candidate_id'])
    claims = rows(db, 'legacy_claims')
    source_counts = Counter()
    for claim in claims:
        source_counts.update(set(filter(None, (s.strip() for s in claim['source_names'].split(';')))))
    return {
        'as_of': as_of, 'active_window_days': active_days,
        'count_semantics': 'Inventory uses all recorded discoveries; lifecycle uses dated reviewed evidence at cutoff. Retrospective knowledge, not historical database availability.',
        'inventory': {'accounts': len(accounts), 'accounts_by_platform': {p: sum(a['platform'] == p for a in accounts.values()) for p in PLATFORMS},
                      'candidates': db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0],
                      'candidate_review': dict(Counter(r['review_status'] for r in rows(db, 'candidates'))),
                      'verified_personas': len(personas)},
        'lifecycle': states, 'persona_states': persona_states,
        'dated_verified_personas_by_platform': {p: len(v) for p, v in platform_personas.items()},
        'persona_platform_count_distribution': dict(sorted(memberships.items())),
        'lifecycle_events_by_year': {y: dict(c) for y, c in sorted(yearly.items())},
        'unique_personas_by_event': {kind: len(pids) for kind, pids in sorted(event_personas.items())},
        'events_without_exact_day': sum(e['date_precision'] != 'day' for e in verified_events),
        'verified_public_continuity_links': sum(r['review_status'] == 'verified' for r in rows(db, 'continuity_links')),
        'discovery_unique_leads_by_method': {k: len(v) for k, v in sorted(discoveries.items())},
        'legacy_claims': {'accounts': len(claims), 'activity': dict(Counter(c['source_activity'] for c in claims)),
                          'agency': dict(Counter(c['source_agency'] for c in claims)),
                          'source_mentions_nonexclusive': dict(source_counts)},
        'open_review_reasons': dict(Counter(r['reason'] for r in rows(db, 'review_queue') if r['status'] == 'open')),
        'eligible_account_links': eligible_links,
    }


def write_csv(path, fields, records):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        for row in records:
            # Keep spreadsheet exports from interpreting creator-controlled text as formulas.
            writer.writerow({key: ("'" + str(value) if str(value).startswith(('=', '+', '-', '@', '\t', '\r')) else value)
                             for key, value in row.items()})


def write_report(db, output, as_of, active_days=90):
    summary = temporal_summary(db, as_of, active_days)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# สถานะทะเบียน ThaiVirtualCreatorRegistry', '', f'วันที่อ้างอิงกิจกรรม: {as_of} · หน้าต่างกิจกรรม {active_days} วัน', '',
             'จำนวน inventory รวมการค้นพบที่บันทึกทั้งหมด ส่วน lifecycle ใช้หลักฐานลงวันที่ที่ผ่าน review แล้ว', '',
             '| แพลตฟอร์ม | บัญชีในทะเบียน | Persona ยืนยันและมีหลักฐานการใช้บัญชี ณ วันอ้างอิง |',
             '|---|---:|---:|']
    for p in PLATFORMS:
        lines.append(f'| {p} | {summary["inventory"]["accounts_by_platform"][p]} | {summary["dated_verified_personas_by_platform"][p]} |')
    lines += ['', 'ดาวน์โหลด [บัญชี TikTok พร้อมรหัสและหลักฐาน](tiktok_accounts.csv) · '
              '[TikTok ที่ยืนยัน persona และการใช้บัญชี ณ วันอ้างอิง](verified_tiktok.csv)', '',
              '`tiktok_accounts.csv` นับบัญชี ส่วน `verified_tiktok.csv` มีหนึ่งแถวต่อคู่ persona/บัญชี '
              'จึงอาจมีหลายแถวต่อ persona ได้ คอลัมน์ `platform_id` ต้องนำเข้าเป็นข้อความเมื่อเปิดด้วยสเปรดชีต']
    lines += ['', f'Persona ที่ผ่าน review: {summary["inventory"]["verified_personas"]} · Candidates: {summary["inventory"]["candidates"]}', '',
              '## สถานะที่ยืนยันได้', '', '| สถานะ | Persona |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in summary['lifecycle'].items()]
    lines += ['', '## สถานะที่สืบทอดจากทะเบียนเดิม', '',
              'ค่าต่อไปนี้เป็นป้ายกำกับในแหล่งเดิม ยังไม่ได้ตรวจซ้ำตามเกณฑ์ข้ามแพลตฟอร์มของ repo นี้', '',
              '| ป้ายกำกับเดิม | บัญชี |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in sorted(summary['legacy_claims']['activity'].items())]
    lines += ['', '## คิวตรวจ', '', '| เหตุผล | รายการ |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in sorted(summary['open_review_reasons'].items())]
    lines += ['', '### Candidate review', '', '| สถานะ candidate | รายการ |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in sorted(summary['inventory']['candidate_review'].items())]
    lines += ['', 'คิวปัญหาของบัญชีและ candidate เป็นคนละหน่วย บัญชีหนึ่งมีหลายปัญหาได้', '',
              'ดู [candidates.csv](candidates.csv) หรือใช้ `python -m registry queue --platform tiktok`',
              'ดูหลักฐานของรายการด้วย `python -m registry inspect candidate CANDIDATE_ID`', '']
    lines += ['', 'ค่า 0 ในหมวดที่ยังไม่มี review หมายถึงยังไม่มีข้อมูลยืนยันในทะเบียน ไม่ได้หมายถึงไม่มีอยู่จริง', '',
              '## แหล่งที่ทะเบียนเดิมอ้างอิง', '', 'หนึ่งบัญชีอ้างอิงหลายแหล่งได้ จึงบวกเป็นจำนวนบัญชีรวมไม่ได้', '',
              '| แหล่ง | บัญชีที่อ้างถึง |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in sorted(summary['legacy_claims']['source_mentions_nonexclusive'].items(), key=lambda x: -x[1])]
    lines += ['', '## สังกัดตามป้ายกำกับเดิม', '', '| สังกัด | บัญชี |', '|---|---:|']
    lines += [f'| {s} | {n} |' for s, n in sorted(summary['legacy_claims']['agency'].items(), key=lambda x: -x[1])]
    lines += ['', '## ประวัติเหตุการณ์', '',
              f'ความต่อเนื่อง persona ที่มีประกาศยืนยัน: {summary["verified_public_continuity_links"]}',
              f'เหตุการณ์ยืนยันที่ยังไม่มีวันที่ระดับวัน: {summary["events_without_exact_day"]}', '',
              'ดู lifecycle events รายปีใน [summary.json](summary.json) และข้อมูลแถวใน [lifecycle_events.csv](lifecycle_events.csv)', '']
    (output / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    write_csv(output / 'accounts.csv', ['platform', 'platform_id', 'name', 'url'],
              ({k: a[k] for k in ['platform', 'platform_id', 'name', 'url']} for a in rows(db, 'accounts')))
    for table in ('personas', 'lifecycle_events', 'review_queue', 'candidates'):
        fields = [r['name'] for r in db.execute(f'PRAGMA table_info({table})')]
        write_csv(output / (table + '.csv'), fields, rows(db, table))
    evidence = {e['id']: e for e in rows(db, 'evidence')}
    personas = {p['id']: p for p in rows(db, 'personas')}
    links = defaultdict(list)
    for link in summary['eligible_account_links']:
        links[link['account_id']].append(link)
    for platform in ('tiktok', 'twitch'):
        inventory, verified = [], []
        for account in sorted(rows(db, 'accounts'), key=lambda a: (a['handle'] or '', a['id'])):
            if account['platform'] != platform:
                continue
            proof = evidence[account['evidence_id']]
            row = {k: account[k] for k in ('platform_id', 'id_namespace', 'handle', 'name', 'url')}
            row.update(account_id=account['id'], observed_at=proof['observed_at'],
                       account_evidence_url=proof['url'], as_of=as_of)
            pids = sorted({link['persona_id'] for link in links[account['id']]})
            inventory.append(dict(row, scope_review='verified' if pids else 'not_established_at_cutoff',
                                  persona_ids=';'.join(pids)))
            # Multiple evidence intervals for one pair do not create duplicate export rows.
            for pid in pids:
                link = next(l for l in links[account['id']] if l['persona_id'] == pid)
                persona = personas[pid]
                verified.append(dict(row, persona_id=pid, persona_name=persona['name'],
                                     thai_relation=persona['thai_relation'], format=persona['format'],
                                     persona_evidence_url=evidence[persona['evidence_id']]['url'],
                                     link_evidence_url=evidence[link['evidence_id']]['url'],
                                     reviewed_at=link['reviewed_at']))
        base_fields = ['account_id', 'platform_id', 'id_namespace', 'handle', 'name', 'url',
                       'observed_at', 'account_evidence_url', 'as_of']
        write_csv(output / f'{platform}_accounts.csv', base_fields + ['scope_review', 'persona_ids'], inventory)
        write_csv(output / f'verified_{platform}.csv', base_fields + ['persona_id', 'persona_name', 'thai_relation',
                  'format', 'persona_evidence_url', 'link_evidence_url', 'reviewed_at'], verified)
    return summary


def export_bundle(db, output, as_of):
    validate(db)
    if output.exists():
        raise ValueError('Snapshot directory already exists; choose a new version')
    summary = temporal_summary(db, as_of)
    output.mkdir(parents=True)
    registry_path = output / 'registry.json'
    registry_path.write_text(json.dumps(payload(db), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_report(db, output / 'reports', as_of)
    accounts = {a['id']: a for a in rows(db, 'accounts')}
    mapping = {}
    for link in summary['eligible_account_links']:
        account = accounts[link['account_id']]
        if account['platform'] == 'youtube':
            mapping.setdefault(account['platform_id'], (account, set()))[1].add(link['persona_id'])
    write_csv(output / 'approved_youtube.csv', ['channel_id', 'name', 'persona_ids', 'as_of'],
              ({'channel_id': cid, 'name': account['name'], 'persona_ids': ';'.join(sorted(pids)), 'as_of': as_of}
               for cid, (account, pids) in sorted(mapping.items())))
    manifest = {'schema_version': 1, 'as_of': as_of, 'files': {}}
    for file in sorted(output.rglob('*')):
        if file.is_file():
            manifest['files'][file.relative_to(output).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest
