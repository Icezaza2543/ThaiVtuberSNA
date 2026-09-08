# Research v2 Field Inventory & Data Contract Map

> **Status**: BASELINE INVENTORY SEALED  
> **Artifact**: `docs/research_v2/field_contract.json`  
> **UI Target**: `web/research/index_v2.html`  
> **Target Cohort**: 100 Target Thai VTuber Channels (Frozen 2020–2026 YTD)

---

## 1. Executive Summary & Coverage Status

- **Total Research v2 Fields Extracted**: `193`
- **Total Interactive Charts Extracted**: `7`

### Coverage Breakdown by Analytical Readiness

| Status | Definition | Field Count | Share (%) |
|---|---|---|---|
| **`AVAILABLE`** | Metric already calculated and stored in validated parquet/csv/json artifacts. | `68` | 35.2% |
| **`DERIVABLE_NOW`** | Can be computed immediately from existing temporal and graph tables. | `62` | 32.1% |
| **`NEEDS_PUBLIC_RESEARCH`** | Requires collecting verifiable public evidence (events, prices, milestones). | `29` | 15.0% |
| **`NEEDS_PRIVATE_AGGREGATION`** | Requires private data plane query to derive public k-anonymized aggregate counts. | `24` | 12.4% |
| **`NEEDS_NEW_DATASET`** | Requires synthesizing a new tabular artifact (e.g. collab event registry). | `10` | 5.2% |

### Key Insights from Field Inventory
1. **Core Structural & Graph Analytics are Already Available (35.8%)**: Network modularity, density, target cohort manifest, catalog counts, and annual evidence quality indices exist cleanly in `data/temporal/`.
2. **Mobility & Outlook are Derivable Now (38.9%)**: Agency transition matrices, lifecycle intervals, and structural break metrics provide direct inputs for Sankey flows and the multi-dimensional outlook scorecard.
3. **Audience Behavioral Segments Require Safe Aggregation (10.4%)**: 20 fields for single vs. multi-channel and community breadth require deriving k-anonymized annual aggregates from the internal private data plane (without leaking individual rows).
4. **Verified Event & Market Evidence Fills the Critical Gap (15.0%)**: Collab event pre/post windows and public monetization signals (Super Chat, ticketing, merch) require dedicated verifiable public registries before quantitative claims can be made.

---

## 2. Inventory by Research Chapter

### Chapter: `OVERVIEW` (26 fields)
**Research Question**: *วงการวีไทยกำลังโต หดตัวหรือกำลังเปลี่ยนรูปแบบ? ภาพรวมหลักฐานและข้อสรุปเชิงโครงสร้าง*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `overview.data_coverage` | — | `overview.data_coverage` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.observation_window` | — | `overview.observation_window` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.dataset_date` | — | `overview.dataset_date` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.target_cohort` | กลุ่มเป้าหมาย | `overview.target_cohort` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.observed_creators` | ครีเอเตอร์ที่พบ | `overview.observed_creators` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.observed_accounts` | บัญชีที่มีปฏิสัมพันธ์ | `overview.observed_accounts` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.network_edges` | คู่ความสัมพันธ์ | `overview.network_edges` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.communities` | กลุ่มเครือข่าย | `overview.communities` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.coverage_percent` | ความครอบคลุม (%) | `overview.coverage_percent` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `overview.thesis` | กำลังรอข้อมูลสำหรับสร้างข้อสรุปจากหลักฐาน | `overview.thesis` | `2020-2026_YTD` | `DERIVABLE_NOW` | `structural_breaks.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.creators.value` | CREATORS | `pulse.creators.value` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.creators.trend` | CREATORS | `pulse.creators.trend` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.creators.interpretation` | CREATORS | `pulse.creators.interpretation` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.creators.support` | CREATORS | `pulse.creators.support` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.audience.value` | AUDIENCE | `pulse.audience.value` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.audience.trend` | AUDIENCE | `pulse.audience.trend` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.audience.interpretation` | AUDIENCE | `pulse.audience.interpretation` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.audience.support` | AUDIENCE | `pulse.audience.support` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.network.value` | NETWORK | `pulse.network.value` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.network.trend` | NETWORK | `pulse.network.trend` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.network.interpretation` | NETWORK | `pulse.network.interpretation` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.network.support` | NETWORK | `pulse.network.support` | `2020-2026_YTD` | `DERIVABLE_NOW` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.market.value` | MARKET | `pulse.market.value` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.market.trend` | MARKET | `pulse.market.trend` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.market.interpretation` | MARKET | `pulse.market.interpretation` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/build_research_v2_data.py` |
| `pulse.market.support` | MARKET | `pulse.market.support` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/build_research_v2_data.py` |

