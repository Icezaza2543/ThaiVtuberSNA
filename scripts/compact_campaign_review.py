"""Compact existing public title signals into human-review packs; no network."""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog

BASE=Path('scratch/expanded-v1-campaign/expanded-v1/downtime-2026-09-10')
REDEBUT=re.compile(r'(?<![a-z])re[\s-]?debut\b|รีเดบิว|เดบิวต์ใหม่|再デビュー',re.I)
DEBUT=re.compile(r'(?<![a-z])debut\b|เดบิว|初配信|初放送|デビュー',re.I)
MODEL=re.compile(r'model\s*(?:reveal|debut|change)|(?:new|3d|live2d)\s*(?:model|debut)|เปิดตัวโมเดล|โมเดลใหม่|新モデル|新衣装|ชุดใหม่|new\s*outfit',re.I)
CONTEXT=[('pre_debut_or_test',r'pre[\s-]?debut|ก่อนเดบิว|ก่อนเปิดตัว|\btest\b|เทส'),
         ('anniversary_or_retrospective',r'anniversary|ครบรอบ|ย้อนหลัง|周年|ย้อนดู'),
         ('possible_other_person_or_clip',r'reaction|react\b|\bclip\b|คลิป|ดูเดบิว|ดูเปิดตัว|凸待ち'),
         ('announcement_not_event',r'teaser|trailer|ประกาศ|นับถอยหลัง|coming\s*soon|告知')]
ROLE_PATTERNS={'PNGTuber':r'png\s*tuber','singer':r'v[ -]?singer|virtual\s*singer',
               'artist':r'v[ -]?artist|virtual\s*artist|illustrator|นักวาด|คนวาด|イラスト|วาดโมเดล',
               'rigger':r'v[ -]?rigger|rigging|rigger|คนริก|ริกเกอร์',
               'modeler':r'modell?er|モデリング', 'Live2D_unspecified':r'live\s*2d'}


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def classify(row):
    title=row['title'];flags=[name for name,pattern in CONTEXT if re.search(pattern,title,re.I)]
    if REDEBUT.search(title): typ='redebut_candidate';score=100
    elif MODEL.search(title):typ='model_change_candidate';score=90
    elif DEBUT.search(title):typ='identity_start_candidate';score=95
    elif re.search('เปิดตัว',title):typ='identity_start_candidate';score=60;flags.append('ambiguous_reveal_subject')
    else:typ='weak_virtual_terminology';score=10;flags.append('no_explicit_identity_event')
    if 'pre_debut_or_test' in flags: score-=55
    if 'anniversary_or_retrospective' in flags:score-=50
    if 'possible_other_person_or_clip' in flags:score-=40
    if 'announcement_not_event' in flags:score-=30
    if not row['published_at']:score-=20;flags.append('missing_publication_date')
    flags.append('publication_date_is_not_verified_identity_date')
    return {**row,'candidate_type':typ,'review_score':score,'uncertainty_flags':flags}


def order(row):return (-row['review_score'],row['published_at'] or '9999',row['video_id'])


def csv_out(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k) for k in fields})


