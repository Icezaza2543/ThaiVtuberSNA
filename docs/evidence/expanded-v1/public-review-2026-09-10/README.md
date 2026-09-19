# ผลตรวจหลักฐานสาธารณะ · 10 กันยายน 2026

ตรวจโดย Codex จาก metadata และคำอธิบายของหน้า watch สาธารณะ รวมถึง portfolio ที่เจ้าของช่องลิงก์ไว้ ไม่ใช่การดูเนื้อหาภาพและเสียงทุกวินาที และยังไม่ใช่ผลอนุมัติจากเจ้าของ persona หรือผู้วิจัยมนุษย์

## ผลที่บันทึกแล้ว

| Identity | กลุ่ม |
|---|---:|
| ตรวจแล้ว | 408 |
| VERIFIED — มีคำยืนยันบริบทโดยตรงในคำอธิบาย/ส่วนแนะนำ | 38 |
| SUPPORTED — บริบทและเจ้าของแหล่งสนับสนุนเหตุการณ์ แต่ยังไม่ยืนยันประวัติครบ | 235 |
| AMBIGUOUS | 45 |
| REJECTED_AS_IDENTITY_EVENT | 90 |

เหตุการณ์ที่รองรับ: identity_start 264, redebut 5, model_change 4 รวม 273 รายการ ทุกเหตุการณ์แยก epoch ตามหลักฐาน ไม่รวม persona ต่างชื่อหรืออ้างว่าเป็นจุดเริ่มต้นแรกสุดตลอดชีวิตโดยอัตโนมัติ รายการถูกปฏิเสธหมายถึงวิดีโอนั้นไม่ใช่เหตุการณ์ที่เสนอ ไม่ได้หมายความว่าเจ้าของช่องไม่ใช่ VTuber

