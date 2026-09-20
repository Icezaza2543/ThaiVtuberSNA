# Analytics จากข้อมูลสาธารณะ

`data/registry.json` ยังเป็นแหล่งจริงสำหรับบัญชี persona และข้ออ้างที่ผ่าน review
ส่วน analytics เป็นชุดสังเกตการณ์ตัวเลขตามต้นทางใน `intake/2026-09-13-analytics-v1/`
ไม่เพิ่ม persona ไม่เปลี่ยนสถานะกิจกรรม และไม่ถือว่ารายการในไดเรกทอรีเป็น VTuber ที่ผ่านการตรวจแล้ว

## แหล่งและวิธีเก็บที่รันจริง

| แหล่ง | ข้อมูล | ข้อจำกัด |
|---|---|---|
| TikTok public creator embed | followers, likes received, รายการวิดีโอและยอดดู | ตรวจ numeric ID ให้ตรงทะเบียน; วิดีโอที่ embed เลือกแสดง ไม่ใช่ uploads ทั้งหมด; วันเผยแพร่/likes/comments ส่วนใหญ่ไม่มี |
| Twitch public website GraphQL | followers, available archive VODs, ระยะเวลา, ยอดดู VOD, live snapshot | ค้นด้วย numeric broadcaster ID; สูงสุด 100 VOD ต่อช่อง พร้อม flag ถ้ามีต่อ; ไม่เก็บรายชื่อผู้ชม/แชต; ไม่มีประวัติผู้ติดตามรายวันย้อนหลัง |
| Chuy-san v2 | channel counters, daily chart_data, ranking/live/upcoming video lists | สถิติจากแหล่งรอง; วันที่ `updated_at` แยกจากวันดาวน์โหลด; รายการ ranking อาจเก่าและไม่ใช่คอนเทนต์ครบทั้งช่อง |
| Hub VTuber Thai | รายการบัญชี, counters, daily subscriber-tracker, agency/tags | เก็บประวัติแยก Chuy; API มี rate limit; counters บน directory ไม่มีเวลาเฉพาะฟิลด์ จึงใช้จุดประวัติที่มี `capturedAt` แทนในหน้าล่าสุดเมื่อมี |
| Bācharu | ฟิลด์โปรไฟล์ไทย, ค่าย/สถานะที่ต้นทางอ้าง, snapshot กิจกรรม | ไม่เชื่อม handle จากแหล่งรองเป็น stable account ID อัตโนมัติ; ไม่เก็บ voiceActor, บุคคลเบื้องหลัง, donation goals หรือข้อมูลติดต่อ |
| HoloList / USADA | หมวดไทย, ค่าย, เดบิวต์, ภาษา, เนื้อหา, model ตามที่แต่ละหน้าให้ | เก็บเป็น secondary source claims; หลายแหล่งคัดลอกจากกัน จึงไม่ใช่การยืนยันอิสระหลายครั้ง |
| แหล่งอื่นที่ผู้ใช้ส่ง | ตรวจการเข้าถึงและบทบาทของหน้า/โครงการ | ดู `source-audit.jsonl`: เข้าถึงได้ไม่เท่ากับนำเข้าฐานทั้งหมด; ไม่ข้าม login, rate limits หรือข้อจำกัดการเข้าถึง |

การอ่าน public website application ID ของ Twitch ทำในหน่วยความจำ ไม่เก็บ request/session tokens
และไม่ใช่การใช้ OAuth หรือ Twitch Helix ที่มีสิทธิ์บัญชีผู้ใช้

## สัญญาข้อมูล