def build(base=BASE):
    raw=read(base/'identity_review_queue.csv');priority=read(base/'identity_priority_review.csv');role_raw=read(base/'role_review_queue.csv')
    labels={r['channel_id']:r['name'] for r in CreatorCatalog.from_path(CREATOR_REGISTRY_PATH).youtube_rows()}
    out=base/'human-review-v1';out.mkdir(exist_ok=True)
    grouped=defaultdict(dict)
    for row in raw:grouped[row['channel_id']][row['video_id']]=classify(row)
    packs=[];chosen_rows=[]
    for cid,by_video in sorted(grouped.items()):
        ranked=sorted(by_video.values(),key=order)
        strong=[r for r in ranked if r['candidate_type']!='weak_virtual_terminology']
        selected=[]
        # Preserve different event hypotheses; fill remaining slots by evidence rank.
        for row in strong:
            if row['candidate_type'] not in {r['candidate_type'] for r in selected}:selected.append(row)
        for row in strong:
            if len(selected)>=3:break
            if row not in selected:selected.append(row)
        selected=sorted(selected,key=order)[:3] if selected else ranked[:1]
        flags=['title_only_not_identity_verification']
        if sum(r['candidate_type']=='identity_start_candidate' for r in strong)>1:flags.append('multiple_possible_starts_require_continuity_review')
        if len({r['candidate_type'] for r in strong})>1:flags.append('debut_redebut_model_events_must_not_be_merged')
        if any(r['review_score']<50 for r in selected):flags.append('contextual_or_weak_evidence')
        pack=dict(channel_id=cid,entity=labels.get(cid,cid),review_status='UNREVIEWED',raw_signal_count=len(by_video),
                  review_tier='identity_event_review' if strong else 'weak_context_only',
                  selected_candidates=selected,signal_type_counts=dict(Counter(r['candidate_type'] for r in ranked)),
                  other_supporting_signals=[{k:r[k] for k in ('video_id','title','published_at','matched_signal','candidate_type')} for r in ranked if r not in selected][:3],
                  uncertainty_flags=flags)
        packs.append(pack)
        for row in selected:
            chosen_rows.append({**row,'entity':pack['entity'],'review_tier':pack['review_tier'],
                'other_supporting_signals':pack['other_supporting_signals'],'group_flags':flags,'raw_signal_count':len(by_video)})
    packs.sort(key=lambda p:(p['review_tier']=='weak_context_only',-p['selected_candidates'][0]['review_score'],p['channel_id']))
    chosen_rows.sort(key=lambda r:(r['review_tier']=='weak_context_only',*order(r),r['channel_id']))
    roles=defaultdict(dict)
    for row in role_raw:roles[row['channel_id']][row['video_id']]=row
    role_packs=[]
    for cid,by_video in sorted(roles.items()):
        evidence=list(by_video.values()); by_role=defaultdict(list)
        for row in evidence:
            matches=[role for role,pattern in ROLE_PATTERNS.items() if re.search(pattern,row['title'],re.I)]
            if len(matches)>1 and 'Live2D_unspecified' in matches:matches.remove('Live2D_unspecified')
            for role in matches:by_role[role].append(row)
        supported={role:sorted(rows,key=lambda r:(r['published_at'] or '9999',r['video_id']))[:2] for role,rows in by_role.items()}
        best=sorted(evidence,key=lambda r:(-sum(bool(re.search(p,r['title'],re.I)) for p in ROLE_PATTERNS.values()),r['published_at'] or '9999',r['video_id']))[0]
        role_packs.append(dict(channel_id=cid,entity=labels.get(cid,cid),review_status='UNREVIEWED',
            candidate_type='role_or_credit_attribution_review',role_hypotheses=sorted(by_role),strongest_title=best['title'],
            video_id=best['video_id'],published_at=best['published_at'],matched_evidence=best['matched_signal'],
            raw_signal_count=len(evidence),role_signal_counts={k:len(v) for k,v in by_role.items()},
            other_supporting_signals=supported,
            uncertainty_flags=['uploader_may_not_be_credited_artist_or_subject','channel_group_not_verified_persona',
                               'roles_are_separate_hypotheses_not_assignments','virtual_creator_status_not_inferred']))
    fields=['channel_id','entity','review_tier','title','video_id','published_at','matched_signal','candidate_type','review_score','uncertainty_flags','group_flags','other_supporting_signals','raw_signal_count']
    csv_out(out/'identity_shortlist.csv',[r for r in chosen_rows if r['review_tier']=='identity_event_review'],fields)
    channel_rows=[]
    for pack in packs:
        if pack['review_tier']!='identity_event_review':continue
        best=pack['selected_candidates'][0]
        channel_rows.append(dict(channel_id=pack['channel_id'],entity=pack['entity'],strongest_title=best['title'],
            video_id=best['video_id'],published_at=best['published_at'],matched_evidence=best['matched_signal'],
            candidate_type=best['candidate_type'],review_score=best['review_score'],review_status='UNREVIEWED',
            other_supporting_signals=[{k:r[k] for k in ('title','video_id','published_at','candidate_type','matched_signal')} for r in pack['selected_candidates'][1:]],
            uncertainty_flags=pack['uncertainty_flags']+best['uncertainty_flags'],raw_signal_count=pack['raw_signal_count']))
    csv_out(out/'identity_channel_review.csv',channel_rows,list(channel_rows[0]))
    csv_out(out/'weak_context_appendix.csv',[r for r in chosen_rows if r['review_tier']=='weak_context_only'],fields)
    ranked_priority=sorted((classify(r) for r in priority),key=order)
    for i,row in enumerate(ranked_priority,1):row['rank']=i
    csv_out(out/'priority_4031_ranked.csv',ranked_priority,['rank','channel_id','title','video_id','published_at','candidate_type','review_score','matched_signal','uncertainty_flags'])
    csv_out(out/'role_entity_review.csv',role_packs,list(role_packs[0]))
    for name,obj in [('identity_groups.json',packs),('role_entity_groups.json',role_packs)]:
        (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=dict(raw_identity_signals=len(raw),identity_channel_groups=len(packs),priority_candidates_ranked=len(ranked_priority),
        primary_review_channels=sum(p['review_tier']=='identity_event_review' for p in packs),
        primary_review_candidates=sum(r['review_tier']=='identity_event_review' for r in chosen_rows),
        weak_only_channels=sum(p['review_tier']=='weak_context_only' for p in packs),
        max_identity_candidates_per_channel=max(len(p['selected_candidates']) for p in packs),
        selected_type_counts=dict(Counter(r['candidate_type'] for r in chosen_rows)),
        raw_role_signals=len(role_raw),role_entity_groups=len(role_packs),
        role_entity_counts=dict(Counter(role for p in role_packs for role in p['role_hypotheses'])),
        caveat='Stable uploader channels group evidence only; credited third parties are unresolved. No identity date or role assigned.')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'START_HERE.md').write_text('''# Human review packs

Start with **identity_channel_review.csv**: one decision group per channel, strongest title first, at most two additional identity hypotheses. Rows are ranked by title specificity, with pre-debut/test, anniversary, announcement and reaction/clip contexts penalized. Scores prioritize reading; they are not probabilities or verified identity confidence. Publication dates are video dates only.

Use **role_entity_review.csv** for one group per stable uploader channel. Multiple role hypotheses stay separate. A title may credit another creator: no cross-channel person merge, role assignment, or VTuber label is inferred. Live2D alone has an unspecified role.

The weak-only groups are deferred in **weak_context_appendix.csv**. **identity_shortlist.csv** exposes the selected 1–3 evidence videos per channel. **priority_4031_ranked.csv** ranks every existing priority row, including low-context evidence. JSON group files provide additional supporting signals and uncertainty flags. The original raw queues remain intact one directory above.

Every group is UNREVIEWED. Verify who the title refers to, whether it describes an actual identity event versus a model change/announcement/retrospective, and persona continuity before assigning any identity dates. No external requests were used to produce these packs.
''',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return summary


if __name__=='__main__':build()
