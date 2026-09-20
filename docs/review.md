# วิธีตรวจและแก้ทะเบียน

1. เพิ่ม candidate จาก URL ที่พบ พร้อม query และ source URL
2. ตรวจว่าเป็นบัญชีเจ้าของ persona และมี virtual presentation/Thai relation แบบใด
3. Resolve stable account ID พร้อม namespace; เก็บเป็น candidate หากยังทำไม่ได้
4. เพิ่มหลักฐาน `evidence` แล้วเพิ่ม persona, account และ account link ที่เกี่ยวข้อง
5. เพิ่มเหตุการณ์/กิจกรรมพร้อมวันที่จริง และชื่อผู้ตรวจ
6. ทดลอง `apply --dry-run` ก่อนบันทึกจริง จากนั้นรัน `validate`, unit tests และสร้างรายงานใหม่ ตรวจ diff ก่อน commit

ชุดจาก creator-link pipeline (`reviews/pending/creator-link-map-<date>.json`) เป็นรายการ `add_account` / `add_candidate` ไม่ใช่ตารางทะเบียนโดยตรง ต้องแปลงเป็น object ที่มี key เป็นชื่อตารางก่อน `apply` ไฟล์ที่ผ่าน dry-run แล้วอยู่ที่ `reviews/applied/` ดู [data-pipeline](data-pipeline.md)

## บัญชีเดียวก็ผ่าน review ได้

เกณฑ์เดียวกันใช้กับทุกแพลตฟอร์ม: ตรวจ virtual presentation, Thai relation และ
ความเป็นเจ้าของบัญชี ไม่กำหนดว่าต้องมี YouTube, X, link hub หรือบัญชีที่สอง
เช่น bio ของ Twitch/TikTok ที่เจ้าตัวแนะนำ persona เสมือนและความเกี่ยวข้องกับไทย
สามารถเป็นหลักฐานประกอบการยืนยัน persona และ ownership ของบัญชีนั้นเองได้
เมื่อผู้ตรวจตรวจเนื้อหาจริงแล้ว ไม่ใช่เพียงตรวจว่ามีลิงก์หรือรูปโปรไฟล์

`candidates.review_status=verified` หมายถึงสถานะ resolution/review ของ candidate
ตามสัญญาเดิม ไม่ใช่ตรารับรองของแพลตฟอร์มหรือการยืนยัน virtual-creator scope
โดยตัวมันเอง `inspect account ...` / `inspect candidate ...` จึงแสดง `verification`
เพิ่ม โดยแยก `account_resolved`, `virtual_creator_status`, `verified_persona_ids`
และ `reason` ออกจากแถวต้นฉบับ

```sh
python -m registry queue --kind account_scope --platform twitch
python -m registry queue --kind account_scope --platform tiktok
python -m registry queue --kind account_scope --status completed
```

`account_scope` เป็นมุมมองอ่านอย่างเดียว หนึ่งรายการต่อบัญชีที่ resolve แล้ว
ไม่ใช่จำนวนคน และไม่แก้ `review_queue`/ข้อมูลหลัก มุมมองนี้รวมบัญชีที่ไม่มี
candidate ค้างหรือ legacy issue ด้วย; คิวค่าเริ่มต้นยังนับงานเดิมเหมือนเดิม
เหตุผล `account_ownership_review` คือยังไม่มี reviewed ownership link;
`persona_scope_review` คือมี link ที่ผ่าน review แต่ persona ยังไม่ผ่าน scope;
`virtual_creator_verified` ต้องมีทั้ง persona และ ownership link ที่ผ่าน review
โดยไม่ตรวจว่ามี YouTube หรือแพลตฟอร์มอื่นหรือไม่

สถานะนี้สรุปการ review ที่บันทึกไว้ ไม่ได้ยืนยันว่าเป็นเจ้าของบัญชีหรือไลฟ์อยู่
ในปัจจุบัน รายงานตามวันและการส่งออก SNA ยังคงบังคับช่วงวันที่หลักฐานเดิม

## ค้นคิวและอ่านหลักฐาน