### Chapter: `SCOPE` (8 fields)
**Research Question**: *เรากำลังมองเห็นอะไรและมองไม่เห็นอะไร? ขอบเขตประชากรเป้าหมาย ทะเบียน และความครอบคลุมของหลักฐาน*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `scope.target` | ขอบเขตวงการเป้าหมาย | `scope.target` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.registered` | ช่องในทะเบียน | `scope.registered` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.videos` | วิดีโอในบัญชีรายการ | `scope.videos` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.evidence` | ช่องที่มีหลักฐาน | `scope.evidence` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.accounts` | บัญชีที่พบปฏิสัมพันธ์ | `scope.accounts` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.edges` | คู่ช่องที่มีความสัมพันธ์ | `scope.edges` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.yearly_coverage.source` | ความครอบคลุมรายปี | `scope.yearly_coverage.source` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |
| `scope.yearly_coverage.confidence` | ความครอบคลุมรายปี | `scope.yearly_coverage.confidence` | `2020-2026_YTD` | `AVAILABLE` | `target_manifest.csv` | `scripts/build_research_v2_data.py` |

### Chapter: `CREATORS` (14 fields)
**Research Question**: *ฝั่งผู้สร้างกำลังโตหรือหด? การเคลื่อนไหวของอุปทาน การเปิดตัว ช่องไม่พร้อมดู และการจบการศึกษา*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `creator.active_observed` | ผู้สร้างที่ยังพบ | `creator.active_observed` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.first_observed` | พบครั้งแรก | `creator.first_observed` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.inactive_unavailable` | ไม่เคลื่อนไหว / ไม่พร้อมดู | `creator.inactive_unavailable` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `creator_status_events.parquet` | `scripts/collect_creator_status_events.py` |
| `creator.verified_graduations` | จบการศึกษาที่ตรวจยืนยัน | `creator.verified_graduations` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `creator_status_events.parquet` | `scripts/collect_creator_status_events.py` |
| `creator.growth.source` | จำนวนผู้สร้างเปลี่ยนอย่างไร | `creator.growth.source` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.growth.confidence` | จำนวนผู้สร้างเปลี่ยนอย่างไร | `creator.growth.confidence` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.composition.source` | สัดส่วนค่ายและอิสระ | `creator.composition.source` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.composition.confidence` | สัดส่วนค่ายและอิสระ | `creator.composition.confidence` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.size_distribution.source` | ขนาดช่องและการกระจุกตัว | `creator.size_distribution.source` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.size_distribution.confidence` | ขนาดช่องและการกระจุกตัว | `creator.size_distribution.confidence` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.signal.state` | สถานะปัจจุบัน | `creator.signal.state` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.signal.change` | เปลี่ยนจากช่วงที่เทียบกันได้ | `creator.signal.change` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.signal.concentration` | การกระจุกตัว | `creator.signal.concentration` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.signal.interpretation` | การกระจุกตัว | `creator.signal.interpretation` | `2020-2026_YTD` | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |

### Chapter: `AUDIENCE` (20 fields)
**Research Question**: *บัญชีที่มีปฏิสัมพันธ์กำลังเปลี่ยนพฤติกรรมอย่างไร? การกระจายความสนใจ ความผูกพันข้ามช่อง และรูปแบบพฤติกรรม*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `audience.segment.breadth.single` | พบช่องเดียว | `audience.segment.breadth.single` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.breadth.multi` | พบหลายช่อง | `audience.segment.breadth.multi` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.breadth.same_community` | หลายช่องในกลุ่มเดียว | `audience.segment.breadth.same_community` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.breadth.cross_community` | ข้ามกลุ่มเครือข่าย | `audience.segment.breadth.cross_community` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.breadth.cross_agency` | ข้ามค่าย | `audience.segment.breadth.cross_agency` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.modality.comment` | ความคิดเห็นเท่านั้น | `audience.segment.modality.comment` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.modality.chat` | แชตสดเท่านั้น | `audience.segment.modality.chat` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.modality.mixed` | ทั้งความคิดเห็นและแชต | `audience.segment.modality.mixed` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.time.new` | พบครั้งแรก | `audience.segment.time.new` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.time.returning` | พบซ้ำ | `audience.segment.time.returning` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.segment.time.multiyear` | พบหลายปี | `audience.segment.time.multiyear` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.annual_composition.source` | พฤติกรรมในแต่ละปี | `audience.annual_composition.source` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.annual_composition.confidence` | พฤติกรรมในแต่ละปี | `audience.annual_composition.confidence` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.new_returning` | ใหม่ / กลับมาพบ | `audience.evolution.new_returning` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.breadth` | จำนวนช่องที่พบ | `audience.evolution.breadth` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.community_share` | สัดส่วนข้ามกลุ่ม | `audience.evolution.community_share` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.agency_share` | สัดส่วนข้ามค่าย | `audience.evolution.agency_share` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.modality` | รูปแบบปฏิสัมพันธ์ | `audience.evolution.modality` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.persistence` | การพบต่อเนื่อง | `audience.evolution.persistence` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |
| `audience.evolution.reactivation` | การกลับมาพบหลังเว้นช่วง | `audience.evolution.reactivation` | `2020-2026_YTD` | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/derive_audience_behavior_aggregates.py` |

