"""Build a conservative reviewed VTuber eligibility layer for Surface Analytics."""
import csv, json, re
from collections import Counter
from pathlib import Path
REVIEW_DIR=Path("docs/evidence/expanded-v1/public-review-2026-09-10")
IDENTITY_FILES=[REVIEW_DIR/f"identity_batch_{i:03d}.json" for i in range(1,7)]
ROLE_FILE=REVIEW_DIR/"role_batch_001.json"
POSITIVE_EVENTS={"identity_start","redebut","model_change"}; OK_REVIEW={"VERIFIED","SUPPORTED"}
EXPLICIT_VIRTUAL=re.compile(r"\bvtuber\b|virtual|วีทู[บป]เบอร์|pngtuber|live2d|\b3d\b|v-artist|v-singer|vsinger|\bpersona\b|fictional|model[- ]?(?:show|reveal|parent|creator|credit)|character\s*design|self-introduc",re.I)
KNOWN_VIRTUAL_ROSTER=re.compile(r"\bARP\b|arproject|algorhythm|pixela|lumina|euphora|virtual7|virtualzeven|genesis project|flora project|parabellum|astars|amakara|chrono prince|v\.w\.y|WISLIVE|Autumnia|V-Janai|VJN|AcastledProject|Majinova|Vniverse|Kikorin|IDYLLIC|Chark Project|DPX|ALF|HZ",re.I)
ORG_LABEL=re.compile(r"\bproject\b|\bofficial\b|\bstudio\b|\bproduction\b|\bagency\b|\bassociation\b|\bnetwork\b|\bgroup\b|\bcompany\b",re.I)

def explicit_non_persona(row):
    text=f"{row.get('review_reason','')} {row.get('evidence_summary','')}".lower()
    return (("project channel hosts" in text and "cannot assign" in text and "project entity" in text)
            or ("project account announces" in text and "neither uploader identity" in text))

def classify_channel(identity_row,role_row=None):
    ip=identity_row.get("review_status") in OK_REVIEW and identity_row.get("event_type") in POSITIVE_EVENTS
    rp=bool(role_row) and role_row.get("review_status") in OK_REVIEW and role_row.get("entity_type") in {"virtual_creator","both"}
    neg=explicit_non_persona(identity_row)
    text=" ".join(str(identity_row.get(k,"")) for k in ("source_title","evidence_summary","review_reason","persona_label"))
    explicit=bool(EXPLICIT_VIRTUAL.search(text))
    roster=bool(KNOWN_VIRTUAL_ROSTER.search(text)) and not bool(ORG_LABEL.search(identity_row.get("persona_label","")))
    if neg and (ip or rp): return "HOLD_CONFLICTING_ELIGIBILITY","CONFLICTING_POSITIVE_AND_NON_PERSONA_EVIDENCE"
    if neg:return "EXCLUDE_NON_PERSONA_ACCOUNT","REVIEWED_PROJECT_ACCOUNT_NOT_PERSONA"
    if rp:return "STRICT_VIRTUAL","REVIEWED_ROLE_ENTITY_VIRTUAL"
    if ip and (explicit or roster):return "STRICT_VIRTUAL",("IDENTITY_EVENT_WITH_EXPLICIT_VIRTUAL_SIGNAL" if explicit else "IDENTITY_EVENT_WITH_INDIVIDUAL_VIRTUAL_ROSTER_SIGNAL")
    if ip:return "PROVISIONAL_VIRTUAL","REVIEWED_PERSONA_EVENT_VIRTUAL_MEDIUM_NOT_SEPARATELY_CONFIRMED"
    return "HOLD_NEEDS_CHANNEL_REVIEW","NO_AFFIRMATIVE_CHANNEL_LEVEL_VIRTUAL_EVIDENCE_IN_CURRENT_REVIEW"

def apply_resolutions(rows, resolutions):
    """Apply complete channel reviews without modifying identity evidence."""
    targets={r['channel_id'] for r in rows if r['eligibility_status']=='PROVISIONAL_VIRTUAL'}
    by_id={r['channel_id']:r for r in resolutions}
    if len(by_id)!=len(resolutions) or set(by_id)!=targets:
        raise ValueError('Resolution must cover each provisional channel exactly once')
    allowed={'STRICT_VIRTUAL','HOLD_NEEDS_CHANNEL_REVIEW','EXCLUDE_NON_PERSONA_ACCOUNT','EXCLUDE_NON_VIRTUAL_CREATOR'}
    for resolution in resolutions:
        if resolution.get('old_status')!='PROVISIONAL_VIRTUAL' or resolution.get('new_status') not in allowed:
            raise ValueError('Invalid channel resolution transition')
        if resolution.get('conflict_flag') and resolution['new_status']=='STRICT_VIRTUAL':
            raise ValueError('Conflicting evidence cannot be promoted into strict cohort')
    for row in rows:
        if row['channel_id'] not in by_id:continue
        resolution=by_id[row['channel_id']]
        row.update(eligibility_status=resolution['new_status'],strict_surface=resolution['new_status']=='STRICT_VIRTUAL',reason_code='PUBLIC_CHANNEL_RESOLUTION_V1',channel_review=resolution)