- Source envelope มี `source_url`, `observed_at`, HTTP Last-Modified ถ้ามี และ SHA256 ของเฉพาะข้อมูลที่เก็บไว้
- ตัวเลขที่ไม่มีเป็น null ไม่ใช่ 0; ไม่ใช้ boolean/string แทนจำนวน; platform IDs เป็น string
- บัญชีตัดซ้ำตามแพลตฟอร์มและ stable ID ไม่รวมจากชื่อคล้ายหรือ handle ตรงกัน
- `directory_only` หมายถึงมี ID/ตัวเลขตามแหล่งรอง ยังไม่ใช่บัญชี/persona ที่ตรวจยืนยันในทะเบียน
- `reviewed_persona_link` หมายถึงเคยมีลิงก์ที่ผ่าน review; ช่วงวันที่จริงต้องอ่านจากทะเบียน ไม่ลากย้อนหลังตามอายุช่อง
- ชุดประวัติแยก `(account, source, date)` และตัดจุดซ้ำที่เหมือนกันในวันเดียวกัน ไม่ต่อเส้นข้าม provider
- Growth 7/30/90 วันใช้วันสุดท้ายที่ต้นทางมี กับวันที่ก่อนหรือเท่ากับเป้าหมายไม่เกิน 3 วัน ระบุวันต้น/ท้ายและจำนวนวันจริง
- ถ้าขาด baseline ให้ null; ฐานเป็น 0 ไม่คำนวณ growth percent; ยอดลดคงค่าติดลบเพราะอาจเกิดจากการลบ/แก้ตัวเลข
- ยอดวิวสะสมที่เปลี่ยนไปไม่ใช่ gross views ที่เกิดขึ้นทั้งหมดในช่วงนั้น
- กราฟย่อแสดง 90 จุดท้ายและจุดท้ายเดือนก่อนหน้า ไฟล์ `history.csv.gz` เก็บทุกจุดที่ normalize ได้
- รวมจุดประวัติข้ามต้นทางเป็นจำนวน observations ไม่ใช่จำนวน account-days ที่ไม่ซ้ำ
- ไม่มีค่า engagement rate เมื่อไม่มี likes/comments ที่เชื่อถือได้ และไม่ใช้ยอดดู VOD เป็น concurrent viewers
- Affiliations/debut/graduation จากไดเรกทอรีไม่เปลี่ยนตาราง affiliations/lifecycle_events ในทะเบียน

## รันใหม่

คำสั่งเก็บข้อมูลเรียกเครือข่ายจริง ต้องรันเมื่อผู้ใช้ขอเก็บข้อมูล เลือกชื่อโฟลเดอร์ใหม่ทุกครั้ง:

```sh
python -m registry.analytics_collect --task tiktok --output intake/analytics-next-run --workers 4
python -m registry.analytics_collect --task twitch --output intake/analytics-next-run
python -m registry.analytics_collect --task chuy --output intake/analytics-next-run --workers 4
python -m registry.analytics_collect --task hub --output intake/analytics-next-run --workers 1
python -m registry.analytics_collect --task bacharu --output intake/analytics-next-run
python scripts/collect/collect_analytics_directories.py --output intake/analytics-next-run
```

ตรวจจำนวน errors ก่อนใช้ โดยเฉพาะ HTTP 429 ไม่ได้หมายถึงไม่มีบัญชีหรือไม่มีประวัติ
รอบนี้ใช้ `retry_hub_history.py` และ `retry_usada_profiles.py` อ่านเฉพาะส่วนที่ติดข้อจำกัด
แบบหนึ่งครั้งต่อวินาทีและหยุดหากถูกจำกัดอีก ไม่ได้ตั้งระบบเก็บตามตารางเวลา

สร้าง reviewed analytics change file ตามไฟล์จริง `reviews/archive/legacy-reviews-2026-09-16.zip`
ต้อง pin hash ของ registry และ source files หลังเก็บเสร็จ แล้วใช้ builder ที่ไม่เรียกเครือข่าย:

```sh
python -m registry.analytics --input intake/2026-09-13-analytics-v1 --review reviews/archive/legacy-reviews-2026-09-16.zip --output dist/2026-09-13-analytics-v2
python -m unittest discover -s tests -v
python -m registry validate
python -m registry report --as-of 2026-09-13
```

Builder ปฏิเสธไฟล์ที่ hash เปลี่ยน การ review ก่อนเวลาเก็บ และโฟลเดอร์ output ที่มีอยู่แล้ว
ตรวจ manifest SHA256 ก่อนส่งต่อ snapshot; เปิด `dashboard.html` ได้โดยตรง หรือใช้ HTTP server ภายในเครื่อง
Snapshot ไม่มี external JS, ไม่มี telemetry และไม่อัปเดตตัวเอง

Google Sheets ใช้แท็บใหม่สำหรับ latest metrics / growth / source coverage พร้อม ID แบบข้อความ
ไฟล์ประวัติเต็มเก็บนอกชีตเพื่อหลีกเลี่ยงการใช้เซลล์หลายล้านช่อง ตัวเลขในชีตเป็น snapshot ไม่ใช่ live sync

สิทธิ์ยังเป็น Internal Research / All Rights Reserved
