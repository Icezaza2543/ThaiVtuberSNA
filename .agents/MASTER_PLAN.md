# แผนรวม ThaiVirtualCreatorRegistry + ThaiVtuberSNA เป็นเว็บเดียว

วันที่วางแผน: 20 กันยายน 2026  
สถานะเอกสาร: แผนดำเนินการจากการอ่าน repository และ config จริง ยังไม่ได้ merge, แก้ Google Sheet, เริ่มเก็บข้อมูล หรือ deploy ในรอบวางแผนนี้

## 1. เป้าหมายและสิ่งที่ล็อกไว้

ให้เปิดเว็บไซต์เดียวแล้วตอบได้ว่า วีไทยในทะเบียนมีใครบ้าง มีกี่เพอร์โซนา มีช่องทางและผู้ติดตามเท่าไร เกิดใหม่/รีเดบิวต์ปีไหน อยู่กลุ่มหรือค่ายอะไร ใครมีปฏิสัมพันธ์กับใคร ผู้มีปฏิสัมพันธ์ซ้อนทับกันกี่บัญชีและกี่เปอร์เซ็นต์ และมีข้อมูลการเงินที่ตรวจดูแหล่งที่มาได้อย่างไร

- Repository หลัก: `Icezaza2543/ThaiVtuberSNA`
- Branch ที่พัฒนาต่อ: `main`
- Frontend เดียว มี Home, VtuberRecord, SNA, Data Analytics Dashboard, Financial Data Analytics Dashboard
- Google Sheet เดิมเป็นฐานหลักของทะเบียนและข้อมูลที่แก้ไขดูแล ไม่สร้างทะเบียน JSON อีกชุดมาแข่งกัน
- ใช้โค้ดและผลเก็บเดิมก่อน ไม่เริ่ม rewrite หรือ recollect ทั้งระบบ
- ไม่เขียน/รัน data-validation suite, data audit, benchmark, synthetic test หรือ regression campaign เพื่อขวางการส่งเว็บ
- แก้ข้อผิดพลาดที่ทำให้คำสั่งทำงานไม่ได้หรือหน้าเว็บเปิดไม่ได้ระหว่างทำงานจริง ไม่มีรอบทดสอบข้อมูลแยก
- ข้อมูล actor ใหม่ใช้ public platform account ID และ display name ได้โดยตรง ไม่บังคับ HMAC
- เก็บเฉพาะตัวตนสาธารณะบนแพลตฟอร์ม ไม่เชื่อมชื่อจริง ที่อยู่ หรือข้อมูลส่วนตัวที่ไม่ได้เปิดเผย
- ไม่เพิ่ม paid API, LLM enrichment หรือบริการใหม่เพื่อทำสิ่งที่ข้อมูลและโค้ดเดิมทำได้

## 2. ข้อเท็จจริงที่ตรวจพบใน repository

### ThaiVtuberSNA

main ณ เวลาวางแผน: `80378402588c6e9429effc4bce7c4e977f9221b8`

Branch นอก main ที่พบ:

1. `codex/creator-registry-consolidation` — `0d21a2ed737d33ca144669e9647cfaa316dc0a5a`
2. `codex/provisional-channel-resolution` — `81ca1e37c78291c41207ba17d68f0ba21bf90144`
3. `simplify-research-dashboard` — `5f1bf88fa575450768e02779fa0766475fe9c187`
4. `temp/visual-identity-review` — `046edea9eff32da25c5a52270ee84d98b1d56f04`

`docs/PROJECT.md` ระบุ frontend เป็น static HTML/CSS/JavaScript ไม่มี build step และมี network กับ research view อยู่แล้ว

`config/settings.py` ระบุ Google Sheet ผ่าน environment variable `VTUBER_SPREADSHEET_ID` และใช้แท็บ `VTUBERS`, `SYSTEM`, `NETWORK_RESULT`

`storage/duckdb_engine.py` มี DuckDB ที่อ่าน Parquet และคำนวณ overlap อยู่แล้ว

เอกสารเดิมยังตรึง cohort 1,370 ช่อง และ config มี `min_subscribers: 100` แผนใหม่นี้ไม่ใช้สองเงื่อนไขดังกล่าวกีดกันรายชื่อใน master registry

เอกสาร worker เดิมระบุ first pass สูงสุด 15 top-level comments ต่อวิดีโอ และยัง defer replies จึงห้ามนำผลเดิมไปเรียกว่ารายชื่อแฟนคลับทั้งหมดหรือคอมเมนต์ทั้งหมด

### ThaiVirtualCreatorRegistry

main ณ เวลาวางแผน: `03da22ab49020058e4f6aec8e6892301556175f1`

Branch นอก main ที่พบ:

