"""Refresh bounded integrity statements from canonical local artifacts."""
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from analytics.research_integrity import reactivation_series
ROOT = Path(__file__).resolve().parents[1]

def refresh():
    events = pd.read_parquet(ROOT / 'data/industry/creator_status_events.parquet')
    tiers = events.evidence_tier.value_counts().to_dict()
    series = '; '.join(f"{r['year']}{' YTD' if r['partial_window'] else ''}: {r['accounts']}" for r in reactivation_series())
    block = '\n'.join(['<!-- source-integrity:start -->', '## Canonical source integrity', '', 'Ratio universe: numerator_scope=FROZEN_COHORT_193; denominator_scope=FROZEN_COHORT_193 unless a local table declares another scope. Registry headcounts are inventory only; they are not a denominator for cohort audience competition. Market scenarios have ILLUSTRATIVE_MARKET_SCENARIO scopes and are not observed ratios.', '', 'Supply saturation: HYPOTHESIS / INSUFFICIENT_EVIDENCE. numerator_scope=FULL_REGISTRY; denominator_scope=FROZEN_COHORT_193; scope_caveat: incompatible coverage, competition ratio withheld.', '', 'Reactivated accounts: ' + series + '. Counts increased across the completed 2022–2025 windows; 2026 is partial and is not compared as a full year. No stability rule has been established.', '', 'WACTOR: SECONDARY_DOCUMENTED; CORPORATE_REGISTRATION_UNVERIFIED. RPG: INFERRED_PROXY activity boundary; legal closure is unverified.', '', f'Lifecycle events: {len(events)}. Evidence tiers: ' + json.dumps(tiers, sort_keys=True) + '.', '', 'Exit events by event type and evidence tier:', '', '| Event | Evidence tier | Count |', '|---|---|---:|'] + [f'| {kind} | {tier} | {count} |' for (kind,tier),count in events[events.event_type.str.contains('GRADUATION|TERMINATION|HIATUS')].groupby(['event_type','evidence_tier']).size().items()] + ['', 'Snapshot: activity_status is an observation at MANIFEST_AT_SELECTION; lifecycle_evidence_tier describes available event evidence, not verification of present activity.', '<!-- source-integrity:end -->'])
    for name in ('OUTLOOK_MODEL.md','OUTLOOK_HYPOTHESES.md','LONG_RUNNING_RESEARCH_REPORT.md'):
        p=ROOT/'docs/research_v2'/name;s=p.read_text(encoding='utf8')
        s=re.sub(r'<!-- source-integrity:start -->.*?<!-- source-integrity:end -->', '', s, flags=re.S)
        s=s.replace('1,370+ discoverable channels in registry competing for ~13,000–18,000 annual observed commenter/chat participant accounts.', 'Registry inventory and frozen-cohort audience have incompatible scopes; no competition ratio is reported.')
        s=s.replace('1,370+ discoverable channels compete for 13k–18k commenters; network density compressed to 0.157.', 'Full-registry audience coverage is missing; cohort density is not evidence of full-ecosystem saturation.')
        s=s.replace('**STRONGLY SUPPORTED by channel inactivity rates, registry-to-interacting-account ratios, and network density compression.**', '**HYPOTHESIS / INSUFFICIENT_EVIDENCE: incompatible population scopes.**')
        s=s.replace('| **H4 SUPPLY SATURATION** | **STRONGLY SUPPORTED** | `[SUPPORTED_INTERPRETATION]` |', '| **H4 SUPPLY SATURATION** | **INSUFFICIENT_EVIDENCE** | `[HYPOTHESIS]` |')
        s=s.replace('Annual reactivated account inflow consistently delivers 700–950 returning accounts per year.', 'Reactivated account yearly series is generated in the canonical source integrity section; stability is not established.')
        s=s.replace('Failed agency models (WACTOR Thailand dissolved 2022; RPG ceased talent ops 2024).', 'WACTOR has secondary documentation and unverified corporate registration; RPG activity cessation is an INFERRED_PROXY, not verified closure.')
        s=s.replace('Agency dissolution: RPG ceased operations in 2024; WACTOR Thailand collapsed in 2022.', 'Organizational boundaries: RPG INFERRED_PROXY; WACTOR SECONDARY_DOCUMENTED with corporate registration UNVERIFIED.')
        s=s.replace('closure of unviable circles (RPG)', 'RPG activity boundary (INFERRED_PROXY; organizational closure unverified)')
        s=re.sub(r'\d+ (status events|verified/proxy events)',lambda m:f'{len(events)} {m[1]}',s)
        for tier,count in tiers.items(): s=re.sub(r'(`'+tier+r'`: \*\*)\d+( events\*\*)',lambda m:m[1]+str(count)+m[2],s)
        s=s.replace('12 official agency announcements with exact tweet URLs', '11 official agency announcements with exact tweet URLs')
        s=s.replace('33 have entered inactive/hiatus status and 12 have formally graduated', 'activity and lifecycle evidence are separated in the canonical snapshot')
        none_count = int((pd.read_parquet(ROOT/'data/industry/creator_evidence_coverage.parquet').remaining_gap == 'NONE').sum())
        s = re.sub(r'(remaining gaps stand at \*\*)\d+', lambda m: m[1]+str(none_count), s)
        s = s.replace('Creator Lifecycle Verification Status (N=193 Cohort)', 'Manifest activity observations at selection (N=193 Cohort)')
        s = s.replace('Hiatus / Inactive (Verified or Proxy)', 'Hiatus at selection (observed)').replace('Graduated / Retired (Formally Closed)', 'Graduated label at selection (not legal closure)').replace('Unknown / Inferred Active', 'Unknown at selection')
        s = s.replace('**HYPOTHESIS / INSUFFICIENT_EVIDENCE: incompatible population scopes.**', '**HYPOTHESIS / INSUFFICIENT_EVIDENCE: incompatible population scopes.**')
        s = s.replace('**Candidate-Video Resolution Rate:** numerator_scope=AUXILIARY_TITLE_CATALOG; denominator_scope=AUXILIARY_TITLE_CATALOG.', '**Candidate-Video Resolution Rate:**')
        s = s.replace('**Candidate-Video Resolution Rate:**', '**Candidate-Video Resolution Rate:** numerator_scope=AUXILIARY_TITLE_CATALOG; denominator_scope=AUXILIARY_TITLE_CATALOG.')
        p.write_text(s.rstrip()+'\n\n'+block+'\n',encoding='utf8')

if __name__ == '__main__': refresh()
