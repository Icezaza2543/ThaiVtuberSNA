# โครงสร้างข้อมูล

ข้อมูลหลักเป็น JSON หนึ่งไฟล์: `schema_version` และ `tables` ทั้ง 13 ตารางใน `schemas/registry.sql` CLI โหลดเข้า SQLite ใน RAM เพื่อบังคับ foreign keys, unique IDs, enums และตรวจหลักฐานเพิ่มเติมก่อนบันทึกไฟล์แบบ atomic

| ตาราง | หน่วยและการเชื่อมโยง |
|---|---|
| `evidence` | URL, ชนิดหลักฐาน, วันเผยแพร่, วันตรวจ, SHA256 ถ้ามี |
| `personas` | ตัวตนครีเอเตอร์ที่เปิดเผยต่อสาธารณะ; ไม่มี real person ID |
| `accounts` | บัญชีแพลตฟอร์มที่มี stable ID; ไม่ได้เท่ากับ persona หนึ่งตัวเสมอ |
| `account_links` | Persona ใช้บัญชีใดในช่วงวันที่ที่มีหลักฐาน รองรับบัญชีกลุ่ม |
| `lifecycle_events` | เหตุการณ์ของ persona พร้อมวันที่และความละเอียดของวันที่ |
| `activity_observations` | หลักฐาน live/post/video ของ persona บนบัญชีที่ยืนยัน |
| `affiliations` | สังกัดสาธารณะพร้อมช่วงวันที่และหลักฐาน |
| `continuity_links` | ความต่อเนื่อง persona ที่เจ้าตัว/ค่ายเปิดเผย |
| `discovery_runs` | แพลตฟอร์ม วิธีค้น query วันตรวจ จำนวนหน้า/รายการ และเหตุผลหยุด |
| `candidates` | รายชื่อรอตรวจ รองรับ stable ID ที่ยังไม่ทราบ |
| `discovery_hits` | พบ candidate/account จาก run ใด หลายแหล่งชี้รายเดียวกันได้ |
| `legacy_claims` | ป้ายกำกับจากทะเบียนเดิมแยกจากข้ออ้างที่ review ใหม่ |
| `review_queue` | ปัญหาที่ต้องตรวจในบัญชีตั้งต้น |

`accounts` ตัดซ้ำด้วย `(platform, id_namespace, platform_id)` Twitch ใช้ `user_id`; YouTube ใช้ `channel_id` TikTok/Facebook ต้องระบุ namespace ที่ API หรือแหล่งต้นทางให้จริง เช่น ID ที่มีขอบเขตต่อแอปไม่ควรถูกรวมกับ global ID ชื่อและ handle เปลี่ยนได้จึงไม่ใช่หลักฐานว่าบัญชีเป็นบัญชีเดียวกัน

รอบ Twitch 2026-09-13 ใช้ numeric `user.id` จากข้อมูลโปรไฟล์สาธารณะของ Twitch เก็บเป็น string ใน namespace `user_id` การค้นด้วยรหัสที่แหล่งรองเคยบันทึกต้องได้รหัสเดิมจาก Twitch จึงยืนยัน login ปัจจุบันได้; ไม่รับรองเจ้าของ handle ในอดีตและไม่สร้าง continuity ระหว่าง persona จากการเปลี่ยนชื่อ

รอบ TikTok วันที่ 2026-09-13 ใช้ namespace `web_user_id` สำหรับค่าตัวเลข `userInfo.id` จาก public creator embed ของ TikTok ตรวจว่า `uniqueId` ตรงกับ handle ที่ร้องขอและโปรไฟล์เป็นสาธารณะ รหัสเก็บเป็น string ไม่รวมกับ `open_id`, `union_id` หรือ Research API ID โดยสมมติว่าใช้ namespace เดียวกัน หลักฐานนี้ยืนยันบัญชีที่ตอบกลับในวันตรวจ ส่วนการเป็น persona เสมือนและความเกี่ยวข้องกับไทยมี review แยก

`roles` เป็น JSON array ที่ serialize เป็น string ตาม SQL เช่น `"[\"streamer\",\"singer\"]"` ค่า format และ roles แยกกัน นักวาด/rigger ไม่ผ่านเป็น VTuber เพียงเพราะมีเครดิตผลิตโมเดล

วันที่กิจกรรมและช่วงเชื่อมบัญชีเป็น `YYYY-MM-DD` ส่วน timestamps ต้องมี timezone ช่วง `valid_from` / `valid_to` นับรวมวันต้นและวันท้าย วันที่ที่ไม่รู้ใช้ null; ห้ามเติมวันย้อนหลังจากวันที่สร้างช่อง

รายงานแพลตฟอร์ม ณ วันอ้างอิงและการส่งออก SNA ใช้ account link ที่มีวันที่ทั้งสองด้านและครอบคลุมวันนั้น การระบุ null หมายถึงยังไม่รู้ ไม่ได้ให้สิทธิ์ลากสถานะไปทุกปี ผู้ตรวจอาจบันทึกช่วงหนึ่งวันเมื่อยืนยันได้เพียงวันเดียว

รายงาน lifecycle อ่านหลักฐานย้อนหลังตามวันเกิดเหตุการณ์โดยใช้ความรู้ทั้งหมดที่มีในไฟล์ปัจจุบัน หากต้องการย้อนดูว่า ณ วันหนึ่งผู้วิจัยรู้อะไรบ้าง ให้ใช้ snapshot ที่สร้างในวันนั้น ทุก report ระบุ `as_of` และความหมายของขอบเขต จำนวน inventory แสดงสิ่งที่เคยนำเข้าทั้งหมดและไม่ได้เป็น census ในอดีต

บุคคลเบื้องหลัง persona ไม่อยู่ในโมเดลนี้ ความต่อเนื่องสาธารณะเป็น relationship ไม่ได้ลดสอง persona ให้เหลือหนึ่งโดยอัตโนมัติ

## ชั้น analytics

สถิติและประวัติจากแพลตฟอร์ม/ไดเรกทอรีเก็บใน source batches แยกจาก 13 ตารางของทะเบียน
เพราะการพบตัวเลขของบัญชีไม่ได้ยืนยัน persona หรือความเกี่ยวข้องกับไทย ชุด analytics มี hash review
และส่งออกเป็น snapshot ใหม่ด้วย `python -m registry.analytics` ดู [สัญญาข้อมูล analytics](analytics.md)
การเพิ่มข้อมูลชั้นนี้จึงไม่เปลี่ยนจำนวน verified personas หรือ lifecycle ใน `registry report` โดยอัตโนมัติ

## Account resolution ไม่ใช่ virtual-creator verification

ไม่มีคอลัมน์ verified ของ `accounts` ที่แปลว่าผ่าน scope โดยลำพัง
สถานะ `virtual_creator_status` ใน dossier/คิว `account_scope` เป็นค่าคำนวณจาก
persona ที่ผ่าน review และ `account_links` ที่ผ่าน review เท่านั้น
ไม่มีเงื่อนไขชื่อแพลตฟอร์ม จำนวนแพลตฟอร์ม หรือการมี YouTube
ข้อมูล derived เหล่านี้ไม่เพิ่มตารางและไม่เปลี่ยน schema ของ snapshot เดิม

หนึ่ง persona อาจมีบัญชีเดียว หนึ่งบัญชีอาจมีหลาย persona โดยเก็บความสัมพันธ์
ทุกตัวไว้ ไม่เลือก owner เพียงคนเดียวจากการเรียงแถว การไม่มี reviewed link
หรือยังไม่ทราบ stable ID ไม่ใช่หลักฐานว่าเจ้าของไม่เป็น virtual creator
