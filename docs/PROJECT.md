# ThaiVtuberSNA — Project Guide

> เอกสารฉบับนี้คือ source of truth หลักของโปรเจกต์  
> `docs/legal/` และ `docs/evidence/` เป็นเอกสารประกอบด้านนโยบาย/หลักฐาน ส่วน `docs/research_v2/` และเอกสาร historical/refactor ที่ยังคงอยู่ถือเป็น frozen provenance ไม่ใช่ active project documentation

## 1. เป้าหมายของโครงการ

ThaiVtuberSNA ศึกษาโครงสร้างของวงการ VTuber ไทยด้วย Social Network Analysis (SNA) จากหลักฐานการมีปฏิสัมพันธ์สาธารณะที่พบร่วมกันระหว่างช่อง

หน่วยหลักของกราฟคือ **ช่องครีเอเตอร์** และความสัมพันธ์หนึ่งเส้นเกิดจากการพบตัวตนแบบใช้นามแฝงเดียวกันมีปฏิสัมพันธ์กับทั้งสองช่องภายใต้ขอบเขตข้อมูลที่ระบุ

โครงการไม่ได้พยายามทำ audience census และไม่ใช้กราฟเพื่อยืนยันความสนิท อิทธิพล การย้ายแฟนคลับ หรือเหตุและผล

## 2. คำถามวิจัยหลัก

Research Dashboard ถูกออกแบบให้ตอบคำถามหลักสี่กลุ่ม:

1. **โครงสร้าง ecosystem เปลี่ยนอย่างไรตามเวลา**
   - จำนวนช่องที่มีหลักฐาน
   - จำนวนคู่ความสัมพันธ์
   - community structure
   - modularity, density และ cross-community edges

2. **กลุ่มที่คำนวณได้มีความต่อเนื่องอย่างไร**
   - community lineage
   - continuation / split / merge relationships
   - สมาชิกที่พบร่วมกันระหว่างปี

3. **ยังพบผู้มีปฏิสัมพันธ์กลุ่มเดิมซ้ำหรือไม่**
   - cohort retention
   - same-channel / cross-channel re-observation
   - reactivation หลังเว้นช่วง

4. **ผลที่เห็นพึ่งพาความครอบคลุมของข้อมูลมากแค่ไหน**
   - channel coverage
   - video sampling ratio
   - interaction volume
   - evidence support tier
   - sensitivity / robustness checks

## 3. นิยามที่ต้องอ่านให้ตรงกัน

| ตัวชี้วัด | ความหมาย |
| --- | --- |
| `shared_any` | ตัวตนแบบใช้นามแฝงที่พบกับทั้งสองช่องจาก source ที่รองรับ |
| `shared_comments` | พบความคิดเห็นกับทั้งสองช่อง |
| `shared_live_chat` | พบ live chat กับทั้งสองช่อง |
| `strong_shared_*` | ตัวตนเดียวกันพบในอย่างน้อย 2 วิดีโอที่ไม่ซ้ำต่อช่องตาม source นั้น |
| `videos_seen` | วิดีโอที่ไม่ซ้ำซึ่งมีหลักฐานจาก source ใด source หนึ่ง |
| `live_streams_seen` | วิดีโอที่ไม่ซ้ำซึ่งมีหลักฐาน `live_chat` |
| community | กลุ่มที่คำนวณจากโครงสร้างเครือข่าย ไม่ใช่ค่าย |
| centrality | ตำแหน่งเชิงโครงสร้างในชุดข้อมูล ไม่ใช่อันดับความนิยม |

`shared_comments` และ `shared_live_chat` อาจทับซ้อนกัน จึงห้ามนำมาบวกเพื่ออนุมาน `shared_any`

การไม่พบตัวตนเดิมในปีถัดไปหมายถึง **ไม่พบในหลักฐานที่เก็บได้** ไม่ใช่การยืนยันว่าเลิกดูหรือออกจากชุมชน

## 4. Cohort และตัวตนครีเอเตอร์

โครงการรักษา approved cohort เดิมทั้งหมด **1,370 ช่อง** เป็นฐานการศึกษา เว้นแต่มีการเปลี่ยนแปลง cohort แบบมีหลักฐานและ provenance ชัดเจน

ThaiVirtualCreatorRegistry เป็นโครงการแยกที่ช่วยเรื่อง discovery / registry / identity evidence ส่วน ThaiVtuberSNA รับผิดชอบ interaction evidence และ network analysis