1. `chatgpt/discovery-20260918` — `fa4a80ef793e0e051c4766d00d17467f8a223a54`
2. `codex/task8-thaivtubersna-runner` — `2acfc3f44aefd19aa5b66aa1a0ec2cec7f3b62b7`
3. `fix/discovery-v2-cleanup` — `03da22ab49020058e4f6aec8e6892301556175f1`
4. `fix/identity-flow-20260917` — `fb3f5ab2e5b83f5e71e6a692eb5c2fa5f6c9e8b9`
5. `fix/persona-evidence-flow` — `51ee2e9838de8d04235f2998a980fb0a98306660`
6. `refactor/creator-link-pipeline` — `e718c0740c8d7c4807ea428dc90c406df835e966`

`fix/discovery-v2-cleanup` ชี้ commit เดียวกับ main ณ เวลาตรวจ ไม่ใช่งานค้างอีกชุดหนึ่ง

README ปัจจุบันระบุ `data/registry.json` เป็น source of truth ต้องเปลี่ยนเมื่อรวมระบบให้ Google Sheet เป็นทะเบียนหลักตามคำสั่งผู้ใช้

ข้อจำกัดของการอ่านรอบนี้: อ่าน repository และ config ไม่ได้เปิด workbook จริง ไม่ได้ตรวจ diff ทุก branch และไม่ได้ยืนยันว่า branch ใด merge แล้วจาก ancestry ทั้งหมด ชื่อคอลัมน์และตารางเพิ่มเติมด้านล่างเป็นแบบที่เสนอ ไม่ใช่คำกล่าวว่ามีอยู่แล้วในชีต

## 3. วิธีรวม repository และ branch

1. หยุด runner ซ้ำของสองโครงการระหว่างย้าย ไม่ลบ checkpoint หรือข้อมูล runtime เดิม
2. Fetch refs ล่าสุดของทั้งสอง repository และบันทึก branch tip ที่จะรวม การตรวจ ancestry เป็นการจัดการ Git ไม่ใช่การทดสอบข้อมูล
3. ใช้ tag ก่อนรวมอย่างละหนึ่งจุด ไม่สร้าง backup branch หรือสำเนาทั้ง repository เข้า main
4. รวมทุก branch ของ Registry เข้าสู่ main ของ Registry โดย branch ที่เป็น ancestor อยู่แล้วไม่ต้องสร้าง merge ปลอม
5. รวมทุก branch ของ SNA เข้าสู่ main ของ SNA ในลักษณะเดียวกัน
6. รวม main ที่รวบรวมแล้วของ Registry เข้าสู่ main ของ SNA โดยรักษาประวัติ ใช้ `--allow-unrelated-histories` เมื่อจำเป็น ไม่ใช้ squash แทนการรวมประวัติทั้งหมด
7. แก้ conflict โดยยึดหน้าที่: shell/navigation/graph ใช้ของ SNA เป็นฐาน; discovery/account mapping ใช้ของ Registry; metadata ที่ผู้ใช้ดูแลในชีตไม่ถูก JSON เก่าทับ; records ใหม่รวมด้วย stable IDs ไม่รวมเพียงเพราะชื่อเหมือน
8. ห้ามใช้ `-s ours` เพื่อทำให้ Git แสดงว่า merge แล้วแต่ทิ้งเนื้อหาอีกฝั่ง และห้ามเลือก ours/theirs แบบเหมาไฟล์ข้อมูลทั้งหมด
9. ย้ายเฉพาะโค้ดที่ใช้จริงเข้าสู่โครงสร้างหลัก ไม่เก็บโปรเจกต์สองชุดที่ต่างมี frontend, README สั่งงาน, worker และ deployment ของตัวเอง
10. เมื่อ tips ของ branch ที่ต้องรวมอยู่ในประวัติ main หลักแล้ว จึงเก็บกวาด branch งานที่รวมแล้ว ปิด workflow ซ้ำ และเปลี่ยน Registry เดิมเป็น read-only archive พร้อมชี้ไป repository หลัก
11. ไม่ force-push main และไม่ rewrite ประวัติเพื่อไล่ลดขนาด Git ในงานนี้ การรวมประวัติสอง repo ไม่ทำให้ .git เล็กลงทันที; สิ่งที่จะลดคือระบบที่ต้องดูแลและไฟล์ generated ที่เคยเพิ่มเข้ามาเรื่อย ๆ

การรวม branch ไม่ใช่การรับรองว่าโค้ดเก่าทุกชิ้นต้องยัง active ในเว็บใหม่ ประวัติอยู่ครบ แต่ runtime ต้องเหลือแบบเดียว

## 4. Tech stack และเส้นทางข้อมูล

เลือกใช้ HTML/CSS/JavaScript + Python ที่มีอยู่ เพราะไม่ต้องย้าย framework หรือสร้าง backend ใหม่เพียงเพื่ออ่าน dashboard

