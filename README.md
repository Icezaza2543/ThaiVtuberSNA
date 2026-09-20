# Thai VTuber Data Worker & Pipeline Engine

> **Status:** 24/7 Backend Data Collection Worker & SNA Engine powering **[ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster)**.

คลังโค้ดนี้ทำหน้าที่เป็น **Data Engine และ 24/7 Worker** สำหรับรวบรวมข้อมูล, ตรวจสอบหลักฐานตัวตน (First-Party Evidence Review), คำนวณเครือข่ายผู้ชม (SNA Overlap Engine ด้วย DuckDB), และส่งออกชุดข้อมูล CSV เพื่อให้เว็บไซต์หลัก [ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster) นำไปแสดงผล

---

## 1. สถาปัตยกรรมระบบ 4 ขั้นตอน (4-Step Pipeline)

```
ThaiVtuberSNA
        │
        ▼
[1] DISCOVER / COLLECT   (Twitch Helix API, vtuberthai.com, multi-platform accounts)
        │
        ▼
[2] REVIEW EVIDENCE      (First-party proof, idempotent queue, zero auto-link)
        │
        ▼
[3] CALCULATE SNA        (DuckDB interaction overlap, Jaccard, Simpson)
        │
        ▼
[4] EXPORT TO MASTER     (5 clean CSV exports for ThaiVtuberMaster)
        │
        ▼
ThaiVtuberMaster
```

### โครงสร้างไฟล์ใน Repository (~20 ไฟล์)

```text
ThaiVtuberSNA/
├── .github/workflows/
│   └── ci.yml                 # CI: migrate → validate → pytest
├── thaivtubersna/             # Core 4-step package
│   ├── __init__.py            # Package version (2.0.0)
│   ├── __main__.py            # CLI entry point
│   ├── store.py               # DuckDB schema, bootstrap, query helpers, parity checks
│   ├── collect.py             # Step 1: Discover & crawl accounts idempotently
│   ├── review.py              # Step 2: Evidence queue & verified change applier
│   ├── sna.py                 # Step 3: Pairwise viewer-overlap calculation
│   ├── export.py              # Step 4: Generate 5 CSV exports for ThaiVtuberMaster
│   └── worker.py              # 24/7 loop with interval scheduling and error backoff
├── data/
│   └── bootstrap.json         # Lean seed snapshot for cold starts (all 15 baseline metrics)
├── docs/
│   └── DATA_CONTRACT.md       # Full architecture & export contract specifications
├── tests/
│   ├── test_collect.py        # Tests for collection & discovery
│   ├── test_review.py         # Tests for evidence review & validation
│   ├── test_sna.py            # Tests for SNA overlap computation
│   ├── test_export.py         # Tests for Master CSV exports
│   └── test_store.py          # Tests for DuckDB store, interactions, & state
├── migrate.py                 # One-shot migration / verification tool
├── pyproject.toml             # Python packaging
├── requirements.txt           # Minimal dependencies (duckdb, requests, pytest)
├── README.md                  # System overview & CLI documentation
└── AGENTS.md                  # Developer & Agent instructions
```

---

## 2. ฐานข้อมูลและสถานะการทำงาน (Storage Architecture)

- **Runtime Database:** `runtime/thaivtubersna.duckdb` (gitignored). จัดเก็บข้อมูลทั้งหมดในเครื่องขณะทำงาน
- **Cold-Start Bootstrap:** `data/bootstrap.json` (tracked ใน git). เมื่อ Clone โปรเจกต์ใหม่ ระบบจะดึงข้อมูลตั้งต้น (13 ตารางสารบบ + 913 network_edges เดิม) เข้าสู่ DuckDB อัตโนมัติในครั้งแรกที่รัน
- **ตาราง Interactions:** บันทึกประวัติการมีปฏิสัมพันธ์ของผู้รับชม (`creator_id`, `video_id`, `viewer_hash`, `source_type`) โดยมี `UNIQUE` constraint ป้องกันข้อมูลซ้ำ 100%
- **ตาราง Network Edges:** บันทึกเส้นเชื่อมความสัมพันธ์ระหว่างครีเอเตอร์ โดยระบุ `calculation_source = 'legacy_seed'` สำหรับข้อมูลตั้งต้นเดิม และจะถูกแทนที่ด้วย `'live_interactions'` เมื่อมีการคำนวณจากข้อมูลสด

---

## 3. การใช้งานและคำสั่งหลัก (CLI Commands)

### ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### เริ่มต้นฐานข้อมูล (ถ้าต้องการรันด้วยตนเอง)
```bash
# ตรวจสอบความถูกต้องเทียบกับ Baseline
python migrate.py --dry-run

# ยืนยันข้อมูลเข้า DuckDB
python migrate.py

# ตรวจสอบ Parity ทุกตาราง
python migrate.py --verify
```

### การรัน Pipeline
```bash
# รันวงรอบการทำงานครบทั้ง 4 ขั้นตอน 1 รอบ
python -m thaivtubersna run

# รัน Worker ทำงานอัตโนมัติต่อเนื่อง 24/7 (มี Exponential Backoff และจำสถานะการทำงาน)
python -m thaivtubersna worker

# ตรวจสอบสุขภาพของฐานข้อมูลและความสอดคล้องกับ Baseline (15 รายการ)
python -m thaivtubersna validate

# ส่งออกไฟล์ CSV ทั้ง 5 ไฟล์ไปยังโฟลเดอร์ปลายทาง
python -m thaivtubersna export --output dist/export/

# ตรวจสอบสถานะคิวงาน Review
python -m thaivtubersna queue

# นำไฟล์ผลการตรวจหลักฐาน (Review JSON) เข้าสู่ระบบ
python -m thaivtubersna apply <review_file.json> --dry-run
python -m thaivtubersna apply <review_file.json>
```

### การทดสอบระบบ (Testing)
```bash
python -m pytest tests/ -v
```

---

## 4. ไฟล์ส่งมอบสำหรับ ThaiVtuberMaster

ผลลัพธ์จากการรัน `export` ประกอบด้วย 5 ไฟล์:
1. `VTUBERS.csv`: รายชื่อช่อง YouTube ที่ยืนยันตัวตนแล้วและผูกกับ Persona
2. `NETWORK_RESULT.csv`: เส้นเชื่อมเครือข่ายผู้ชมข้ามช่อง (Audience Overlap)
3. `TIKTOK_VERIFIED.csv`: บัญชี TikTok ที่ยืนยันตัวตนแล้ว
4. `TWITCH_VERIFIED.csv`: บัญชี Twitch ที่ยืนยันตัวตนแล้ว
5. `ANALYTICS_METRICS.csv`: สถิติและเมทริกซ์ของผู้สร้างแต่ละคน