ข้อมูลค่ายหรือสถานะที่ใช้ในกราฟต้องระบุช่วงเวลาและแหล่งที่มา ห้ามเปลี่ยน metadata ปัจจุบันให้กลายเป็นประวัติย้อนหลังโดยไม่มีหลักฐาน

## 5. Privacy และ HMAC continuity

ผู้มีปฏิสัมพันธ์ถูกใช้นามแฝงด้วย HMAC-SHA256 เพื่อให้เชื่อมหลักฐานข้ามช่องและข้ามเวลาได้อย่างสม่ำเสมอ

กฎสำคัญ:

- `config/secret.key` ไม่เข้า Git
- ต้องใช้กุญแจเดิมสำหรับ longitudinal evidence เดิม
- `config/secret.fingerprint` ใช้ตรวจ continuity ของกุญแจ
- ห้ามสร้างกุญแจใหม่ทับ dataset เดิม
- หน้าเว็บสาธารณะเผยแพร่เฉพาะ creator metadata และ aggregate outputs
- HMAC คือ pseudonymization ไม่ใช่การรับรองว่าเป็นข้อมูลนิรนามตามกฎหมาย

ตรวจ continuity ด้วย:

```bash
python -m core.hasher --verify-key
```

## 6. Live collection contract ปัจจุบัน

runtime state ของ campaign อยู่ใน `scratch/expanded-v1-campaign/` และถูกกันออกจาก Git โดยตั้งใจ

interaction worker ปัจจุบันใช้ policy:

`bulk-fair-channel-year-page15-v3`

หลักการ:

- เก็บ **หนึ่ง successful comment page ต่อ NEW video**
- สูงสุด **15 top-level comments ต่อ video** ใน first pass
- replies ถูก deferred
- legacy deep jobs และ checkpoint เดิมต้องคงอยู่
- catalog completion แยกจาก sampled interaction coverage
- single writer เท่านั้น
- quota ledger, acknowledged events, page offsets, provenance และ HMAC continuity ห้าม reset
- shared general ceiling = 9,000 units ต่อ Pacific day โดยกัน 1,000 units เป็น reserve
- `quotaExceeded` / `dailyLimitExceeded` ปิด window นั้น
- worker รอ `QUOTA_WAIT` โดยไม่ยิง API
- `WORKER_ERROR_STOP`, `PERSISTENCE_STOP`, `STORAGE_CAPACITY_STOP`, `OPERATOR_STOP` และ `interactions.stop` ต้องให้ operator ตรวจ ไม่ auto-retry ambiguous writes

คำสั่ง worker canonical:

```bash
python -m scripts.run_campaign_interactions
```

ห้ามใช้คำสั่งนี้เป็นการเริ่ม campaign ใหม่จากศูนย์ ต้อง resume จาก durable checkpoints เดิมเท่านั้น

## 7. Storage และ provenance

แยกข้อมูลเป็นสามชั้น:

1. **Secret**
   - HMAC key
   - API keys
   - credentials

2. **Private analytical evidence**
   - pseudonymous interaction records
   - job/checkpoint state
   - private workbook/archive
   - local campaign SQLite ledgers

3. **Public**
   - creator metadata ที่อนุญาตให้เผยแพร่
   - aggregate network outputs
   - temporal snapshots
   - Research Dashboard data

หลักฐานหรือ source copies ไม่ถูกนับเป็น observation ซ้ำโดยอัตโนมัติ ทุก output ต้องรักษา provenance และ distinction ระหว่าง catalog coverage กับ interaction coverage

## 8. Frontend

เว็บไซต์เป็น static vanilla HTML/CSS/JavaScript ไม่มี build step

canonical views มีเพียงสองหน้า:

- `/?view=network` — network observatory
- `/?view=research` — Research Dashboard

โครงสร้าง frontend หลัก:

```text
web/
├─ index.html             # markup ของทั้งสอง view
├─ site.js                # query-route loader
├─ site.css               # shell/navigation
├─ network.css            # network view
├─ network-state.js       # temporal snapshot adapter
├─ app.js                 # graph renderer/core state
├─ network-ui.js          # controls/inspector/accessibility
├─ research.css           # Research Dashboard
├─ research.js            # Research Dashboard rendering
├─ data.json              # public network snapshot
├─ data/                  # public aggregate temporal outputs
└─ research/
   └─ dashboard_data.json # aggregate Research Dashboard dataset
```

