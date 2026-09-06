# รายงานการเก็บข้อมูลรายวิดีโอและแยกแยะแหล่งข้อมูล (ระยะที่ 3)

**วันที่และเวลาเก็บข้อมูล:** 2026-09-06 15:09:23 UTC  
**สถานะการผ่านเกณฑ์ระยะที่ 3 (Phase 3 Gate Criteria):** **PASSED**  
**สถานะการตรวจสอบความเป็นส่วนตัว (Cryptographic Privacy Audit):** **PASSED (ZERO PII LEAKS)**  
**ลายนิ้วมือกุญแจลับ (Key Fingerprint):** `142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`

---

## 1. สรุปผลการเก็บข้อมูล (Collection Summary)

| ตัวชี้วัด | ค่าที่บันทึกได้ | คำอธิบาย |
|---|---|---|
| **จำนวนแถว Presence ทั้งหมด (Total Rows)** | **750** | ข้อมูลการปรากฏตัวที่บันทึกลงใน Parquet |
| **จำนวนคู่ Presence ไม่ซ้ำ (Unique Keys)** | **750** | คีย์ `(viewer_hash, channel_id, video_id, source_type)` |
| **จำนวนผู้ชมไม่ซ้ำ (Unique Viewers)** | **710** | คำนวณผ่าน HMAC-SHA256 โดยไม่มีข้อมูลตัวตนเดิม |
| **จำนวนไฟล์ Parquet ที่จัดเก็บ** | 9 ไฟล์ | จัดเก็บแบบพาร์ติชันแยกวันและ Atomic Commit |

---

## 2. การแยกแยะแหล่งข้อมูลอย่างเคร่งครัด (Strict Source Separation)

ตามข้อกำหนด Public Comments ไม่สามารถใช้ทดแทน Live Chat ได้ ระบบจึงแยกงานและบันทึกแยกแหล่งข้อมูลอย่างชัดเจน:

| ประเภทแหล่งข้อมูล (`source_type`) | จำนวนแถวที่เก็บได้ | สัดส่วน | หมายเหตุ |
|---|---|---|---|
| **Public Comments (`comment`)** | 750 | 100.0% | คอมเมนต์ใต้คลิป/VOD ดึงผ่าน YouTube Data API |
| **Live Chat Messages (`live_chat`)** | 0 | 0.0% | ข้อความแชทสดระหว่างถ่ายทอดสด / Live Replay |

---

## 3. ความเป็นธรรมในการจัดสรรคิว (Fair API Budgeting & Coverage)

ระบบจัดสรรคิวโดยกระจายไปยังวิดีโอจากหลากหลายสังกัดและกลุ่มอย่างสมดุล ไม่กระจุกตัวเฉพาะช่อง Seed ใหญ่:

| ลำดับ | ช่อง VTuber | สังกัด | Video ID | ประเภทคลิป |
|---|---|---|---|---|
| 1 | `UC3it6w4G8eUA98J2w60gBDQ` | Independent | `MFwLyIn5eRY`: ◄Live!!!!► [Free Talk] 4 คน 4ค... | replay_vod |
| 2 | `UC3QTic1iBGQN_LzWo7JfDKQ` | Independent | `p1hrKwJksGk`: Switchblade - aespa「Cover by C... | normal_video |
| 3 | `UC3OnR-Tqd8dHmY-XNHO4iZw` | Independent | `OKNQ_SPs-fs`: เรื่องที่ทำให้โมโห... | replay_vod |
| 4 | `UC2mSWpVqjjQ7G7gEIfQ7p9w` | Independent | `LkhrTJsn8so`: 【CHAT】แชทโดเนทให้กินผัก... | normal_video |
| 5 | `UC2sAw3h-IzU3JOtvXVzTjxw` | Independent | `raWTffMYJ5Q`: 【COVER】NuNew feat. Tan Lipta -... | normal_video |
| 6 | `UC3gREX7tB8vEhPFgAOGr9xg` | Independent | `jCIEmbCB9vk`: ไดโนเสาร์ยังไม่นอน... | replay_vod |

---

## 4. รายการที่เข้าถึงไม่ได้ตามจริง (Inaccessible / Disabled Features Log)

บันทึกสถานะข้อจำกัดของแต่ละคลิปอย่างโปร่งใสตามความเป็นจริง (เช่น ปิดคอมเมนต์ หรือ Live Replay ไม่ถูกเก็บถาวร):

| Job ID | สาเหตุที่เข้าถึงไม่ได้ | รายละเอียดข้อผิดพลาด |
|---|---|---|
| - | ไม่มีรายการที่ผิดพลาดหรือถูกปิดกั้นในรอบนี้ | - |

---

## 5. การตรวจสอบความปลอดภัยและความเป็นส่วนตัว (Privacy Audit Trail)

- **การทดสอบ Zero-PII Leak:** ตรวจสอบไฟล์ `.parquet` ทั้งหมดในไดเรกทอรีจัดเก็บ
- **ผลการสแกน:** ไม่พบบัญชีผู้ใช้, ไม่พบชื่อที่แสดง (Display Name), ไม่พบรูปโปรไฟล์, ไม่พบข้อความคอมเมนต์/แชทดิบ, และไม่พบค่า Sentiment
- **การคงสภาพกุญแจ (Key Continuity):** ยืนยันตรงกับ `data/real/identity_manifest.json`

---

## 6. ไฟล์ผลลัพธ์ที่สร้างในระยะที่ 3 (Generated Artifacts)

- **ไดเรกทอรีข้อมูลเหตุการณ์ (Parquet):** [`data/real/events/`](file:///C:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/real/events)
- **สมุดบันทึกสถานะงาน (Durable Journal):** [`data/real/jobs.sqlite3`](file:///C:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/real/jobs.sqlite3)
- **รายงานสรุปการเก็บข้อมูล:** [`data/phase3_collection_report.md`](file:///C:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/phase3_collection_report.md)

---
*รายงานนี้จัดทำขึ้นโดยอัตโนมัติเพื่อเป็นหลักฐานตรวจสอบย้อนหลังสำหรับระยะที่ 3*