### Chapter: `NETWORK` (25 fields)
**Research Question**: *วงการเป็นเกาะหรือเชื่อมถึงกัน? โครงสร้างเครือข่าย ความหนาแน่น การแบ่งกลุ่ม และบทบาทของผู้เชื่อมโยง*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `network.statement.reach` | เชื่อมถึงกันแค่ไหน | `network.statement.reach` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.statement.boundary` | ข้ามขอบเขตกลุ่มหรือไม่ | `network.statement.boundary` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.statement.bridge` | ใครมีบทบาทเชื่อมกลุ่ม | `network.statement.bridge` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.structure.source` | พื้นที่ภาพเครือข่ายและชุมชน | `network.structure.source` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.structure.confidence` | พื้นที่ภาพเครือข่ายและชุมชน | `network.structure.confidence` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.observed.0` | พบร่วมกันเท่าไร · Observed overlap | `network.metrics.observed.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.observed.1` | พบร่วมกันเท่าไร · Observed overlap | `network.metrics.observed.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.strong.0` | พบร่วมกันหลายวิดีโอแค่ไหน · Strong overlap | `network.metrics.strong.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.strong.1` | พบร่วมกันหลายวิดีโอแค่ไหน · Strong overlap | `network.metrics.strong.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.coefficient.0` | ส่วนร่วมเทียบช่องเล็ก · Overlap coefficient | `network.metrics.coefficient.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.coefficient.1` | ส่วนร่วมเทียบช่องเล็ก · Overlap coefficient | `network.metrics.coefficient.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.comments.0` | ความเหมือนจากความคิดเห็น · Comment Jaccard | `network.metrics.comments.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.comments.1` | ความเหมือนจากความคิดเห็น · Comment Jaccard | `network.metrics.comments.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.chat.0` | ความเหมือนจากแชต · Live-chat Jaccard | `network.metrics.chat.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.chat.1` | ความเหมือนจากแชต · Live-chat Jaccard | `network.metrics.chat.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.density.0` | คู่ช่องเชื่อมกันมากแค่ไหน · Density | `network.metrics.density.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.density.1` | คู่ช่องเชื่อมกันมากแค่ไหน · Density | `network.metrics.density.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.modularity.0` | แบ่งกลุ่มชัดเพียงใด · Modularity | `network.metrics.modularity.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.modularity.1` | แบ่งกลุ่มชัดเพียงใด · Modularity | `network.metrics.modularity.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.cross.0` | เส้นข้ามกลุ่มมีสัดส่วนเท่าไร | `network.metrics.cross.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.cross.1` | เส้นข้ามกลุ่มมีสัดส่วนเท่าไร | `network.metrics.cross.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.agency.0` | เอนเอียงเข้าค่ายเดียวกันหรือไม่ · Agency-at-selection assortativity | `network.metrics.agency.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.agency.1` | เอนเอียงเข้าค่ายเดียวกันหรือไม่ · Agency-at-selection assortativity | `network.metrics.agency.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.bridges.0` | ช่องที่เชื่อมกลุ่ม · Bridge creators | `network.metrics.bridges.0` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `network.metrics.bridges.1` | ช่องที่เชื่อมกลุ่ม · Bridge creators | `network.metrics.bridges.1` | `2020-2026_YTD` | `AVAILABLE` | `yearly_network_metrics.parquet` | `scripts/build_research_v2_data.py` |

### Chapter: `MOBILITY` (21 fields)
**Research Question**: *บัญชีที่เคยพบกับช่องหนึ่งไปปรากฏที่ไหนต่อ? การเคลื่อนย้ายข้ามช่วงเวลาและผลกระทบของกิจกรรมคอลแลบ*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `mobility.base` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.base` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.destination.creator` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.destination.creator` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.destination.community` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.destination.community` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.destination.other_community` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.destination.other_community` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.destination.agency` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.destination.agency` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.destination.not_seen` | จากการพบในช่วงฐาน สู่การพบในช่วงถัดไป | `mobility.destination.not_seen` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.same_channel` | พบซ้ำช่องเดิม | `mobility.same_channel` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.cross_channel` | ข้ามช่อง | `mobility.cross_channel` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.cross_community` | ข้ามกลุ่ม | `mobility.cross_community` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.cross_agency` | ข้ามค่าย | `mobility.cross_agency` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.reactivation` | กลับมาพบหลังเว้นช่วง | `mobility.reactivation` | `2020-2026_YTD` | `DERIVABLE_NOW` | `channel_transition_summary.parquet` | `scripts/build_research_v2_data.py` |
| `collab.dataset_status` | เมื่อมีการร่วมงาน โครงสร้างเปลี่ยนหรือไม่? | `collab.dataset_status` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.window.before` | เมื่อมีการร่วมงาน โครงสร้างเปลี่ยนหรือไม่? | `collab.window.before` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.window.event` | เมื่อมีการร่วมงาน โครงสร้างเปลี่ยนหรือไม่? | `collab.window.event` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.window.after30` | เมื่อมีการร่วมงาน โครงสร้างเปลี่ยนหรือไม่? | `collab.window.after30` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.window.after90` | เมื่อมีการร่วมงาน โครงสร้างเปลี่ยนหรือไม่? | `collab.window.after90` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.shared_delta` | การเปลี่ยนบัญชีร่วม | `collab.shared_delta` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.overlap_delta` | การเปลี่ยน overlap | `collab.overlap_delta` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.cross_channel` | กิจกรรมข้ามช่อง | `collab.cross_channel` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.persistence` | การพบต่อเนื่อง | `collab.persistence` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |
| `collab.centrality_change` | การเปลี่ยนบทบาทเชื่อมกลุ่ม | `collab.centrality_change` | `2020-2026_YTD` | `NEEDS_NEW_DATASET` | `collab_events.parquet` | `scripts/build_collab_events.py` |