- Frontend: `web/index.html`, `web/site.js`, `web/site.css` เดิม เป็น shell ของ 5 tabs
- Graph: reuse renderer และ network controls เดิม
- Data processing: Python modules เดิม
- Master records และข้อมูลแก้ไขดูแล: Google Sheet เดิม
- ข้อมูลปฏิสัมพันธ์ดิบ/ประวัติที่มีอยู่: ใช้ Parquet และ DuckDB เดิม ไม่ย้ายทุกคอมเมนต์เข้า Sheet และไม่สร้าง database server ใหม่
- Website data: export JSON ขนาดเหมาะสม แยกตาม tab/channel/ช่วงเวลา โหลดเฉพาะเมื่อใช้
- Deployment: static site ปลายทางเดียว ใช้ Vercel project เดียวเป็นเป้าหมายของแผน ไม่แยก frontend เป็นหลายเว็บไซต์

Data flow:

```text
Google Sheet -> Python reader/aggregation -> website JSON -> 5 tabs
ข้อมูล interaction เดิม/ข้อมูลใหม่ -> DuckDB เดิม -> website JSON ชุดเดียวกัน
```

JSON ที่ export เป็นผลคำนวณและ cache อ่านอย่างเดียว ไม่ใช่ทะเบียนที่แก้ได้อีกชุดหนึ่ง แก้ทะเบียนที่ Sheet เท่านั้น

ใช้ entrypoint ใหม่เพียงตัวเดียว `scripts/update_site.py` เพื่ออ่านชีต ใช้ข้อมูลดิบที่มี คำนวณ และ export เว็บ โดยค่าเริ่มต้นไม่ยิง API เก็บข้อมูลใหม่ การเรียก collection ต้องเลือกโดยชัดแจ้งและ resume worker เดิม

ผล export, runtime data, log, credentials และข้อมูลการเงินที่ไม่ได้เปิดเผย ไม่ commit ลง public Git ต้อง export เฉพาะข้อมูลที่ตั้งใจแสดงบนเว็บไซต์ โดยข้อมูลการเงินที่เจ้าของไม่ได้อนุญาตให้เผยแพร่ไม่อยู่ใน static deployment สาธารณะ

เครื่องที่ทำ aggregation ใช้ storage เดิมของโครงการและ deploy ผลที่ export แล้ว ไม่ย้ายข้อมูลดิบไปอาศัย runner ชั่วคราวที่หายไปทุกครั้ง

## 5. ข้อมูลใน Google Sheet

ใช้แท็บเดิมก่อน แมปคอลัมน์ที่มีจริงขณะลงมือ เพิ่มเฉพาะข้อมูลที่ขาด ห้ามรื้อ workbook หรือ clear-and-rewrite จนสูตรและข้อมูลที่ผู้ใช้แก้ไว้เสีย

### ตารางหลักเชิงตรรกะ

| ตาราง | หน้าที่ | ฟิลด์ขั้นต่ำที่เว็บต้องใช้ |
|---|---|---|
| VTUBERS เดิม | หนึ่งแถวต่อ persona | persona_id, display_name, creator_type, status, status_as_of, affiliation_id, debut_date หรือ debut_year, source_url, updated_at |
| ACCOUNTS หากยังไม่มี | บัญชีสาธารณะของ persona | persona_id, platform, platform_account_id, handle, profile_url |
| SNAPSHOTS หากยังไม่มี | ยอดที่ผูกกับเวลา | platform, platform_account_id, observed_at, followers, views, source_url |
| EVENTS หากยังไม่มี | เดบิวต์ รีเดบิวต์ ย้ายค่าย พัก/จบกิจกรรม | event_id, persona_id, event_type, event_date หรือ event_year, related_persona_id เมื่อเปิดเผย, affiliation_id, source_url |
| GROUPS หากข้อมูลยังไม่มีที่เก็บ | ค่าย/กลุ่มที่มีชื่อจริง | affiliation_id, name, affiliation_type, source_url |
| FINANCE หากยังไม่มี | ยอดเงินที่มีข้อมูลรองรับ | record_id, persona_id หรือ affiliation_id, period, category, amount, currency, source_type, source_url, publication_allowed |
| NETWORK_RESULT เดิม | ผลสรุปคู่ช่อง | source_channel_id, target_channel_id, period, evidence_type, shared_accounts, source_accounts, target_accounts, overlap_from_source_pct, overlap_from_target_pct |
| SYSTEM เดิม | ข้อมูลรอบอัปเดต | last_success_at, collection_window, status, error_summary |

ตารางเหล่านี้เป็น logical datasets ไม่ได้บังคับสร้างชื่อแท็บใหม่ทุกชื่อ ถ้าแท็บเดิมเก็บข้อมูลเดียวกันอยู่แล้วให้ map และใช้ต่อ

### กฎนำข้อมูลสอง repo เข้าชีต