```sh
python -m registry queue --platform tiktok --limit 20
python -m registry queue --platform youtube --kind account_issue --query lifecycle_conflict
python -m registry queue --status completed
python -m registry inspect candidate CANDIDATE_ID
python -m registry inspect account ACCOUNT_ID
python -m registry inspect persona PERSONA_ID
```

คำสั่งเหล่านี้อ่านทะเบียนปัจจุบันและคืน JSON ไม่เรียก API หรือแก้ข้อมูล แทน ID ด้วย `record_id` จากคิว หรือ ID persona ที่บันทึกไว้ ใช้ `--data path/to/registry.json` ก่อนชื่อคำสั่งเมื่อต้องการอ่าน snapshot อื่น

`queue` รวมสองชนิดงาน: `candidate` หนึ่งรายการต่อ candidate และ `account_issue` หนึ่งรายการต่อปัญหาใน `review_queue` ค่า `total`, `totals_by_kind` และ `totals_by_reason` นับหลังใช้ตัวกรอง แต่ก่อนแบ่งหน้า ไม่ใช่จำนวน persona หรือจำนวนบัญชีที่ตัดซ้ำ

- `--status pending` เป็นค่าเริ่มต้น: candidate ที่ `needs_evidence` และปัญหาที่ `open`
- `--status completed`: candidate ที่ `verified`/`rejected` และปัญหาที่ `resolved`/`dismissed`; แต่ละแถวยังคงสถานะจริง
- `--status all`: รวมทุกสถานะ
- `--query` ค้นข้อความตรงตัวแบบไม่แยกตัวพิมพ์เล็กใหญ่ในชื่อ URL ID เหตุผล และฟิลด์สรุปอื่นของรายการ
- `--limit` รับ 1–500 ค่าเริ่มต้น 50; `--offset` เริ่มที่ 0 และผลลัพธ์ให้ `next_offset` หรือ null เมื่อไม่มีหน้าถัดไป

ลำดับคิวคือ lifecycle conflict, legacy identity collision, candidate แล้ว legacy scope review ภายในกลุ่มเรียงตามแพลตฟอร์ม ชื่อ และ ID ลำดับนี้ช่วยจัดงาน ไม่ใช่คะแนนความน่าเชื่อถือ หากทะเบียนเปลี่ยนระหว่างแบ่งหน้า ผลลัพธ์อาจเลื่อนได้

`inspect` แสดงแถวต้นฉบับ หลักฐาน ประวัติการค้นพบ และความสัมพันธ์ที่บันทึกด้วย ID รวมทั้งสถานะที่ยังไม่ผ่าน review ข้อมูล legacy แยกใน `legacy_claims` และวันที่เหตุการณ์คงความละเอียดเดิม บัญชีหรือ persona ที่ชื่อ/handle คล้ายกันไม่ถูกเชื่อมเพิ่ม รายงานของ persona รวมบัญชีที่มี link โดยตรง ส่วนรายงานของบัญชีรวม persona ที่มี link กับบัญชีนั้น ไม่ไล่ขยายไปทุกบัญชีของ persona ที่เกี่ยวข้อง

รายงานปกติและ snapshot ส่งออก `candidates.csv` พร้อม ID สถานะ review และ evidence ID สำหรับหยิบไปตรวจต่อด้วย `inspect`

## เตรียมและทดลองชุดแก้ไข

`reviews/your-reviewed-change.json` เป็น object ที่ใช้ชื่อตารางเป็น key และ list ของแถวเป็น value ตารางที่ไม่เกี่ยวข้องไม่ต้องใส่ แถวใหม่ต้องมีฟิลด์ตาม schema แถวเดิมใช้ ID เดิมและส่งเฉพาะฟิลด์ที่แก้ได้ ระบบเติมค่าปัจจุบันแล้วตรวจทั้งชุดก่อนบันทึก

ตัวอย่างโครงสร้างการแก้สถานะ candidate ที่มีอยู่แล้ว (แทนค่า ID ด้วยข้อมูลจริง):