หลักฐาน VERIFIED เก่าสุดในชุดที่ตรวจ: Qualia, 1 กรกฎาคม 2020 เวลา 11:00:01 UTC จาก [first stream](https://www.youtube.com/watch?v=BR5l9mgxNpc) ไม่ใช่ข้อสรุปว่าเป็น VTuber ไทยคนแรก

ไฟล์ identity_batch_001 ถึง identity_batch_006 เก็บคำตัดสินรายแหล่ง วันเวลา ความละเอียด URL เหตุผลและ conflict flag ส่วนชื่อช่องเป็นชื่อที่ใช้ระบุกลุ่มปัจจุบัน ไม่ใช่หลักฐานยืนยันชื่อ/สังกัดย้อนหลัง

## บทบาทและเครดิต

ตรวจ role candidate 50 กลุ่ม: virtual_creator 13, both 10, unknown 27, production_only 0 ในกลุ่มเจ้าของช่องที่ตรวจ บทบาทที่รองรับนับซ้ำข้ามบทบาทได้: performer 23, singer 5, artist 8, rigger 9

แยกเครดิตการผลิต 12 รายการเป็น 10 public-profile entities ใน production_credits_001.json คำว่า production_only ในไฟล์เครดิตหมายถึงบทบาท endpoint ที่หลักฐานนี้รองรับเท่านั้น ยังไม่ได้ตรวจว่าผู้รับเครดิตมีบทบาท virtual performer ที่อื่นหรือไม่ ไม่สร้าง YouTube ID ให้โปรไฟล์ที่ไม่มี ID

ตัวอย่างที่ตัด false positive: Trigger ในชื่อเกมไม่ใช่ rigger และการใส่เครดิตคนวาด/คนริกไม่ได้ทำให้เจ้าของช่องเป็นผู้ผลิต ส่วน portfolio ของ Aozora Sukai ระบุทั้ง VTuber และ rigger โดยตรง

## Local Time Slider preview

[เปิด preview ในเครื่อง](http://127.0.0.1:5501/?snapshot=data/expanded-v1/public-review-408.json)

ไฟล์ข้อมูล: `scratch/expanded-v1-campaign/expanded-v1/downtime-2026-09-10/public-review-2026-09-10/reviewed_temporal_preview_408_ui.json`

ใช้ snapshot builder/exporter เดิมกับ reviewed event points และ audience aggregates ที่มีอยู่ ไม่แตะ frozen releases มี 271 ช่องที่มีเวลาเหตุการณ์แน่นอน อีก 2 รายการรู้เพียงระดับวันจึงไม่ยกระดับเป็นเวลาแน่นอน

| ปีแบบ yearly | โหนดที่มีหลักฐาน | เส้นก่อนกรองน้ำหนัก |
|---|---:|---:|
| 2020 | 4 | 1 |
| 2021 | 68 | 41 |
| 2022 | 53 | 1 |
| 2023 | 57 | 56 |
| 2024 | 89 | 16 |

All-Time: 271 โหนด / 663 เส้นก่อนกรอง ในหน้าเว็บ threshold เดิม 5 แสดง 208 เส้น โหนดที่ไม่มีเส้นเชื่อมยังอยู่ ปี 2014–2019 และ 2025–2026 ยังไม่มี reviewed event points ใน cohort นี้ จึงแสดง 0 โหนดพร้อม unknown history ไม่ใช่การยืนยันว่าไม่มี VTuber ในปีเหล่านั้น

ข้อจำกัด: audience aggregates ยังเป็นระดับช่อง ไม่ได้คำนวณใหม่แยก identity epoch; การมีเส้นไม่ได้พิสูจน์ว่าปฏิสัมพันธ์ทั้งหมดเกิดหลังเดบิวต์ หลักฐานเป็นจุดกิจกรรม ไม่ลากความต่อเนื่องถึงปัจจุบัน ไม่ใส่ subscribers/agency/status ปัจจุบันย้อนหลัง และค่า unknown history ใน preview อ้างอิง cohort 271 ช่องนี้เท่านั้น

หาก local server หยุด รัน `python scratch/serve_review_preview.py` จาก working copy นี้ ไฟล์ helper และ preview อยู่ใน scratch ของเครื่อง ไม่ใช่ public release

## จุดหยุดและงานค้าง

รอบอ่านแหล่งสาธารณะหยุดที่ candidate 408: [Zayn Gloucester](https://www.youtube.com/watch?v=kEjHLSbalxk) คืน LIVE_STREAM_OFFLINE และไม่มี actual stream start จึงไม่กำหนดวัน ข้อจำกัดนี้เฉพาะแหล่งดังกล่าว ไม่ได้ยืนยันว่าช่องที่เหลือเข้าถึงไม่ได้

ยังเหลือ primary identity 600 กลุ่ม: score >=90 จำนวน 532 และคะแนนต่ำกว่า 68; role groups 309; weak appendix 313 ยังไม่แตะ Candidate ถัดไปตามลำดับเดิมคือ 409 จึงยังไม่อ้างว่าการตรวจ strong queue เสร็จทั้งหมด

## การตรวจความสอดคล้อง

ตรวจ owner/title กับ public source metadata ครบ 408 กลุ่ม, ตรวจวัน exact เทียบ actual stream start, วันที่ unresolved เป็น null, public-data classifier ผ่าน ตรวจเบราว์เซอร์จริงที่ All-Time, cumulative 2020, yearly 2024 และ yearly 2025 ดูรายละเอียด/hash ใน review_checkpoint.json และ preview_evidence_408_ui.json

YouTube Data API requests: 0 ไม่อ่าน/เขียน workbook ไม่แตะ campaign ledger/cursor/HMAC และไม่เปลี่ยน frontend หรือ frozen artifacts ไม่รัน broad tests เพราะไม่ได้แก้ production code

Batch commits: 8fded3a, 06d4490, a1c9112, 1bebd68, e889b0b, 93fac94, d8be95a


## Channel eligibility cleaning for Surface Analytics

การตรวจ 408 กลุ่มก่อนหน้านี้เป็นการตรวจ **candidate event** เป็นหลัก จึงห้ามตีความว่า `REJECTED_AS_IDENTITY_EVENT` = “ไม่ใช่ VTuber” รอบนี้เพิ่มชั้น **channel eligibility** แยกต่างหากโดยไม่แก้ raw registry, frozen releases, workbook หรือ live campaign

| สถานะ | ช่อง | ใช้ใน Surface Analytics เริ่มต้น |
|---|---:|---|
| **STRICT_VIRTUAL** | **229** | ใช้ |
| **PROVISIONAL_VIRTUAL** | **45** | ปิดไว้โดยปริยาย / เปิดได้พร้อม caveat |
| **EXCLUDE_NON_PERSONA_ACCOUNT** | **2** | ไม่ให้นับเป็น VTuber |
| **HOLD_NEEDS_CHANNEL_REVIEW** | **132** | ยังไม่ใช้ |

สองช่องที่หลักฐานในชุด review ระบุชัดว่าเป็น account ระดับโครงการ ไม่ใช่ persona endpoint คือ **Destinesia Project** (`UCYu6pahmFwIki35ru8s62pQ`) และ **Flora Vtuber Project** (`UC8DTBPbQq0NZNo2RtCtTXuw`) จึงถูกตัดออกจาก VTuber counts แต่ยังเก็บเป็น ecosystem/source entities ได้

`STRICT_VIRTUAL` ต้องมี reviewed role ว่าเป็น virtual creator/both หรือมี VERIFIED/SUPPORTED identity event ร่วมกับหลักฐาน virtual medium/persona ที่ชัด หรือเป็น individual channel ใน reviewed virtual roster context. `PROVISIONAL_VIRTUAL` มี event ที่รองรับ แต่หลักฐานชุดปัจจุบันยังไม่ยืนยัน virtual medium แยกชัดพอสำหรับ strict surface cohort. `HOLD` หมายถึง “หลักฐานยังไม่พอ” ไม่ใช่ “ไม่ใช่ VTuber”

Artifacts: `channel_eligibility_v1.json`, `channel_eligibility_v1.csv`, `surface_virtual_cohort_v1.json`

**ค่า default สำหรับ Surface Analytics คือ 229 ช่องใน STRICT_VIRTUAL เท่านั้น** จนกว่าจะ review เพิ่ม ส่วน reference frame 1,370 ช่องและข้อมูลที่เก็บมาแล้วไม่ถูกลบ เพื่อไม่ให้เสีย provenance หรือทำให้ collection checkpoint เปลี่ยน
