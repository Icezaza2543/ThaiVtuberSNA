# ที่มาของข้อมูลตั้งต้น

- Repository: [Icezaza2543/ThaiVtuberSNA](https://github.com/Icezaza2543/ThaiVtuberSNA)
- Git commit: `47d98e1d9fdc9020fd0e4eb4ff025bbfc12902cf`
- Source file: `data/thai_vtuber_registry.csv`
- SHA256: `9c9b4fb90350bfa5313235906769eae72ba2bfda5b7c26abb6afe2fabbb57b02`
- วันที่นำเข้า: 2026-09-11
- จำนวนบัญชี YouTube ไม่ซ้ำ: 1,370

นำเข้าช่อง ชื่อ handle ป้ายกำกับสถานะเดิม สังกัดเดิม ชื่อแหล่งอ้างอิง วันตรวจเดิม และวันวิดีโอล่าสุด โดยใช้รายการฟิลด์ที่กำหนด ไม่มีข้อมูลผู้ชม คอมเมนต์ แชต token หรือไฟล์ .env ในชุดนำเข้า

ทุกแถวเดิมมี source status `CONFIRMED` แต่สถานะนี้เป็นคำกล่าวในแหล่งเดิม การยืนยันแบบข้ามแพลตฟอร์มของ repo ใหม่นับจาก `personas.review_status` และ evidence ที่ผ่าน review เท่านั้น

ไม่ได้แปลง `person_id` เดิมเป็น persona เนื่องจาก mapping เดิมเป็นสมมติฐานระดับช่องและมี ID ซ้ำ 2 กลุ่ม ครอบคลุม 4 บัญชี บัญชีเหล่านี้ได้คิว `legacy_identity_collision` แยกไว้โดยไม่เผยแพร่การเชื่อม persona ที่ยังไม่ตรวจ

ค่าประวัติใน `data/industry/creator_status_events.csv` ของ repo เดิมยังไม่ถูกนำมาเป็น verified events ใน v0.1 เพราะมีทั้งประกาศที่มีหลักฐานและ inferred proxies ให้คัดเฉพาะเหตุการณ์ที่ตรวจ source และ subject แล้วในรอบต่อไป

## สร้าง baseline ซ้ำในไฟล์ใหม่

เมื่อมี checkout ของ ThaiVtuberSNA ที่ commit ข้างต้นและไฟล์ต้นทางมี checksum ตรงกัน:

```sh
python -m registry --data scratch/reimport/registry.json import-legacy --csv ../ThaiVtuberSNA/data/thai_vtuber_registry.csv --source-commit 47d98e1d9fdc9020fd0e4eb4ff025bbfc12902cf
python -m registry --data scratch/reimport/registry.json validate
```

เนื้อหาบัญชีและป้ายกำกับจะเหมือนเดิม แต่เวลานำเข้า (`observed_at`, `first_discovered_at`) เป็นเวลาของการรันใหม่ หากต้องการผล byte-for-byte ให้ใช้ snapshot และ manifest เดิม