Report v2 prototype ถูกยกเลิกจาก canonical UI เพื่อไม่ให้ซ้ำกับ Research Dashboard และไม่ให้ placeholder ถูกเข้าใจว่าเป็นผลวิจัยจริง

## 9. โครงสร้าง repository

```text
analytics/   นิยาม metric และ aggregate analysis
collector/   collection logic
core/        identity, HMAC, security/data rules
storage/     private storage adapters
scripts/     CLI, campaign, analysis และ maintenance
web/         public network + research UI
tests/       regression / synthetic fixtures
docs/        PROJECT.md + legal/ + evidence/
data/        public/frozen analytical artifacts ตามขอบเขตของแต่ละชุด
scratch/     local runtime state; ไม่เข้า Git
```

หลีกเลี่ยงการเพิ่ม directory ใหม่หากหน้าที่ซ้ำกับพื้นที่ด้านบน

## 10. Research Dashboard

หน้า Research ต้องเริ่มจาก **scope ก่อน interpretation**

ลำดับการอ่าน:

1. เลือกปี
2. ตรวจ channel/video coverage
3. อ่าน ecosystem structure
4. อ่าน lineage / cohort / bridge metrics
5. ตรวจ sensitivity และข้อจำกัด
6. จึงสรุปเชิงพรรณนา

ปี 2026 เป็น partial year ใน dataset ปัจจุบัน ห้ามเทียบกับปีเต็มแล้วสรุป growth/decline โดยตรง

Dashboard ไม่ควรมี leaderboard เชิงคุณค่าหรือคำตัดสินว่าช่องใด “ดีกว่า” อีกช่องหนึ่ง centrality ใช้เพื่อบรรยายตำแหน่งในกราฟเท่านั้น

## 11. การรันเว็บในเครื่อง

```bash
python -m http.server 5500 --bind 127.0.0.1 --directory web
```

เปิด:

- http://127.0.0.1:5500/?view=network
- http://127.0.0.1:5500/?view=research

อย่า serve repository root เพราะ local checkout อาจมี credentials และ private runtime state

## 12. การแก้โค้ด

หลักการสำหรับงานต่อจากนี้:

- ไม่แก้ frozen evidence เพียงเพื่อให้ test ผ่าน
- ไม่เพิ่ม test ซ้ำหากไม่ได้ป้องกัน regression ที่เกิดจากงานนั้นจริง
- ไม่เปลี่ยน HMAC identity
- ไม่ reset ledger/checkpoint
- ไม่ตีความ missing data เป็น zero
- ไม่อ้าง complete interaction coverage จาก catalog completion
- ไม่สร้าง public artifact ที่มี viewer-level rows
- ไม่ทำ framework migration โดยไม่มีเหตุผล
- ชื่อไฟล์ควรบอกหน้าที่ตรง ๆ และหลีกเลี่ยง suffix เช่น `_v2`, `_final`, `_new` สำหรับ canonical code

## 13. หลักฐานและนโยบาย

เอกสารที่แยกออกจาก Project Guide เพราะเป็นคนละประเภท:

- `docs/evidence/` — machine-readable QA / audit evidence
- `docs/research_v2/` — frozen historical research/provenance; ไม่ใช่ canonical documentation
- `docs/legal/TERMS.md`
- `docs/legal/PRIVACY.md`
- `docs/legal/RIGHTS_REQUESTS.md`
- `docs/legal/OPERATOR_CHECKLIST.md`
- `SECURITY.md`
- `LICENSE`

ไฟล์เหล่านี้ไม่ควรถูกนำกลับมารวมเป็น narrative docs หลายชุดอีก

## 14. ข้อจำกัดที่ยังต้องถือไว้

- interaction coverage เป็น sampled evidence ไม่ใช่ exhaustive archive
- public interaction ไม่เท่ากับ consent สำหรับทุกการใช้
- community detection ไม่ยืนยัน social group จริง
- centrality ไม่ยืนยัน influence
- HMAC pseudonyms ไม่เท่ากับจำนวนมนุษย์จริงแบบสมบูรณ์
- historical identity / affiliation บางช่วงยังมี uncertainty
- runtime collection state สดอยู่ local และไม่ควร publish ลง Git

เป้าหมายของโครงการคือทำให้ข้อสรุปทุกอย่างย้อนกลับไปตรวจ **scope, evidence, method และ limitation** ได้ โดยไม่ทำให้ dashboard ดูมั่นใจกว่าหลักฐานที่มี