- รักษา persona_id เดิมที่ใช้งานได้ และใช้ mapping ของ IDs เมื่อต้นทางตั้งรหัสคนละระบบ
- ใช้ platform + stable account ID เพื่อกันบัญชีซ้ำ ไม่รวมชื่อคล้ายกันอัตโนมัติ
- ข้อมูลที่ผู้ใช้แก้ในชีตมีสิทธิ์เหนือ snapshot เก่า; เพิ่มข้อมูลใหม่และเติมช่องที่ว่าง แทนเขียนทับทั้งแถว
- Discovery ที่ยังไม่ชัดต้องค้นหาเจอพร้อมสถานะ ยังไม่บังคับรอ review ทั้งชุดก่อนเปิดเว็บ แต่ไม่เอาบัญชี/ลิงก์ที่ยังไม่รู้ว่าเป็นคนเดียวกันมาปั่นเป็นยอด persona ยืนยันแล้ว
- ไม่มี subscriber ขั้นต่ำในการเข้าทะเบียน และไม่มีเพดาน 1,370 ช่อง
- รองรับ creator ที่ไม่มี YouTube: อยู่ในทะเบียนและสถิติที่มีข้อมูลได้ ส่วน SNA ระบุแพลตฟอร์มที่มีหลักฐานจริง
- แยก virtual creator ประเภทอื่นออกจาก VTuber ในการนับด้วยฟิลด์ประเภท ไม่เหมารายการทุกแถวเป็น VTuber
- ไม่ทราบสถานะ/สังกัด/ยอด ให้เป็น unknown/null ไม่เปลี่ยนเป็น active/individual/0 โดยอัตโนมัติ

## 6. รายละเอียด 5 tabs

### Home

แสดงจำนวน VTuber personas ในทะเบียน จำนวนที่มีสถานะ active ตามข้อมูลล่าสุด สถานะไม่ทราบ จำนวนค่าย/กลุ่ม จำนวน independent ผู้ติดตามแยกแพลตฟอร์ม ยอดสรุปปฏิสัมพันธ์ และวันอัปเดตล่าสุด แต่ละตัวเลขกดไปยังรายการต้นทางได้

ต้องเขียนขอบเขตเป็น “ในทะเบียน ณ วันที่...” ไม่กล่าวอ้างว่าค้นพบวีไทยครบทั้งประเทศแล้ว

### VtuberRecord

ค้นด้วยชื่อ/ชื่อเดิม/handle กรองค่าย ประเภท สถานะ แพลตฟอร์ม และปีเดบิวต์ แสดงทุกบัญชี ผู้ติดตามล่าสุด วันที่ของยอด สังกัด และ timeline เดบิวต์/รีเดบิวต์/ย้ายค่าย กดไปยัง SNA ของคนนั้นได้

หน่วยทะเบียนเป็น persona; ร่างใหม่ให้ persona ใหม่เสมอ ไม่รวมเพราะเป็นคนพากย์คนเดิม ความเชื่อมโยงรีเดบิวต์ใช้เฉพาะการเปิดเผยจากเจ้าตัวหรือหลักฐานสาธารณะที่ยืนยันความเชื่อมโยง ไม่สืบชื่อจริงหรือเดาจากเสียง/ลายเส้น

### SNA

มีสามมุมมองในแท็บเดียว:

1. Creator -> Creator: แสดงว่า public account ที่เป็นของวี A ไปคอมเมนต์/ตอบที่ช่องหรือวิดีโอของวี B เมื่อไร กี่ครั้ง กี่วิดีโอ พร้อมลิงก์หลักฐาน กราฟมีทิศทาง
2. Audience overlap: สองช่องมีบัญชีผู้มีปฏิสัมพันธ์ร่วมกันกี่บัญชี คิดเป็นกี่เปอร์เซ็นต์ของฐานแต่ละช่อง พร้อมช่วงเวลาและประเภทหลักฐาน
3. Account list: บัญชีสาธารณะที่พบ ชื่อที่แสดง profile URL ช่องที่ไปคอมเมนต์ จำนวนคอมเมนต์หรือจำนวนวิดีโอที่พบตามข้อมูลที่เก็บได้ first/last observed และลิงก์หลักฐาน

มีทั้งตารางและกราฟ การเลือกเส้น A-B ต้องเปิดตัวเลขและรายการบัญชีที่เกี่ยวข้องได้ ไม่ส่งมอบเป็นกราฟที่ดูสวยแต่หาคำตอบไม่ได้

ให้เรียกบัญชีทั่วไปว่า “บัญชีผู้มีปฏิสัมพันธ์ที่พบ” ในคำอธิบาย ไม่ยืนยันว่าเป็นแฟนคลับหรือผู้ชมทั้งหมด และไม่ตีความว่า shared audience เท่ากับ creator สนิทกัน

### Data Analytics Dashboard

