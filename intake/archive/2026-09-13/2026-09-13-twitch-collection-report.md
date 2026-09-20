# Twitch collection — 2026-09-13

เพิ่มบัญชี Twitch 646 บัญชีที่ยืนยัน numeric user_id จาก Twitch ลงทะเบียนแล้ว ยืนยัน persona-account links 217 รายการ ครอบคลุม 217 persona (ใช้ persona ที่เคยตรวจแล้ว 60 และเพิ่มใหม่ 157) ยอดทั้งหมดในทะเบียนเป็น 547 persona; ไม่ใช่จำนวนบุคคลจริง

## แหล่งที่อ่านจริง

| แหล่ง | ขอบเขตที่อ่าน | ผลที่ใช้ค้นต่อ |
|---|---:|---:|
| VTuberThaiInfo archive | 1,811 รายการ | 496 รายการมี Twitch หลัก |
| vdb JSON | 10,035 รายการทั่วโลก | 45 Twitch references; ต้องตรวจความเกี่ยวข้องกับไทย |
| Thai ranking JSON | 1,352 ช่อง | 32 Twitch links ในคำอธิบาย |
| YouTube owner About | 1,387 ช่อง | 250 Twitch handles; 126 ชื่อใหม่จากคิวแรก |
| HoloList หมวดไทย | 9 หน้าหมวด / 197 โปรไฟล์ | 73 โปรไฟล์มีลิงก์ Twitch |
| Bācharu | ประเทศไทย 244 / ภาษา Thai 216 records | รวมแล้วตัดซ้ำกับแหล่งอื่น |

แหล่งเหล่านี้มีรายการซ้ำกัน จึงบวกเป็นจำนวนช่องหรือ persona ไม่ได้ ชุดแรก 558 ชื่อ เพิ่มจาก owner links/HoloList/Bācharu อีก 172 ชื่อ รวม 730 ชื่อ

## ตรวจที่ Twitch

- 730 login lookups ตอบกลับเป็นบัญชีจริง 636 รายการ
- ตรวจ numeric ID เดิมอีก 63 รหัส พบ 53 บัญชีที่เปลี่ยน login; ไม่เดาชื่อใหม่
- รวม 793 lookup attempts ตอบกลับ 689 numeric IDs ไม่ซ้ำ; 104 attempts ไม่ได้โปรไฟล์ ห้ามตีความเป็น 104 ช่องที่ลบหรือจบกิจกรรม
- คัด 43 บัญชีที่ยังไม่อยู่ในขอบเขตไทยออกจากชุดส่งทะเบียน เหลือ 646 บัญชี
- 217 บัญชีผ่าน scope/persona review อีก 429 บัญชีมีรหัสจริงแต่ยังไม่ยืนยัน persona; รวมบัญชีผู้จัดการ/กลุ่มและกรณีข้อความกำกวม
- เก็บ graduation ของ Rhea Ataraxia วันที่ 2025-05-31 จากคำประกาศตรงใน bio วันสังเกต 2026-09-13 ไม่ใช่วันกลับมา

คำว่า VTuber ในกฎแชต ชื่อผู้วาด URL แนะนำคนอื่น หรือประวัติค่ายไม่พอสำหรับยืนยัน persona การเชื่อม persona เดิมใช้ owner-controlled social link หรือ YouTube About ที่มี Twitch link โดยตรง ไม่จับคู่จากเสียงหรือชื่อคล้ายกัน ข้อมูลวัน debut/กิจกรรมที่ไม่ได้ตรวจไม่ถูกเติม

## หลักฐานและผลลัพธ์

- Candidate intake: `2026-09-13-twitch-source-queue.json`, `2026-09-13-twitch-expanded-source-queue.json`, `2026-09-13-twitch-id-recovery-queue.json`
- Public observations: `2026-09-13-twitch-public-profiles*.jsonl`, `2026-09-13-twitch-youtube-owner-evidence.jsonl`
- Review decisions: `2026-09-13-twitch-review-decisions.json`
- Reviewed change: `../reviews/archive/legacy-reviews-2026-09-16.zip`
- Exports: `../reports/current/twitch_accounts.csv`, `../reports/current/verified_twitch.csv`

ข้อมูลรอบนี้เป็น snapshot ไม่มี scheduler หรือซิงก์อัตโนมัติ Scope decisions เป็นการตรวจของ Codex ตามหลักฐานที่ระบุ ไม่ใช่การรับรองโดย Twitch หรือผู้ตรวจมนุษย์