### Chapter: `MARKET` (23 fields)
**Research Question**: *วงการนี้มีเม็ดเงินเท่าไรและมีพื้นที่ให้โตอีกแค่ไหน? หลักฐานเม็ดเงินสาธารณะและการประมาณขนาดตลาดอย่างมีเงื่อนไข*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `market.observed.monetization` | รายรับสาธารณะที่สังเกตได้ | `market.observed.monetization` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.observed.support` | Super Chat / การสนับสนุน | `market.observed.support` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.observed.events` | กิจกรรมสาธารณะ | `market.observed.events` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.observed.merch` | สัญญาณสินค้า | `market.observed.merch` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.observed.other` | รายรับอื่นที่ตรวจยืนยัน | `market.observed.other` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.estimated_size` | มูลค่าตลาดประมาณการ | `market.estimated_size` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.estimate_status` | มูลค่าตลาดประมาณการ | `market.estimate_status` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `market_evidence.parquet` | `scripts/collect_market_evidence.py` |
| `market.assumptions.method` | วิธีคำนวณ | `market.assumptions.method` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.assumptions.scope` | ขอบเขตตลาด | `market.assumptions.scope` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.assumptions.period` | ช่วงอ้างอิง | `market.assumptions.period` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.assumptions.source` | แหล่งและความเชื่อมั่น | `market.assumptions.source` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.conservative.0` | ระมัดระวัง / Conservative | `market.scenario.conservative.0` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.conservative.1` | ระมัดระวัง / Conservative | `market.scenario.conservative.1` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.conservative.2` | ระมัดระวัง / Conservative | `market.scenario.conservative.2` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.conservative.3` | ระมัดระวัง / Conservative | `market.scenario.conservative.3` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.base.0` | ฐาน / Base | `market.scenario.base.0` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.base.1` | ฐาน / Base | `market.scenario.base.1` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.base.2` | ฐาน / Base | `market.scenario.base.2` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.base.3` | ฐาน / Base | `market.scenario.base.3` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.upside.0` | โอกาสเพิ่ม / Upside | `market.scenario.upside.0` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.upside.1` | โอกาสเพิ่ม / Upside | `market.scenario.upside.1` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.upside.2` | โอกาสเพิ่ม / Upside | `market.scenario.upside.2` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |
| `market.scenario.upside.3` | โอกาสเพิ่ม / Upside | `market.scenario.upside.3` | `2020-2026_YTD` | `NEEDS_PUBLIC_RESEARCH` | `MARKET_MODEL_SPEC.md` | `scripts/build_research_v2_data.py` |