ตอบจำนวนเดบิวต์รายปี ปีที่เดบิวต์มากที่สุด แนวโน้มจำนวนและผู้ติดตาม จำนวนผู้มีเหตุการณ์รีเดบิวต์ต่อปี จำนวนเหตุการณ์รีเดบิวต์ และระยะห่างระหว่างเหตุการณ์เท่าที่มีวันจริง รวมถึงจำนวนค่าย/กลุ่ม สมาชิกและอันดับยอดตาม metric ที่เลือก

แยกกลุ่มสองชนิด:

- สังกัดจริง: agency / creator group / independent / unknown
- กลุ่มเครือข่าย: community ที่คำนวณจาก interaction หรือ shared audience

กลุ่มที่ algorithm หาได้ไม่กลายเป็นชื่อค่าย จำนวนสมาชิก ยอดติดตามรวมแยกแพลตฟอร์ม ค่ามัธยฐานต่อสมาชิก และการเติบโตเป็นคนละคอลัมน์ ไม่ใช้ centrality แทนความนิยม

เกณฑ์ขนาดค่ายเริ่มต้นที่เสนอ: เล็ก 1-5 personas, กลาง 6-19, ใหญ่ 20 ขึ้นไป แสดงเกณฑ์ให้เห็นและแก้ได้ เกณฑ์นี้เป็นการตั้งค่าโครงการ ไม่ใช่มาตรฐานอุตสาหกรรม

คนที่ไม่พบค่ายยังเป็น unknown ไม่ถูกนับเป็น independent จนกว่าจะมีข้อมูลรองรับ สังกัดปัจจุบันไม่ถูกย้อนใช้กับทุกปีย้อนหลัง

### Financial Data Analytics Dashboard

ใช้ขอบเขตเริ่มต้นเป็นยอดรายได้ที่มีบันทึก/หลักฐานของ persona หรือค่าย แยกเดือน ปี ประเภท และแหล่งข้อมูล ไม่สร้างคะแนนความรวยจาก followers

รองรับยอดสนับสนุนสาธารณะที่เก็บได้ และข้อมูลที่เจ้าตัว/ค่ายให้หรือเปิดเผยไว้ ข้อมูลจากเจ้าของที่ยังไม่อนุญาตให้เผยแพร่ไม่ export ไปเว็บสาธารณะ

แสดงรายได้ที่บันทึกได้ ค่าใช้จ่ายที่มีข้อมูล และผลต่างของรายการที่บันทึกได้ โดยแยกยอดสนับสนุนขั้นต้น รายได้จากแพลตฟอร์ม และรายได้สุทธิให้ถูกประเภท ไม่หักอัตราค่าธรรมเนียมเดาเอง

ไม่รวมเงินคนละสกุลโดยตรง; แยกสกุลเงินก่อน หากมีอัตราแลกเปลี่ยนที่อ้างอิงได้จึงแสดงยอดแปลงพร้อมวันที่และอัตรา

แหล่งรายได้ไม่ครบต้องแสดงความครอบคลุมและไม่กล่าวว่าเป็นรายได้ทั้งหมด ข้อมูลว่างให้เป็น “ยังไม่มีข้อมูล” ไม่ใส่ 0 หรือ generated estimates เพื่อให้กราฟดูเต็ม

YouTube Analytics รายช่องและข้อมูล monetary ต้องได้รับการอนุญาตจากเจ้าของช่อง ไม่สามารถเรียกดูรายได้หลังบ้านทุกช่องด้วย public API key ของโครงการ

## 7. นิยามตัวเลขที่ใช้จริง

### จำนวนวีและผู้ติดตาม

- จำนวนวี: distinct persona_id ที่อยู่ในขอบเขต VTuber ตามทะเบียน แยกสถานะ
- จำนวนบัญชี: distinct platform + platform_account_id เป็นอีกตัวเลขหนึ่ง
- ผู้ติดตาม: ล่าสุดที่มี observed_at ต่อบัญชี แสดงแพลตฟอร์มและวันที่ ยอดรวมหลายช่อง/หลายแพลตฟอร์มเป็นผลรวม follower counts ไม่ใช่ unique people
- การเติบโต: คำนวณเมื่อมี snapshot อย่างน้อยสองเวลาที่เทียบกันได้ ไม่สร้างยอดย้อนหลังจากยอดวันนี้
- YouTube subscriberCount สาธารณะมีการปัดเป็นสามเลขนัยสำคัญ ไม่แสดงความละเอียดเกินข้อมูล

### เดบิวต์และรีเดบิวต์

