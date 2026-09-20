"""Build cleaned Surface Analytics from public aggregate artifacts only.

No YouTube API, private workbook, viewer-level data, or live campaign state is touched.
The default cohort is STRICT_VIRTUAL from surface_virtual_cohort_v1.json.
"""
import csv, json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/"docs/evidence/expanded-v1/public-review-2026-09-10"
DOWNTIME=ROOT/"docs/evidence/expanded-v1/downtime-2026-09-10"
GRAPH=ROOT/"data/real/analytics/network_graph.json"
OUT=ROOT/"web/research/surface_analytics_v1.json"

def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def quantile(values,q):
    s=sorted(values)
    if not s:return None
    pos=(len(s)-1)*q;lo=int(pos);hi=min(len(s)-1,lo+1)
    return s[lo] if lo==hi else s[lo]+(s[hi]-s[lo])*(pos-lo)

def build():
    cohort=json.loads((REVIEW/"surface_virtual_cohort_v1.json").read_text(encoding="utf-8"))
    strict=set(cohort["strict_channel_ids"])
    coverage=[r for r in read_csv(DOWNTIME/"channel_coverage.csv") if r["channel_id"] in strict]
    yearly_rows=[r for r in read_csv(DOWNTIME/"channel_year_coverage.csv") if r["channel_id"] in strict]
    eligibility={r["channel_id"]:r for r in json.loads((REVIEW/"channel_eligibility_v1.json").read_text(encoding="utf-8"))["rows"]}
    graph=json.loads(GRAPH.read_text(encoding="utf-8"))
    if len(strict)!=229 or len(coverage)!=229:raise RuntimeError("Strict cohort inputs changed; review before rebuilding")

    vc=[int(r["video_count"] or 0) for r in coverage]
    years=defaultdict(lambda:{"videos":0,"channels":set()})
    for r in yearly_rows:
        y=int(r["year"]);years[y]["videos"]+=int(r["video_count"]);years[y]["channels"].add(r["channel_id"])
    nodes=[n for n in graph["nodes"] if n["id"] in strict]
    node_by={n["id"]:n for n in nodes}
    edges=[e for e in graph["edges"] if e["source"] in strict and e["target"] in strict]
    adj={cid:set() for cid in strict}
    for e in edges:adj[e["source"]].add(e["target"]);adj[e["target"]].add(e["source"])
    seen=set();components=[]
    for cid in strict:
        if cid in seen:continue
        stack=[cid];seen.add(cid);comp=[]
        while stack:
            cur=stack.pop();comp.append(cur)
            for nxt in adj[cur]:
                if nxt not in seen:seen.add(nxt);stack.append(nxt)
        components.append(comp)
    components.sort(key=len,reverse=True)
    event_years=defaultdict(lambda:{"identity_start":0,"redebut":0,"model_change":0})
    strict_rows=[eligibility[cid] for cid in strict]
    for r in strict_rows:
        if r.get("identity_event_date") and r.get("identity_event_type") in event_years[int(r["identity_event_date"][:4])]:
            event_years[int(r["identity_event_date"][:4])][r["identity_event_type"]]+=1
    dates=sorted([d for r in coverage for d in (r.get("oldest"),r.get("newest")) if d])
    weights=[int(e.get("shared_viewers",e.get("weight",0)) or 0) for e in edges]
    degree=sorted(({"channel_id":cid,"label":node_by.get(cid,{}).get("label",eligibility[cid].get("label",cid)),"degree":len(adj[cid]),"agency":node_by.get(cid,{}).get("agency")} for cid in strict),key=lambda r:(-r["degree"],r["label"]))
    identity_starts=[r for r in strict_rows if r.get("identity_event_type")=="identity_start" and r.get("identity_event_date")]
    payload={
      "schema_version":"surface-analytics-v1",
      "cohort":{"raw_reference_channels":1370,"reviewed_identity_channels":408,"strict_virtual_channels":229,"provisional_virtual_channels":45,"hold_channels":132,"excluded_non_persona_accounts":2,"default_policy":"STRICT_VIRTUAL_ONLY"},
      "content":{"source_as_of":"2026-09-10","catalog_channels":229,"catalog_videos":sum(vc),"exact_timestamp_videos":sum(int(r["exact_timestamps"] or 0) for r in coverage),"oldest_publication":dates[0],"newest_publication":dates[-1],"channels_with_video_at_or_before_2020":sum(r["at_or_before_2020"]=="True" for r in coverage),"catalog_status_counts":dict(__import__("collections").Counter(r["catalog_status"] for r in coverage)),"videos_per_channel":{"min":min(vc),"p25":quantile(vc,.25),"median":quantile(vc,.5),"mean":round(sum(vc)/len(vc),2),"p75":quantile(vc,.75),"p90":quantile(vc,.9),"max":max(vc)},"yearly":[{"year":y,"videos":v["videos"],"channels":len(v["channels"])} for y,v in sorted(years.items())]},
      "network":{"source_as_of":"2026-09-07","source_note":"Filtered public thresholded network snapshot; live private archive is newer.","minimum_shared_viewers":graph["metadata"]["min_relation_threshold"],"nodes":229,"edges":len(edges),"strong_edges":sum(int(e.get("strong_shared",0) or 0)>0 for e in edges),"isolated_nodes":sum(len(adj[cid])==0 for cid in strict),"connected_components":len(components),"largest_component_nodes":len(components[0]),"density":round(len(edges)/(229*228/2),6),"average_degree":round(2*len(edges)/229,4),"edge_shared_viewers":{"min":min(weights) if weights else 0,"median":quantile(weights,.5),"p75":quantile(weights,.75),"p90":quantile(weights,.9),"max":max(weights) if weights else 0},"top_degree":degree[:10]},
      "audience":{"clean_unique_pseudonyms":None,"clean_interactions":None,"status":"NOT_RECOMPUTED_WHILE_LIVE_PRIVATE_ARCHIVE_IS_MUTATING","note":"Exact strict-cohort audience totals require a stable private canonical rebuild; values are intentionally null."},
      "timeline":{"reviewed_identity_starts":len(identity_starts),"reviewed_redebuts":sum(r.get("identity_event_type")=="redebut" and bool(r.get("identity_event_date")) for r in strict_rows),"reviewed_model_changes":sum(r.get("identity_event_type")=="model_change" and bool(r.get("identity_event_date")) for r in strict_rows),"earliest_reviewed_identity_start":min(r["identity_event_date"] for r in identity_starts),"event_points_by_year":[{"year":y,**v} for y,v in sorted(event_years.items())]},
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return payload

if __name__=="__main__":print(json.dumps(build(),ensure_ascii=False,indent=2))
