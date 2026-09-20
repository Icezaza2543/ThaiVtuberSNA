# วิธีค้นหาและขอบเขตแพลตฟอร์ม

เริ่มจากลิงก์ที่เจ้าตัวเผยแพร่ในบัญชี YouTube ตั้งต้น หน้าแนะนำตัว เว็บไซต์ค่าย และ link-in-bio แล้วเสริมด้วยการค้นหาแพลตฟอร์มและการส่งรายชื่อโดยครีเอเตอร์ ช่องที่ไม่มี YouTube อยู่ในทะเบียนได้

ชุดคำค้น: VTuberTH, ThaiVTuber, วีทูบเบอร์ไทย, วีทูปเบอร์, PNGTuber, VSinger, Virtual Idol, เดบิวต์, รีเดบิวต์, เปิดตัวโมเดล, graduation, ยุติบทบาท, พักกิจกรรม, rebrand, กลับมา

## Twitch

รอบ 2026-09-13 ใช้ `registry.twitch_public` อ่านโปรไฟล์สาธารณะจริงจาก Twitch รวมคำแนะนำตัวและ social links โดยไม่มี OAuth อ่าน public website application ID จากหน้า Twitch ที่ runtime และเก็บเฉพาะข้อมูลสาธารณะที่เลือกไว้ ไม่เก็บ raw response, request IDs, session, แชต, รายชื่อผู้ชม หรือข้อความขอบคุณผู้บริจาค ชื่อ login ต้องตรง หรือ numeric user_id ต้องตรงเมื่อค้นด้วยรหัสเดิม; response ว่างและข้อผิดพลาดไม่ผ่านการ resolve

คิวมาจาก VTuberThaiInfo archive, vdb JSON, Thai ranking JSON, HoloList หมวดไทย, Bācharu ประเทศ/ภาษาไทย และลิงก์ของเจ้าของ YouTube ตรวจ 730 ชื่อและ 63 numeric ID พบ 689 ID ไม่ซ้ำ คัดเข้าทะเบียน 646 บัญชี และยืนยัน 217 persona-account links ดู [รายงานรอบ Twitch](../intake/archive/2026-09-13/2026-09-13-twitch-collection-report.md) บัญชีที่ยังไม่มี scope review ไม่ถูกนับเป็น VTuber ที่ยืนยันแล้ว

รายงานสร้าง `twitch_accounts.csv` และ `verified_twitch.csv` โดยใช้วันอ้างอิงและกติกาเดียวกับ TikTok ช่องออฟไลน์หรือคำอธิบายเก่าไม่ใช้สรุปกิจกรรม การเปลี่ยน login ของ user_id เดิมไม่ใช่หลักฐาน continuity ระหว่าง persona

มีคำสั่ง `twitch-discover` ที่เรียก Helix Get Streams แบบจำกัดหน้าและกรองภาษา ตรวจ candidate ทุกรายก่อนยืนยัน เพราะภาษาไทยอย่างเดียวไม่บอกว่าเป็น VTuber และผู้ใช้ภาษาอื่นก็อาจเกี่ยวข้องกับไทยได้

เก็บแต่ user ID, ชื่อบัญชี, URL และที่มาของการพบ ไม่เก็บแชต ผู้ติดตาม หรือผู้ชม ตัว adapter ยังไม่ได้ทดสอบกับ credential จริง; unit tests ใช้ response จำลอง รวม pagination และ HTTP error