- ปีเดบิวต์มาจากข้อมูล event ของ persona ไม่ใช้วันที่สร้างบัญชีแทนโดยเงียบ ๆ
- วันที่ทราบแค่ปีคงความละเอียดระดับปี ไม่ประดิษฐ์วันที่ 1 มกราคม
- จำนวนรีเดบิวต์รายปีแยก distinct personas ที่มีเหตุการณ์ และจำนวน event ทั้งหมด
- อัตรารีเดบิวต์แบบตั้งต้น = จำนวน personas ที่มี redebut event ในปี / จำนวน personas ที่บันทึกว่า active ในปีเดียวกัน x 100 ถ้าไม่มีประวัติ active ที่พอระบุตัวหารได้ ให้แสดงเฉพาะจำนวน ไม่สร้างเปอร์เซ็นต์
- ระบุวิธีนับร่างใหม่ให้ชัดตามกฎ persona separation; การเชื่อม event ไม่ใช่การ merge persona
- ปี 2026 เป็น YTD ตามวันตัดข้อมูล ไม่เทียบ 2026 ที่ยังไม่จบกับปีเต็มโดยไม่ระบุ และใช้ช่วงวันเท่ากันเมื่อต้องการเปรียบเทียบการเติบโต

### Overlap

ให้ A และ B เป็นเซตบัญชีสาธารณะที่พบมีปฏิสัมพันธ์กับช่อง A/B ภายในแพลตฟอร์ม ช่วงเวลา และ evidence type เดียวกัน

```text
shared_accounts = |A intersect B|
overlap_from_A_pct = shared_accounts / |A| x 100
overlap_from_B_pct = shared_accounts / |B| x 100
jaccard = shared_accounts / |A union B|
```

ถ้าตัวหารเป็นศูนย์แสดง N/A ไม่ใช่ 0% ที่ดูเหมือนมีการสังเกตแล้ว

ตัวอย่างสมมติ: A มี 1,000 บัญชี, B มี 400, ร่วมกัน 200 จึงเป็น 20% ของ A และ 50% ของ B ตัวเลขนี้ไม่ได้แปลว่า 20% ของผู้ชมทั้งหมดของ A ดู B

เลือก comments, live_chat หรือ union ได้ สำหรับ union ต้อง distinct actor IDs ไม่บวกจำนวนสองประเภทตรง ๆ

เก็บ `strong_shared_live_chat` เดิมไว้เป็นตัวกรองทางเลือก: actor เดียวกันพบใน live chat อย่างน้อย 2 distinct video_id ต่อช่องทั้ง A และ B ไม่ใช้เป็นเงื่อนไขบังคับของทุกมุมมอง

ความคิดเห็นใต้วิดีโอไลฟ์ย้อนหลังไม่ถูกนับเป็น live attendance; ใช้ `videos_seen` ทั่วไป และ `live_streams_seen` เฉพาะ live_chat

ข้อมูลที่มีแต่ presence ต่อวิดีโอใช้ตอบจำนวนบัญชี/วิดีโอที่พบ ไม่เรียกจำนวนแถว presence ว่าจำนวนคอมเมนต์จริง

## 8. บัญชีผู้มีปฏิสัมพันธ์และการเก็บต่อ

ฟิลด์ใหม่ขั้นต่ำ: platform, actor_account_id, actor_display_name, actor_profile_url, target_channel_id, video_id, comment_id หรือ message_id, parent_comment_id เมื่อมี, source_type, published_at, observed_at, source_url

- Stable key เป็น platform + public account ID ไม่ใช่ display name ที่อาจเปลี่ยนหรือซ้ำ
- ข้อมูลใหม่ไม่ผ่าน HMAC
- จับ account ID กับบัญชีทางการในทะเบียนเพื่อแยก creator interaction จากบัญชีทั่วไป
- ไม่ต้องเก็บเนื้อหาคอมเมนต์เต็มเพื่อทำ count/overlap; เก็บลิงก์หลักฐานและตัวระบุที่จำเป็นก่อน
- กันการนับซ้ำด้วย comment/message ID ระหว่างการ resume ไม่ตั้ง validation pipeline ใหม่
- การดึง replies ใช้ pagination ที่รองรับจริง เพราะ replies ที่ติดมากับ commentThreads อาจไม่ครบ
- ค่าเริ่มต้นของหน้าเว็บใช้ข้อมูลที่มีอยู่ การเก็บเพิ่มทำเฉพาะช่อง/ช่วงเวลาที่ต้องเติมและ resume checkpoint เดิม ไม่ backfill ทุกปีทุกช่องทันที
- ไม่เปิด paid API หรือพยายามหลบ quota; ไม่มีข้อมูลจากแพลตฟอร์มใดให้บอกตรง ๆ และยังแสดงช่องทางนั้นในทะเบียนได้
- ไม่รับรองว่า API ดึงรายชื่อผู้ชมเงียบหรือ live chat ย้อนหลังที่ไม่ได้เก็บไว้ได้ทั้งหมด

### ข้อมูล HMAC เดิม

ค่า HMAC เดิมไม่สามารถย้อนกลับเป็นชื่อได้ด้วยตัวมันเอง ใช้ mapping ที่มีอยู่ หรือจับ public IDs ที่ดึงมาได้กับค่า HMAC โดยใช้ key เดิมเมื่อมี เท่านี้ก็เพียงพอสำหรับการย้ายครั้งเดียว ไม่สร้างระบบ key management ใหม่