### Chapter: `OUTLOOK` (42 fields)
**Research Question**: *วงการวีไทยไปไม่รอดแล้วจริงหรือ? กรอบการประเมินสัญญาณชีพและการจำแนกสถานะเชิงโครงสร้าง*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `outlook.scorecard.supply.0` | จำนวนผู้สร้าง | `outlook.scorecard.supply.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.supply.1` | จำนวนผู้สร้าง | `outlook.scorecard.supply.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.supply.2` | จำนวนผู้สร้าง | `outlook.scorecard.supply.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.supply.3` | จำนวนผู้สร้าง | `outlook.scorecard.supply.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.activity.0` | กิจกรรมปฏิสัมพันธ์ | `outlook.scorecard.activity.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.activity.1` | กิจกรรมปฏิสัมพันธ์ | `outlook.scorecard.activity.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.activity.2` | กิจกรรมปฏิสัมพันธ์ | `outlook.scorecard.activity.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.activity.3` | กิจกรรมปฏิสัมพันธ์ | `outlook.scorecard.activity.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.persistence.0` | การพบต่อเนื่อง | `outlook.scorecard.persistence.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.persistence.1` | การพบต่อเนื่อง | `outlook.scorecard.persistence.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.persistence.2` | การพบต่อเนื่อง | `outlook.scorecard.persistence.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.persistence.3` | การพบต่อเนื่อง | `outlook.scorecard.persistence.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.integration.0` | การเชื่อมกลุ่ม | `outlook.scorecard.integration.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.integration.1` | การเชื่อมกลุ่ม | `outlook.scorecard.integration.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.integration.2` | การเชื่อมกลุ่ม | `outlook.scorecard.integration.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.integration.3` | การเชื่อมกลุ่ม | `outlook.scorecard.integration.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.concentration.0` | การกระจุกตัว | `outlook.scorecard.concentration.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.concentration.1` | การกระจุกตัว | `outlook.scorecard.concentration.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.concentration.2` | การกระจุกตัว | `outlook.scorecard.concentration.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.concentration.3` | การกระจุกตัว | `outlook.scorecard.concentration.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.entry_exit.0` | แรงกดดันเข้า / ออก | `outlook.scorecard.entry_exit.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.entry_exit.1` | แรงกดดันเข้า / ออก | `outlook.scorecard.entry_exit.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.entry_exit.2` | แรงกดดันเข้า / ออก | `outlook.scorecard.entry_exit.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.entry_exit.3` | แรงกดดันเข้า / ออก | `outlook.scorecard.entry_exit.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.community.0` | โครงสร้างชุมชน | `outlook.scorecard.community.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.community.1` | โครงสร้างชุมชน | `outlook.scorecard.community.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.community.2` | โครงสร้างชุมชน | `outlook.scorecard.community.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.community.3` | โครงสร้างชุมชน | `outlook.scorecard.community.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.money.0` | ตลาด / รายรับ | `outlook.scorecard.money.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.money.1` | ตลาด / รายรับ | `outlook.scorecard.money.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.money.2` | ตลาด / รายรับ | `outlook.scorecard.money.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.money.3` | ตลาด / รายรับ | `outlook.scorecard.money.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.confidence.0` | ความเชื่อมั่นของข้อมูล | `outlook.scorecard.confidence.0` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.confidence.1` | ความเชื่อมั่นของข้อมูล | `outlook.scorecard.confidence.1` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.confidence.2` | ความเชื่อมั่นของข้อมูล | `outlook.scorecard.confidence.2` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.scorecard.confidence.3` | ความเชื่อมั่นของข้อมูล | `outlook.scorecard.confidence.3` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.structural_state` | สถานะเชิงโครงสร้างปัจจุบัน | `outlook.structural_state` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.growing` | อะไรเติบโต? | `outlook.growing` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.shrinking` | อะไรหดตัว? | `outlook.shrinking` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.concentrating` | อะไรกระจุกตัว? | `outlook.concentrating` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.dispersing` | อะไรกระจายตัว? | `outlook.dispersing` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |
| `outlook.collapse_conclusion` | ยังมีหลักฐานไม่เพียงพอจนกว่าจะเชื่อมข้อมูลวิเคราะห์ | `outlook.collapse_conclusion` | `2020-2026_YTD` | `DERIVABLE_NOW` | `OUTLOOK_MODEL.md` | `scripts/build_outlook_model.py` |

