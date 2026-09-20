# ผลรวบรวม Analytics — 2026-09-13

ส่งมอบ [Dashboard](../dist/2026-09-13-analytics-v1/dashboard.html) และ [ข้อมูล JSON](../dist/2026-09-13-analytics-v1/dashboard-data.json)

| ชุดข้อมูล | จำนวนที่ได้จริง |
|---|---:|
| บัญชีที่มีสถิติ | 3,574 |
| YouTube ตาม stable channel ID จากแหล่งรอง | 2,065 |
| TikTok ตรวจ stable ID กับแพลตฟอร์ม | 863 |
| Twitch ตรวจ stable ID กับแพลตฟอร์ม | 646 |
| ประวัติรายวัน Chuy-san | 1,318,030 จุด |
| ประวัติ Hub ที่ normalize ได้ | 41,609 จุด |
| รวมประวัติแยกต้นทาง | 1,359,639 จุด |
| บัญชีที่มีประวัติ | 2,065 |
| TikTok วิดีโอที่ embed แสดง | 8,169 |
| Twitch VOD ที่ยังเปิดให้ดู | 1,983 |
| YouTube จากรายการ ranking/live/upcoming | 117 |
| คอนเทนต์ไม่ซ้ำในชุดเก็บ | 10,269 |
| โปรไฟล์/ข้ออ้างจากไดเรกทอรี | 2,042 รายการแยกต้นทาง |

ประวัติเริ่ม 2020-08-16 ถึง 2026-09-13 แต่วันเริ่ม/จบแต่ละบัญชีไม่เท่ากัน
รวม observations จากหลาย provider ไม่ใช่จำนวน account-days ที่ไม่ซ้ำ

## ความครอบคลุมและหลักฐาน

- ทะเบียนหลักยังมี 2,879 บัญชีและ 547 persona ที่ผ่าน review ไม่เปลี่ยนเป็นจำนวน 3,574 persona
- Analytics catalog มี 3,601 บัญชี รวม 27 บัญชีเดิมที่ยังไม่มี counters รอบนี้
- 722 บัญชีที่มีตัวเลขยังเป็น directory_only; เก็บ source statistics ได้โดยไม่รับรองการเป็น VTuber
- Chuy-san สำเร็จ 1,352/1,352 history endpoints
- Hub ดึง directory 1,401 records; 7 records ไม่มี channel ID ที่ใช้ normalize ได้
- Hub history เคยติด HTTP 429 จำนวน 565 requests เก็บซ้ำช้า ๆ สำเร็จครบ 565
- HoloList 197 โปรไฟล์ และ USADA 180 โปรไฟล์ไทย; USADA เคยติด 429 จำนวน 108 เก็บซ้ำสำเร็จครบ
- Bācharu กรองประเทศไทย/ภาษาไทยรวมไม่ซ้ำ 264 profiles; เก็บเป็น source claims ไม่จับคู่บุคคลเบื้องหลัง
- ตรวจแหล่งที่ผู้ใช้ให้มา 38 URLs/endpoint references: อ่านได้ 29; 9 อ่านไม่ได้ในรอบนี้
- 9 แหล่งที่อ่านไม่ได้: vdb editor, Holodex API, Fandom, Playboard Thai, TierMaker Thai, VSTATS, Taiwan site, Danbooru, NamuWiki
- หน้าเว็บ/โค้ด GitHub ที่อ่านได้ไม่ถือว่านำเข้าฐานทั้งหมดแล้ว ดู source-audit และหน้าแหล่งข้อมูลใน Dashboard

## สิ่งที่ใช้วิเคราะห์ได้

ค้นบัญชี อันดับแยกแพลตฟอร์ม ผู้ติดตาม/ยอดวิวสะสมย้อนหลัง growth 7/30/90 วัน
พร้อมวันที่ฐานจริง ตารางคอนเทนต์ และค้นข้อมูลค่าย/แนวเนื้อหาตามที่ไดเรกทอรีรายงาน
ตัวเลขล่าสุดทุกบัญชีมีเวลาที่อ้างอิง: timestamp ของต้นทางหรือเวลาอ่านแพลตฟอร์ม
Hub ที่ไม่มีเวลาตัวเลขใน directory ใช้ค่าจากจุดประวัติที่มี capturedAt แทน โดยเก็บค่าต้นฉบับแยกไว้

## สิ่งที่ยังสรุปไม่ได้

จำนวนวีไทยทั้งวงการ, จำนวนผู้ชมไม่ซ้ำข้ามแพลตฟอร์ม, รายได้รวม, engagement ทั้งช่อง,
ชั่วโมงไลฟ์ครบทุกครั้ง, สถานะ active/แกรดจากการหายไป, และประวัติ persona ย้อนหลังตามอายุบัญชี
TikTok ไม่มีวันเผยแพร่/likes/comments หลายฟิลด์; ไม่เติม 0 หรืออนุมานจาก video ID
ข้อมูลค่าย/เดบิวต์/สถานะยังเป็น secondary claims ไม่เปลี่ยนทะเบียนที่ต้องใช้หลักฐานเจ้าตัว/ค่าย

## ตรวจสอบ

- Unit tests 49 ข้อผ่าน รวม baseline หาย, ฐานเป็นศูนย์, growth ติดลบ, วันที่, source hash และ CSV formula escaping
- registry validate ผ่าน; registry report ณ 2026-09-13 ผ่าน
- ตรวจ manifest ทุกไฟล์, stable IDs เป็น string, unique account/content keys และนับ history CSV เต็มตรง summary
- ตรวจ growth 4,667 ค่ากับวันฐานและวันท้ายใน history CSV เต็ม ทุกค่าตรงกัน
- ทดสอบ Dashboard ในเบราว์เซอร์: ค้นหา/สลับแพลตฟอร์ม, growth table/กราฟ, คอนเทนต์ Twitch และ USADA หลายภาษา ไม่มี JavaScript errors ในการทดสอบ
- [Review ที่ pin hash](../reviews/archive/legacy-reviews-2026-09-16.zip) · [นิยามและคำสั่ง](../docs/analytics.md)

ข้อมูลและโปรแกรมยังคง Internal Research / All Rights Reserved ไม่มี scheduler หรือ live sync

## Google Sheets

เพิ่มแท็บใหม่ใน [ThaiVtuber_SNA](https://docs.google.com/spreadsheets/d/1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE/edit#gid=26091305):

- ANALYTICS_METRICS: 3,574 แถวข้อมูล
- ANALYTICS_GROWTH: 2,065 แถวข้อมูล
- ANALYTICS_SOURCES: 38 แหล่ง/endpoint references
- ANALYTICS_NOTES: 22 รายการนิยามและขอบเขต

อ่านกลับตรงทุกค่าและชนิดข้อมูล 81,900 เซลล์รวม headers; รักษาแท็บเดิม 15 แท็บ
ตรวจรูปแบบผ่าน CellData/metadata เนื่องจากเบราว์เซอร์ Google ยังต้องลงชื่อเข้าใช้
ไม่ได้ส่งประวัติ 1.36 ล้านจุดทั้งหมดลงชีต ดูไฟล์ history.csv.gz ใน snapshot
[บันทึกการส่งและตรวจ](google-sheets-analytics-publish-2026-09-13.json)