ถ้าไม่มี mapping หรือ key ให้เก็บ historical aggregate ต่อไป และระบุว่าชุดเก่านี้ไม่มีรายชื่อบัญชีที่กู้ได้ ไม่เดาชื่อ ไม่ทิ้งผลย้อนหลัง และไม่เริ่มเก็บใหม่ทั้งระบบเพียงเพื่อแทนที่ hash

actor แบบ legacy hash และ public ID ที่ยังจับคู่ไม่ได้ต้องไม่ถูกบวกนับเป็นสองคนในช่วงเดียวกัน แยกผลเป็น legacy กับ identified dataset จนกว่าจะมี mapping; อย่าอ้าง longitudinal identity continuity ที่ยังเชื่อมไม่ได้

## 9. ลำดับดำเนินงาน 7 ขั้น

### ขั้น 1 — รวม repo/branch และตั้ง shell เดียว

ทำตามขั้นตอน Git ในหัวข้อ 3 แก้ `web/index.html`, `web/site.js`, `web/site.css` ให้มี routes Home, VtuberRecord, SNA, Data Analytics, Financial Analytics โดย reuse network/research code ที่มีอยู่

ปิด entrypoint/workflow ซ้ำ ไม่สร้าง frontend อีกชุดหรือ wrapper ที่เพียง iframe เว็บเก่าสองเว็บเข้าด้วยกัน

ผลส่งมอบ: main เดียวเป็นที่ทำงานต่อ และเปิด shell ที่นำทางครบ 5 tabs ได้ รายงาน commit ที่เกิดจริง ไม่กล่าวว่า merge แล้วจากแค่สร้างแผน

### ขั้น 2 — Sheet -> VtuberRecord + Home

ปรับ reader ใน `storage/` ที่ใช้อยู่ ให้เข้าถึง workbook จาก `VTUBER_SPREADSHEET_ID` เดิม นำ records ที่จำเป็นจาก Registry เข้าชีตครั้งเดียวโดยไม่ทับสูตร/ข้อมูลแก้ไขเอง เติม account mapping และ export ผ่าน `scripts/update_site.py`

เพิ่ม record/home view ภายใต้ web เดิม แสดง counts, ชื่อ, platform links, followers ที่มีข้อมูล และตัวกรอง ดึงข้อมูลจาก Sheet ไม่ใช้ mock catalog

ผลส่งมอบ: เปิดเว็บดูทะเบียนและภาพรวมจริงได้ตั้งแต่ขั้นนี้ รวมผู้ค้นพบเพิ่ม ไม่ล็อกไว้ที่ 1,370 และไม่ตัดผู้ติดตามน้อยกว่า 100

### ขั้น 3 — SNA ที่กดหาคำตอบได้จากข้อมูลเดิม

ต่อ graph เดิมกับ record ที่นำเข้า เพิ่มตารางคู่ช่อง shared count, %A, %B และตัวเลือกช่วงเวลา/comments/live_chat ใช้ analytics และ DuckDB เดิม

ผลส่งมอบ: เลือกวี A และ B แล้วเห็น overlap ที่คำนวณจากข้อมูลจริงพร้อมขอบเขต ไม่ต้องรอเก็บข้อมูลใหม่หรือ review ทะเบียนทุกคนให้เสร็จ

### ขั้น 4 — Creator interaction + รายชื่อ public accounts

ปรับ collector ที่ใช้งานจริงให้เก็บ public actor ID/display name ก่อนขั้น hash และเก็บหลักฐานของ top-level comments/replies ตามข้อมูลที่ดึงได้ สร้าง directed edges จาก actor accounts ที่ตรงกับทะเบียน

เชื่อมชุดที่เก็บใหม่หรือชุดเดิมที่มี mapping ให้ account list และช่อง A-B ที่เลือก หลีกเลี่ยงการ backfill แบบไม่จำกัดงบ

ผลส่งมอบ: ดูได้ว่า public creator account ใดไปเมนต์ช่องใด และเปิดบัญชีผู้มีปฏิสัมพันธ์ที่เก็บได้จริงได้ ข้อมูล legacy ที่ไม่มี mapping แสดงขอบเขตแยก ไม่ใส่ชื่อสมมติ

### ขั้น 5 — Data Analytics: รายปีและค่าย/กลุ่ม

ใช้ snapshots/events/affiliations ที่มีใน Sheet หรือข้อมูลเดิมที่นำเข้า เพิ่มกราฟ debut/redebut, อันดับปี, followers ตามเวลา, ประเภทค่าย/independent และ network communities พร้อมตารางรายชื่อสมาชิก