```json
{
  "candidates": [
    {
      "id": "candidate_REPLACE_ME",
      "review_status": "rejected",
      "reviewer": "YOUR_PUBLIC_REVIEWER_ID",
      "reviewed_at": "2026-09-11T12:00:00+07:00"
    }
  ]
}
```

```sh
python -m registry apply --file reviews/your-reviewed-change.json --dry-run
python -m registry apply --file reviews/your-reviewed-change.json
```

`--dry-run` ใช้ validator เดียวกับการบันทึกจริง ตรวจชุดแก้ไขทั้งหมดร่วมกับทะเบียน แล้วแสดง `counts` ของแถว added/updated/unchanged และ `changes` ที่มีค่าก่อน/หลังรายฟิลด์ การส่ง ID เดิมหลายครั้งนับผลสุดท้ายครั้งเดียว ไม่มีการบันทึกหรือสร้าง lock แม้การตรวจล้มเหลว เมื่อไม่ผ่านจะคืน exit code 1 และข้อความเหตุผล ต้องมีไฟล์ทะเบียนอยู่แล้วเพื่อใช้โหมดนี้

การผ่าน dry-run ยืนยันเฉพาะรูปแบบและความสอดคล้องของข้อมูล ผู้ตรวจยังต้องอ่านหลักฐานจริง การใช้ `apply` โดยไม่มี `--dry-run` จะตรวจอีกครั้งกับทะเบียนขณะบันทึก

ตัวอย่างครบที่ใช้ทดสอบได้โดยไม่แตะทะเบียนหลักอยู่ใน `tests/test_registry.py` ฟังก์ชัน `reviewed_fixture` ตัวอย่างเหล่านั้นเป็นข้อมูลสมมติและไม่ใช่หลักฐานบุคคลจริง

## เงื่อนไขยืนยัน

- persona ต้องมี roles, Thai relation, evidence, reviewer และ reviewed_at
- `account_links` ต้องมีหลักฐานโดยตรงจากเจ้าตัว/ค่าย/official profile
- `continuity_links` ต้องตรวจคำประกาศที่เชื่อมสอง persona ชัดเจน การมี URL official เพียงอย่างเดียวไม่เพียงพอในขั้น review
- lifecycle ที่ verified ต้องอ้าง self_statement หรือ agency_statement
- การนำเข้า legacy ไม่ยืนยันหลักฐานใหม่ให้อัตโนมัติ
- กิจกรรมที่ยืนยันต้องมี account link ครอบคลุมวันของกิจกรรมนั้น
- วันที่รับรู้หลักฐาน (`observed_at`) และวันที่เกิดเหตุการณ์เป็นคนละฟิลด์

ตัว validator ตรวจรูปแบบและความสอดคล้องได้ แต่ไม่อ่านความหมายของหน้าเว็บแทนผู้ตรวจ ให้เขียน `evidence.summary` และ `lifecycle_events.note` ว่าประโยค/เนื้อหาใดสนับสนุนข้ออ้าง หลีกเลี่ยงข้อความเต็มหรือข้อมูลส่วนตัวที่ไม่จำเป็น

อย่าสร้างความเชื่อมโยงตัวบุคคลจริงจากเสียง วิธีพูด รูปลักษณ์ เพื่อน หรือข่าวลือ ชื่อแบบ account handle เดียวกันต่างแพลตฟอร์มเป็นเพียงเบาะแส ต้องมี official cross-link

## ประวัติการแก้ไข

Git diff/commit เก็บว่าใครแก้อะไร ข้อมูลหลักบันทึก reviewer และเวลาตรวจ ชุดแก้ไขล้มเหลวจะไม่เปลี่ยน registry และมี lock ป้องกันการเขียนซ้อน การเพิ่มข้ออ้างที่ขัดกันให้เปิด review queue; อย่าลบประวัติแกรดเพื่อให้สถานะดู active

แก้ `legacy_claims` เฉพาะเมื่อการนำเข้าผิดจากแหล่งต้นทาง ใช้ตาราง review ใหม่เพื่อเพิ่มความรู้ ไม่เขียนทับสิ่งที่รายงานเก่าเคยอ้าง