Get Streams เปลี่ยนตามเวลาจริงและอาจซ้ำ/หล่นระหว่างแบ่งหน้า ผล `end_of_results` หมายถึงจบผลลัพธ์ของรอบนั้น ไม่ใช่ค้นพบ VTuber ครบทั้งแพลตฟอร์ม Search Channels จำกัดช่องที่เคยสตรีมในหกเดือนล่าสุดและจับคู่ชื่อ จึงเหมาะช่วย resolve ชื่อที่มีอยู่มากกว่าทำ census [Twitch API](https://dev.twitch.tv/docs/api/reference/)

แผน pilot ที่เสนอ: รันหลายช่วงเวลาและวันในสัปดาห์ บันทึกจำนวน run, leads ใหม่, จำนวนที่ยืนยันแล้ว และช่องที่ซ้ำ ไม่มี automation เปิดอยู่ใน repo นี้

## TikTok

มีตัวเก็บ public creator profile ที่รันจริงแล้วใน `registry/tiktok.py` ใช้ลิงก์ที่พบจากหน้าแนะนำตัวเจ้าของช่องและไดเรกทอรีสาธารณะ อ่าน [TikTok creator embed](https://developers.tiktok.com/doc/embed-creator-profiles) โดยไม่ใช้ login หรือ session ของผู้ใช้

```sh
python -m registry.tiktok --input intake/archive/2026-09-13/2026-09-13-tiktok-profile-queue-03.json --output intake/tiktok-next-observation.jsonl --workers 6
```

ไฟล์ input เป็นรายการ URL โปรไฟล์จริงพร้อมแหล่งที่มา และต้องไม่มี handle ซ้ำ output ต้องเป็นชื่อใหม่ จำกัด 1–8 workers, timeout 25 วินาที และ response ไม่เกิน 2 MB ต่อโปรไฟล์ ผลทุกแถวบันทึกทันที มีผล resolved/unresolved และตัวนับความคืบหน้า

ตรวจ numeric `userInfo.id` ใน public embed, `uniqueId` ตรงกับ handle ที่ร้องขอ, `privateAccount=false` และ code สำเร็จ เก็บเป็น `web_user_id` ไม่ปะปนกับ `open_id`/`union_id` ชื่อและ handle เป็น alias ไม่ใช่รหัสบัญชี ไม่เก็บ raw HTML, session, signed media, chat หรือข้อมูลผู้ชม bio และคำบรรยายวิดีโอจำกัดความยาวและละข้อมูลติดต่อ/คำขอบคุณผู้บริจาค

การอ่าน embed เป็นการตรวจ URL ที่มีอยู่ ไม่ใช่ API ค้นหาทุกช่องใน TikTok และไม่ได้รับรอง persona อัตโนมัติ ผลที่ตรวจแล้วถูกเตรียมเป็น reviewed changes ก่อนบันทึกลงทะเบียน Persona ต้องมีหลักฐานเจ้าตัวเกี่ยวกับการเป็นครีเอเตอร์เสมือนและความเกี่ยวข้องกับไทย ลิงก์ค่ายหรือกลุ่มไม่ถูกถือเป็นบัญชีเฉพาะของ persona

รอบ 2026-09-13 ตรวจ 1,011 TikTok URL ได้ 863 บัญชีจริง ยืนยัน 390 persona บน 391 บัญชี ส่วน 148 URL ตอบ HTTP 400 จาก embed คงสถานะ unresolved วิธีนี้ไม่บอกว่าบัญชีถูกลบหรือหยุดกิจกรรม ดู [ผลการเก็บข้อมูลและขอบเขตแหล่งที่ค้น](../intake/archive/2026-09-13/2026-09-13-resolution-report.md)

มีสคริปต์ `scripts/collect/collect_youtube_about.py` สำหรับอ่าน owner-written About metadata และ social links โดยตรวจ channel ID ที่ทราบแล้ว ใช้ `--input` เพื่อระบุช่อง และ `--output` เป็นชื่อไฟล์ใหม่ แยกข้อมูลคำอธิบาย/ลิงก์ของเจ้าของช่องออกจากเนื้อหาแนะนำและข้อมูลผู้ชม

```sh
python scripts/collect/collect_youtube_about.py --input intake/archive/2026-09-13/2026-09-13-youtube-additional-queue.json --output intake/youtube-next-crosslinks.jsonl
```

[Research API](https://developers.tiktok.com/products/research-api) ยังต้องมีสิทธิ์ที่ได้รับอนุมัติ และไม่ได้ถูกใช้ในรอบนี้ ไม่มี scheduler เปิดอยู่ การค้นหา/เก็บสดรอบถัดไปต้องมีคำขอของเจ้าของโครงการ

## Facebook

ค้น Page ค่าย โพสต์ประกาศ persona งานอีเวนต์ และ public creator Pages พร้อม official cross-links จากนั้นบันทึก candidate และหลักฐาน URL เครื่องมือ Meta Content Library/API เปิดให้ผู้วิจัยที่ผ่านเกณฑ์สถาบัน ไม่ใช่สิทธิ์ที่มากับ repo [Meta Content Library](https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/)

ยังไม่มี Graph API collector หรือ Facebook scraper การเพิ่มบัญชีที่ได้มาด้วยวิธีที่เหมาะสมทำได้ผ่านชุด review อย่าเก็บสมาชิกกลุ่มหรือโปรไฟล์ส่วนตัวที่ไม่เกี่ยวกับ persona สาธารณะ

## การค้นหาหลายแพลตฟอร์มด้วย Playwright (Multi-platform Playwright Discovery v2)

รองรับการค้นหาอัตโนมัติบนหน้าเว็บสาธารณะด้วยเบราว์เซอร์ Chromium ผ่าน Playwright โดยไม่ต้องใช้ API key และไม่มี dependency ของโมเดลภาษา (LLM) ผ่านคำสั่ง `discover-all`:

### สถานะความพร้อมของแต่ละแพลตฟอร์ม (Platform Status)

1. **Core Tested Platforms**:
   - `youtube`: ค้นหาช่องจากผลค้นหาและโปรไฟล์ `@handle` หรือ `/channel/UC...` รองรับ bounded scroll และ empty-state assertions
   - `twitch`: ค้นหาช่องสตรีมเมอร์สาธารณะ (รองรับ DOM card selector ล่าสุด) พร้อม runtime Client-ID GQL resolver สำหรับ numeric `user_id` โดยไม่มี credential hardcoded
   - `tiktok`: ค้นหาผู้ใช้สาธารณะ (guest search มักติด `login_required`) พร้อม public creator embed resolver สำหรับ numeric `web_user_id`
   - `ganknow`: ทำหน้าที่เป็นทั้งแพลตฟอร์มและ Discovery hub ค้นหาโปรไฟล์ครีเอเตอร์บน GankNow และเปิดหน้าโปรไฟล์จริงเพื่อดึง outbound social links และ personal websites แบบ bounded crawl (depth 1–2)

2. **Experimental Public Surface Platforms** (อาจพบ Login wall หรือ Rate limit ตามนโยบายของแพลตฟอร์ม):
   - `facebook` (Experimental): ค้นหา Public Pages ของครีเอเตอร์/ค่าย (ตรวจจับ login wall)
   - `instagram` (Experimental): ค้นหาแท็ก/โปรไฟล์สาธารณะ (ตรวจจับ login wall)
   - `x` / Twitter (Experimental): ค้นหาบัญชีครีเอเตอร์สาธารณะ (ตรวจจับ rate limit และ login modal)
   - `kick` (Experimental): ค้นหาช่องสตรีมเมอร์สาธารณะ
   - `bilibili` (Experimental): ค้นหา UP Host พร้อม numeric UID
   - `niconico` (Experimental): ค้นหาผู้ใช้ Niconico พร้อม numeric user ID

3. **Discovery-support Surfaces และ Link Hubs**:
   - `carrd`, `linktree`, `litlink`, `kofi`, `patreon`, `vgen`, `website`
   - หน้า link hub และ personal website ใช้เป็นแหล่งดึง outbound cross-links แบบจำกัดไม่เกิน 2 hops ไปยังแพลตฟอร์มหลัก แต่ไม่ถูกนำมาเชื่อมโยงเป็น persona เดียวกันโดยอัตโนมัติ

### สถาปัตยกรรม Provenance และการแยก Entity Dedupe ออกจาก Discovery Observation

1. **Exact Per-Execution Run Provenance**:
   - แต่ละ execution จะถูกบันทึกแยกเป็น `discovery_run` อย่างชัดเจนตาม `(platform, query, method, source_url)` พร้อม `observed_at`, `pages_seen`, `records_seen` และ `stop_reason`
   - ค่า `pages_seen` หมายถึง bounded navigation/scroll cycles ที่เกิดขึ้นจริง
   - ค่า `records_seen` สะท้อนจำนวนรายการที่ DOM หรือหน้าเว็บสแกนจริงจาก adapter
   - ทุกคำค้นและทุกแหล่ง cross-link มี run ID ของตนเองที่ตรวจสอบย้อนกลับได้
2. **Preserved Discovery Hits and Evidence**:
   - Entity deduplication ถูกแยกออกจากการสังเกตการณ์ (observation): candidate/account จะมีเพียง 1 แถวในตาราง `candidates` หรือ `accounts`
   - ทุกครั้งที่พบครีเอเตอร์จากคำค้นต่างกัน หรือพบผ่าน cross-link ของ creator profile ต่างกัน ระบบจะสร้าง `discovery_hits` และ `evidence` แถวใหม่เชื่อมโยงกับ run และ source_url นั้นเสมอ ไม่ collapse หรือทิ้งประวัติการพบซ้ำ
   - ตัวอย่าง: หากครีเอเตอร์ Alice และ Bob ต่างวางลิงก์ไปยัง YouTube ช่องเดียวกัน ระบบจะเก็บ 1 candidate แต่สร้าง 2 discovery runs, 2 discovery hits และ 2 evidence rows โดยมี `source_url` ชี้กลับไปยัง Alice และ Bob ตามลำดับ

### Bounded Pagination และ Browser Readiness

- ตัวเลือก `--max-pages` ทำงานร่วมกับ infinite scrolling / pagination จริง โดยเลื่อนหน้าและรอ DOM stabilization จนกว่าจะถึง `max_results`, `max_pages`, หรือไม่พบผลลัพธ์ใหม่
- `pages` ในรายงานหมายถึง bounded navigation/scroll cycles ไม่จำเป็นต้องเป็น numbered HTTP page
- มี readiness checks (`wait_for_selector`) สำหรับ container และการ์ดผลการค้นหาก่อนดึงข้อมูล ป้องกัน race condition จาก SPA rendering

### Personal Website Hop (Bounded Depth = 2) และการป้องกัน SSRF

- รองรับการเปิด personal website ที่ครีเอเตอร์เชื่อมโยงไว้ในหน้าโปรไฟล์ (เช่น `creator profile -> personal website -> known platform`)
- กำหนดขอบเขตความปลอดภัยอย่างเคร่งครัด:
  - จำกัดไม่เกิน 2 personal websites ต่อครีเอเตอร์
  - จำกัดลิงก์ขาออกไม่เกินโควตา (bounded links)
  - รองรับเฉพาะ HTTPS สาธารณะ
  - ไม่เปิดหน้าภายในเว็บไซต์ซ้ำ (landing page only)
  - สกัดเฉพาะลิงก์ไปยังแพลตฟอร์มหลักที่รู้จัก
- **การป้องกัน SSRF และ Local Network Navigation Guard (`registry.discovery.network_safety`)**:
  - ตรวจสอบ URL อย่างเข้มงวดก่อนเปิดเบราว์เซอร์ (`is_safe_public_http_url` / `validate_public_navigation_url`):
    - Scheme ต้องเป็น `https` เท่านั้น และห้ามมี userinfo (`username:password`)
    - Reject `localhost`, `.localhost`, `.local`, `.internal`, `.lan`, `broadcasthost`
    - Reject IP literals ที่เป็น loopback (`127.0.0.0/8`, `::1`), private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), link-local (`169.254.0.0/16`, `fe80::/10`), multicast, CGNAT (`100.64.0.0/10`), unspecified (`0.0.0.0`, `::`)
    - Resolve DNS ล่วงหน้า และปฏิเสธหากปลายทางชี้ไปยัง private/local network
  - **Redirect Safety**: ใช้ `safe_goto` ดัก route requests ของ Playwright เพื่อ abort navigation (`blockedbyclient`) หากมีการ redirect ไปยัง private/internal IP และตรวจทาน final URL หลังโหลดเสร็จ
  - **DNS Rebinding Limitation**: ระบบตรวจสอบ IP ทั้งก่อน navigation และตรวจสอบ final URL รวมถึง intercept redirect requests แต่เนื่องจากเบราว์เซอร์ภายในอาจทำการ resolve DNS อิสระในแต่ละ socket connection ระบบจึงดักจับ navigation requests ทั้งหมดเพื่อลดความเสี่ยง SSRF โดยไม่ต้องตั้ง network sandbox ภายนอก
  - หาก URL ไม่ปลอดภัยหรือ resolve เข้า local network: ระบบจะไม่สร้าง website candidate และจะไม่เปิดในเบราว์เซอร์เด็ดขาด
- **การกรอง Same-site Navigation ใน Crosslink Discovery**:
  - ใน `extract_crosslinks()` กำหนด `allow_same_host=False` เป็นค่าตั้งต้น เพื่อสกัดเฉพาะลิงก์ outbound ไปยังแพลตฟอร์มอื่น
  - ข้าม internal links บนโฮสต์เดียวกัน เช่น หน้าข้อกำหนด/นโยบาย/ร้านค้าบน GankNow (`ganknow.com/terms`, `ganknow.com/shop`) หรือหน้าย่อยบน personal website (`creator.example/about`) ไม่ให้หลุดเข้าไปเป็น creator candidate
  - สำหรับ Link Hubs (Linktree, Carrd, Litlink): สกัดเฉพาะ outbound cross-links และ personal website ข้าม internal hub pages (`linktr.ee/privacy`)
- **ข้อกำหนดความปลอดภัยด้านอัตลักษณ์**: Personal website เป็นเพียง discovery source ห้ามนำมาเชื่อมโยงเป็น persona เดียวกันหรือยืนยัน persona โดยอัตโนมัติเด็ดขาด บัญชี website จะคงสถานะ `needs_evidence`

### Selector Assertions และการแยก `selector_changed`

เพื่อป้องกันปัญหาเงียบ (silent failure) เมื่อโครงสร้าง DOM ของหน้าเว็บเปลี่ยนไป:
- หากพบผลลัพธ์: รายงานสถานะ `completed`
- หากไม่พบผลลัพธ์ แต่ตรวจพบข้อความ official empty-state (เช่น "No results found" หรือ "ไม่พบผลลัพธ์"): รายงานสถานะ `completed` พร้อม 0 hits
- หากไม่พบทั้งผลลัพธ์และ empty-state: รายงานสถานะ `selector_changed` เพื่อแจ้งเตือนผู้ดูแลระบบให้ตรวจสอบ selectors ของแพลตฟอร์มนั้น

### Stable ID Enrichment และ Concurrent Single-Flight Resolver

- สำหรับ Twitch: อ่าน public website application ID จากหน้า Twitch ที่ runtime (reuse logic จาก `registry/twitch_public.py` โดยไม่มี hardcoded credential) แล้ว resolve numeric `user_id` ผ่าน public GQL
- สำหรับ TikTok: reuse logic จาก `registry/tiktok.py` สกัด numeric `web_user_id` จาก public embed JSON
- **Concurrent Bounded Execution**: รันการ enrich batch leads แบบ concurrent จริงด้วย `asyncio.gather` ภายใต้ `asyncio.Semaphore(4)` เพื่อควบคุมภาระงานบน event loop
- **Single-Flight In-Flight Deduplication**: ป้องกัน race condition เมื่อพบ handle เดียวกันพร้อมกันหลาย task (เช่น `twitch/alice` ปรากฏพร้อมกัน 5 leads)
  - Task แรกจะทำหน้าที่เป็น initiator ยิง network request เพียง 1 ครั้ง
  - Tasks อื่นที่เข้ามาพร้อมกันจะ await ผลลัพธ์จาก Future เดียวกัน และนับเป็น `cache_hits`
- **Runtime Resolver Cache**: ผลการ resolve ทั้งสำเร็จและไม่สำเร็จจะถูกเก็บไว้ใน cache ตลอดทั้ง execution run เพื่อลด network round-trips
- **Resolver Stats Semantics**: สถิติ Resolver แยกตามหมวดหมู่อย่างถูกต้อง:
  - `attempted`: จำนวน network/custom resolver executions จริง
  - `resolved`: จำนวน resolutions ที่สำเร็จจริงและไม่ซ้ำ
  - `cache_hits`: จำนวนครั้งที่นำผลลัพธ์เดิมหรือ in-flight response มาใช้ซ้ำ
  - `failed`: จำนวนครั้งที่ resolution ล้มเหลว
- หาก resolution ล้มเหลว (timeout/offline) จะ fallback เก็บ lead ตาม URL/handle เดิมในสถานะ `needs_evidence` เสมอ ไม่ทำ lead สูญหาย

### Registry Expansion, Discovery Modes และ Prioritized Seeds

- เพิ่มโหมด `--expand-registry` และ `--mode [broad|registry-expansion|intake]` เพื่อนำ handle และชื่อครีเอเตอร์ที่มีอยู่แล้วในทะเบียนมาเป็น search seeds ค้นหาข้ามแพลตฟอร์ม
- **Prioritized Seed Selection**: จัดลำดับความสำคัญของเมล็ดค้นหาอย่างเข้มงวด:
  1. Handles ของ verified persona accounts (Priority 1)
  2. Handles ของ YouTube accounts (Priority 2)
  3. Unique account handles อื่น ๆ (Priority 3)
  4. Verified Persona display names (Priority 4)
  5. Account display names (Priority 5)
  พร้อมกรอง noise words, คำสั้น, และ suffix ทั่วไป (เช่น ` Ch.`, ` Official`, ` VTuber`) เพื่อเพิ่ม recall ข้ามแพลตฟอร์ม
- **Historical Intake Ingestion (`--include-intake`)**: รองรับการโหลด directory listings (เช่น Bācharu, Thai directories) และ YouTube owner crosslink queues จากโฟลเดอร์ `intake/` เข้าสู่ discovery pipeline พร้อม provenance ครบถ้วน
- **Deterministic Discovery Scoring**: ให้คะแนน relevance (0–10) แก่ candidate แต่ละรายการตาม signal (เช่น official crosslinks, VTuber keywords, ภาษาไทย, known handle match) เพื่อจัดเรียงลำดับใน review queue
- **Yield Tracking**: บันทึกสถิติ `raw_hits`, `new_candidates`, `known_accounts`, และ `stable_ids_resolved` แยกตาม query และ source เพื่อติดตามประสิทธิภาพของแต่ละ source
- **Platform Coverage (`python -m registry coverage`)**: รายงานสรุปจำนวนบัญชีทั้งหมด, บัญชีที่ verified, candidates ที่รอตรวจหลักฐาน (needs evidence), และ stable IDs ของแต่ละแพลตฟอร์ม
- **Missing-Platform Matrix (`python -m registry missing-matrix`)**: รายงานเมทริกซ์การมี/ขาดบัญชีบนแต่ละแพลตฟอร์มหลักของ verified personas เพื่อระบุเป้าหมายการขุดค้นหาบัญชีที่ยังขาดอยู่
- **ข้อกำหนดความปลอดภัยสำคัญ**: การพบชื่อหรือ handle เดียวกันบนแพลตฟอร์มอื่นจะสร้างเพียง candidate ใหม่ในสถานะ `needs_evidence` เท่านั้น **ห้ามเชื่อมโยงบัญชี (account link) หรือรับรอง persona โดยอัตโนมัติเด็ดขาด** การเชื่อมโยงต้องผ่านการตรวจหลักฐานของมนุษย์ (human review) เสมอ

### สถานะการหยุดและข้อผิดพลาด (Stop reasons)
ระบบรายงานสถานะของแต่ละแพลตฟอร์มอย่างชัดเจนโดยไม่หยุดการทำงานของแพลตฟอร์มอื่น:
- `completed`: ค้นหาและรวบรวมผลลัพธ์สำเร็จตามขอบเขต
- `partial`: ทำงานได้บางส่วนเนื่องจากข้อผิดพลาดในหน้าเว็บหรือการเชื่อมต่อ
- `login_required`: หน้าเว็บต้องการการเข้าสู่ระบบเพื่อดูผลค้นหา
- `captcha`: ตรวจพบระบบทดสอบความเป็นมนุษย์ (CAPTCHA / Cloudflare Turnstile / Geetest)
- `rate_limited`: แพลตฟอร์มจำกัดอัตราการเรียกค้นข้อมูล
- `selector_changed`: โครงสร้างหน้าเว็บเปลี่ยนแปลงจนไม่สามารถอ่าน selectors ได้
- `timeout`: หมดเวลารอโหลดหน้าเว็บ
- `blocked`: ถูกระงับการเข้าถึงจากเครือข่าย

### หลักการด้านความปลอดภัยและความเป็นส่วนตัว
- ไม่มีการ bypass CAPTCHA, challenge pages หรือกำแพงล็อกอิน
- ไม่มีการเก็บข้อมูล session, cookies, tokens, แชต, ผู้ชม หรือข้อมูลส่วนบุคคลที่ไม่ได้เปิดเผยต่อสาธารณะ
- ไดเรกทอรี browser profile ในเครื่องถูก exclude ใน `.gitignore` (`.playwright/`, `browser_profiles/`, `profiles/`, `playwright-data/`)

## วัดความครอบคลุม

แต่ละ run มีวิธีค้น query วันสังเกต จำนวนรายการ และเหตุผลหยุด `discovery_hits` เก็บทุกแหล่งที่พบรายเดียวกัน การนับแหล่งที่มีประสิทธิผลควรดู new verified personas เพิ่มจาก baseline หลัง review ไม่ใช้จำนวน hits เป็นจำนวนผู้สร้างใหม่

ข้อจำกัดเชิงระบบ: ผู้ที่ออฟไลน์ ผู้ไม่ใช้แท็ก ผู้ใช้ภาษาอื่น ผู้ที่ไม่มีประวัติสาธารณะ และผลค้นที่จัดอันดับยังมีโอกาสตกหล่น ไม่มีคำสั่งใดใน v0.1 อ้างว่าครอบคลุมทุกช่อง

ตรวจเอกสารอ้างอิงเมื่อ 2026-09-11 ก่อนพัฒนา collector เพิ่มให้ตรวจสิทธิ์และ endpoint ที่ใช้ได้กับบัญชีจริงอีกครั้ง