ผลส่งมอบ: จำนวนและกราฟเชื่อมไปยัง rows/events ที่ทำให้เกิดผลได้ ข้อมูลไม่ทราบวันหรือไม่มีประวัติไม่ถูกใช้ประดิษฐ์แนวโน้ม

### ขั้น 6 — Financial Analytics

อ่านรายการการเงินจากชีตที่มีสิทธิ์ใช้และสิทธิ์เผยแพร่ แยก public observations กับข้อมูลจากเจ้าของ และไม่เปิดข้อมูลส่วนตัวเพราะมันอยู่ใน workbook เดียวกัน

ผลส่งมอบ: แสดงรายงานจริงของข้อมูลที่มีพร้อมหน่วยเงิน/ช่วงเวลา/แหล่งที่มา ถ้ายังไม่มีรายการการเงินจริง ให้ระบุว่า UI/reader พร้อมแต่ความต้องการด้านรายงานเงินจริงยังไม่ครบ ไม่รายงานว่าทำ Financial Dashboard สำเร็จครบโจทย์ด้วยหน้า empty state อย่างเดียว

### ขั้น 7 — Publish และเก็บกวาด

Export ชุดปัจจุบันและ publish ไป static deployment เดียว จัด navigation และ links ให้ทั้งหมดอยู่ในเว็บเดียว แก้เฉพาะปัญหาเปิดหน้า/โหลดข้อมูลจริงที่พบ

ถอด runtime ที่ไม่ใช้ fixture/รายงาน generated และไฟล์ export ขนาดใหญ่ออกจาก tracked tree โดยไม่ลบข้อมูลทำงานจริงที่ยังต้องใช้ เหลือเอกสารวิธี run/update/deploy สั้น ๆ หนึ่งชุด

ผลส่งมอบ: URL ที่เปิดได้จริง, commit ล่าสุด, วันที่ข้อมูลของแต่ละ tab และรายการความสามารถที่ทำงานแล้ว/ยังขาดข้อมูล บอกสถานะตามจริงโดยไม่มีคำว่า “ผ่านทุกเทส” เพราะไม่ได้ทำรอบทดสอบข้อมูล

## 10. วิธีคุมไม่ให้โครงการบวมอีก

ทำตาม 7 ขั้นเรียงกันใน main ไม่แตก subproject ไม่เรียกหลาย agent ให้เปลี่ยนไฟล์เดียวกัน ไม่เขียนเอกสารแผนเพิ่มซ้ำ ไม่เปลี่ยน framework ระหว่างงาน ไม่เพิ่ม abstraction ที่ยังไม่มีหน้าจอใช้ และไม่สร้าง feature ใหม่จากความคิดของผู้ทำเอง

ทุกช่วงส่งงานรายงานเพียง:

- เปลี่ยนอะไร
- เปิดดูผลตรงไหน
- commit ใด
- ข้อมูลส่วนไหนยังขาดหรือผิดพลาดจริง

ความคืบหน้าวัดจากคำถามของผู้ใช้ที่เว็บตอบได้ ไม่วัดจากจำนวนไฟล์ สคริปต์ test หรือรายงานที่ผลิต

## 11. เกณฑ์จบงาน

ผู้ใช้เปิดเว็บไซต์เดียวแล้วค้นวีหนึ่ง persona ได้ เห็นช่องทาง ยอดที่มีวันกำกับ สังกัดและ timeline จากนั้นเปิด SNA เห็น creator interaction, shared-account counts, สัดส่วนที่มีตัวหารชัด และบัญชีสาธารณะที่มีหลักฐาน รวมทั้งเปิดดูการเปรียบเทียบปี/กลุ่มและรายการการเงินที่มีแหล่งข้อมูลจริง

รายการที่ไม่มีข้อมูลต้องบอกตรง ๆ แต่การมี placeholder ไม่ถือว่าเติมความต้องการนั้นสำเร็จ ความไม่ครบต้องผูกกับข้อมูลเฉพาะส่วน ไม่กลายเป็นข้ออ้างหยุดส่งเว็บทั้งระบบ

## แหล่งข้อมูลที่อ่านประกอบแผน

1. ThaiVtuberSNA, README และ docs/PROJECT.md, main ณ 20 กันยายน 2026
2. ThaiVtuberSNA, config/settings.py
3. ThaiVtuberSNA, storage/duckdb_engine.py
4. ThaiVirtualCreatorRegistry, README
5. GitHub branch listings ของทั้งสอง repository ณ วันที่วางแผน ไม่ใช่การยืนยันว่า refs จะไม่เปลี่ยนหลังจากนั้น
6. Google YouTube Data API — Comments
7. Google YouTube Data API — CommentThreads
8. Google YouTube Analytics API — Channel Reports
9. Google YouTube Data API — Channels

ข้อกำหนด schema, thresholds, file ใหม่ และลำดับงานเป็นข้อเสนอในแผน ไม่ใช่สิ่งที่ตรวจพบว่าทำเสร็จแล้ว
