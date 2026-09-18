# ThaiVtuberSNA

**Thai VTuber Social Network Analysis · Virtual Constellation Observatory**

ThaiVtuberSNA ศึกษาโครงสร้างของวงการ VTuber ไทยจากหลักฐานผู้มีปฏิสัมพันธ์สาธารณะที่พบร่วมกันระหว่างช่อง แล้วแปลงเป็นเครือข่ายที่สำรวจตามเวลาได้

> จุดหนึ่งคือช่องครีเอเตอร์ เส้นหนึ่งคือ observed interaction overlap — ไม่ใช่ผู้ชมทั้งหมด ความสนิท อิทธิพล หรืออันดับความนิยม

![Thai VTuber audience network](docs/frontend/screenshots/main-desktop.webp)

## ใช้งาน

```bash
git clone https://github.com/Icezaza2543/ThaiVtuberSNA.git
cd ThaiVtuberSNA
python -m http.server 5500 --bind 127.0.0.1 --directory web
```

เปิด:

- Network Observatory: <http://127.0.0.1:5500/?view=network>
- Research Dashboard: <http://127.0.0.1:5500/?view=research>

Research Dashboard รวมภาพรวม ecosystem, community lineage, cohort persistence, bridge position และ coverage/sensitivity ไว้ในหน้าเดียว

![Research Dashboard](docs/frontend/screenshots/research-desktop.webp)

## อ่านผลให้ถูก

- `shared_any` = pseudonymous interactors ที่พบกับทั้งสองช่องภายใต้ source ที่รองรับ
- `strong_shared_*` ต้องพบตัวตนเดียวกันในอย่างน้อย 2 วิดีโอที่ไม่ซ้ำต่อช่อง
- community ที่คำนวณได้ไม่เท่ากับค่าย
- centrality ไม่ใช่อันดับความนิยม
- การไม่พบหลักฐานในช่วงหนึ่งไม่ใช่การยืนยันว่าไม่มี activity
- catalog coverage และ sampled interaction coverage เป็นคนละเรื่อง
- ปี 2026 ในชุดวิเคราะห์ปัจจุบันยังเป็น partial year

## เอกสาร

เอกสารโครงการหลักมีฉบับเดียว:

**[docs/PROJECT.md](docs/PROJECT.md)**

อ่านไฟล์นี้สำหรับ objective, methodology, metrics, privacy/HMAC, live collection contract, storage, frontend และโครงสร้าง repository

เอกสารที่แยกไว้เฉพาะหน้าที่:

- [Terms](docs/legal/TERMS.md)
- [Privacy](docs/legal/PRIVACY.md)
- [Rights requests](docs/legal/RIGHTS_REQUESTS.md)
- [Operator checklist](docs/legal/OPERATOR_CHECKLIST.md)
- [Security](SECURITY.md)
- `docs/evidence/` สำหรับ machine-readable QA/audit evidence

## Source map

```text
analytics/  network/temporal analysis
collector/  data collection
core/       identity, HMAC, security rules
storage/    private storage adapters
scripts/    CLI and campaign tools
web/        Network Observatory + Research Dashboard
tests/      targeted regression/synthetic fixtures
docs/       PROJECT.md, legal/, evidence/
```

Runtime campaign state, SQLite ledgers, locks, secrets และ private interaction records ไม่ควรอยู่ใน Git

## License / responsibility

Internal Research / All Rights Reserved สำหรับส่วนที่ผู้พัฒนาถือสิทธิ์ โครงการไม่เกี่ยวข้องกับหรือได้รับการรับรองจาก YouTube, Google, ค่าย หรือครีเอเตอร์ที่ปรากฏในข้อมูล