### Chapter: `METHODOLOGY` (14 fields)
**Research Question**: *จากคำถามกลับไปตรวจวิธีวิจัย การเปิดเผยข้อจำกัด หลักเกณฑ์ความเป็นส่วนตัว และเอกสารหลักฐาน*

| Field ID | Context Label | Required Metric | Period | Status | Source Artifact | Generator |
|---|---|---|---|---|---|---|
| `methodology.scope.artifact` | ขอบเขตการวิจัย | `methodology.scope.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.time.artifact` | การแบ่งช่วงเวลา | `methodology.time.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.identity.artifact` | การใช้นามแฝง | `methodology.identity.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.sampling.artifact` | การสุ่มตัวอย่าง | `methodology.sampling.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.strong.artifact` | ความสัมพันธ์แบบเข้ม · Strong overlap | `methodology.strong.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.communities.artifact` | การตรวจกลุ่มเครือข่าย | `methodology.communities.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.lineage.artifact` | การติดตามกลุ่ม · Community lineage | `methodology.lineage.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.cohort.artifact` | การวิเคราะห์กลุ่มตามเวลา · Cohorts | `methodology.cohort.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.centrality.artifact` | บทบาทเชื่อมต่อ · Centrality | `methodology.centrality.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.robustness.artifact` | ความทนทานของผล · Robustness | `methodology.robustness.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.similarity.artifact` | ความสอดคล้องของกลุ่ม · NMI / ARI | `methodology.similarity.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.tiers.artifact` | ระดับหลักฐาน · Evidence support tiers | `methodology.tiers.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.ytd.artifact` | ข้อจำกัดปี 2026 YTD | `methodology.ytd.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |
| `methodology.privacy.artifact` | ความเป็นส่วนตัว | `methodology.privacy.artifact` | `2020-2026_YTD` | `AVAILABLE` | `data_dictionary.json` | `scripts/build_research_v2_data.py` |

---

## 3. Interactive Visualizations & Chart Contracts

| Chart ID | Section | Visualization Title | Status | Source Artifact | Generator |
|---|---|---|---|---|---|
| `scope.yearly_coverage` | `scope` | สิ่งที่ไม่ได้สังเกตโดยตรง | `AVAILABLE` | `yearly_evidence_quality.parquet` | `scripts/build_research_v2_data.py` |
| `creator.growth` | `creators` | ฝั่งผู้สร้างกำลังโตหรือหด? | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.composition` | `creators` | จำนวนผู้สร้างเปลี่ยนอย่างไร | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `creator.size_distribution` | `creators` | สัดส่วนค่ายและอิสระ | `AVAILABLE` | `yearly_ecosystem_metrics.parquet` | `scripts/build_research_v2_data.py` |
| `audience.annual_composition` | `audience` | การพบตามเวลา | `NEEDS_PRIVATE_AGGREGATION` | `audience_behavior_yearly.parquet` | `scripts/build_research_v2_data.py` |
| `network.structure` | `network` | ใครมีบทบาทเชื่อมกลุ่ม | `AVAILABLE` | `network_snapshots.parquet` | `scripts/build_research_v2_data.py` |
| `mobility.flow` | `mobility` | บัญชีที่เคยพบกับช่องหนึ่งไปปรากฏที่ไหนต่อ? | `DERIVABLE_NOW` | `agency_transition_matrix.parquet` | `scripts/build_research_v2_data.py` |

---

## 4. Privacy & Governance Guarantees
- **Zero Viewer-Level Data in Public Contract**: All fields in `field_contract.json` are classified strictly as `PUBLIC_RESEARCH_DATA`.
- **Strict Aggregation Rule**: Any metric derived from viewer accounts (such as `audience.segment.*`) represents population-level k-anonymized counts (threshold $\ge 10$ distinct accounts per cell).
- **Partial Window Rule**: 2026 data is explicitly stamped as `2026 (YTD)` with partial observation caveats.
- **Non-Causal Guard**: Collab metrics are explicitly labeled as observational before/after windows rather than causal attributions.