def build(review_dir=REVIEW_DIR):
    review_dir=Path(review_dir)
    identity=[]
    for path in [review_dir/f'identity_batch_{i:03d}.json' for i in range(1,7)]:
        for row in json.loads(path.read_text(encoding="utf-8")):identity.append({**row,"_review_source":path.as_posix()})
    if len(identity)!=408 or len({r["channel_id"] for r in identity})!=408:raise RuntimeError("Expected 408 unique reviewed channels")
    roles={r["channel_id"]:r for r in json.loads((review_dir/'role_batch_001.json').read_text(encoding="utf-8"))}
    rows=[]
    for row in identity:
        role=roles.get(row["channel_id"]);status,reason=classify_channel(row,role)
        rows.append({"channel_id":row["channel_id"],"label":row.get("persona_label"),"eligibility_status":status,"reason_code":reason,"strict_surface":status=="STRICT_VIRTUAL","identity_review_status":row.get("review_status"),"identity_event_type":row.get("event_type"),"identity_event_date":row.get("event_date"),"identity_source_url":row.get("source_url"),"identity_source_title":row.get("source_title"),"identity_review_reason":row.get("review_reason"),"role_review_status":role.get("review_status") if role else None,"role_entity_type":role.get("entity_type") if role else None,"role_roles":role.get("roles",[]) if role else [],"role_source_url":role.get("source_url") if role else None,"source_review_file":row["_review_source"]})
    rows.sort(key=lambda r:r["channel_id"]);counts={}
    for row in rows:counts[row["eligibility_status"]]=counts.get(row["eligibility_status"],0)+1
    expected={"STRICT_VIRTUAL":229,"PROVISIONAL_VIRTUAL":45,"EXCLUDE_NON_PERSONA_ACCOUNT":2,"HOLD_NEEDS_CHANNEL_REVIEW":132}
    if counts!=expected:raise RuntimeError(f"Eligibility counts changed: {counts}")
    resolutions=json.loads((review_dir/'provisional_resolution_v1.json').read_text(encoding='utf-8'))['rows']
    apply_resolutions(rows,resolutions)
    counts=dict(Counter(r['eligibility_status'] for r in rows))
    payload={
        'schema_version':'reviewed-channel-eligibility-v1',
        'evidence_scope':'408 identity-reviewed channel groups from public-review-2026-09-10; role_batch_001 is supplementary evidence; provisional_resolution_v1 contains channel-level public reviews dated 2026-09-19.',
        'policy':{
            'strict_virtual':'Reviewed virtual role or identity evidence, with explicit channel-level resolutions taking precedence for the 45 formerly provisional channels.',
            'provisional_virtual':'Intermediate legacy classification only; all 45 require a complete resolution before export.',
            'exclude_non_persona_account':'Affirmative evidence identifies the uploader as a project/company/clip/production/host account rather than the individual persona.',
            'exclude_non_virtual_creator':'Affirmative evidence of a non-virtual creator without relevant virtual-persona activity; art/rigging/singing roles alone do not justify exclusion.',
            'hold':'Insufficient or contradictory channel-level evidence. HOLD does not mean non-VTuber and is outside the default Surface cohort.',
            'rejected_event_rule':'REJECTED_AS_IDENTITY_EVENT rejects only that proposed event and never by itself excludes the channel.',
        },
        'status_counts':counts,'rows':rows,
    }
    (review_dir/"channel_eligibility_v1.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=["channel_id","label","eligibility_status","reason_code","strict_surface","identity_review_status","identity_event_type","identity_event_date","identity_source_url","identity_source_title","role_review_status","role_entity_type","role_roles","channel_review"]
    with (review_dir/"channel_eligibility_v1.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:w.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k) for k in fields})
    strict=[r for r in rows if r["eligibility_status"]=="STRICT_VIRTUAL"];prov=[r for r in rows if r["eligibility_status"]=="PROVISIONAL_VIRTUAL"];ex=[r for r in rows if r["eligibility_status"].startswith('EXCLUDE_')];hold=[r for r in rows if r["eligibility_status"].startswith('HOLD_')]
    cohort={"schema_version":"surface-virtual-cohort-v1","default_surface_policy":"STRICT_VIRTUAL_ONLY","reviewed_reference_channels":408,"strict_virtual_count":len(strict),"provisional_virtual_count":len(prov),"explicitly_excluded_non_persona_count":sum(r["eligibility_status"]=="EXCLUDE_NON_PERSONA_ACCOUNT" for r in ex),"explicitly_excluded_non_virtual_count":sum(r["eligibility_status"]=="EXCLUDE_NON_VIRTUAL_CREATOR" for r in ex),"hold_count":len(hold),"strict_channel_ids":[r["channel_id"] for r in strict],"provisional_channel_ids":[r["channel_id"] for r in prov],"explicit_exclusions":[{k:r[k] for k in ("channel_id","label","reason_code","identity_source_url","identity_review_reason")} for r in ex]}
    (review_dir/"surface_virtual_cohort_v1.json").write_text(json.dumps(cohort,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return counts
if __name__=="__main__":print(json.dumps(build(),ensure_ascii=False))
