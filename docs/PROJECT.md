# Thai VTuber Social Network Analysis (SNA)

โครงการวิจัยและสำรวจโครงสร้างเครือข่ายความสัมพันธ์ของผู้ผลิตคอนเทนต์ VTuber ในประเทศไทย โดยใช้หลักฐานการมีปฏิสัมพันธ์ร่วมกันบนแพลตฟอร์มสาธารณะ (YouTube)

---

## 1. ขอบเขตและสถาปัตยกรรมของโครงการ (Architecture)

โครงการถูกออกแบบเป็น **Static Web Application** ที่ประมวลผลข้อมูลจากชุดหลักฐานคงที่ (Sealed Datasets) เผยแพร่ผ่านหน้าเว็บสาธารณะ โดยไม่มีการเก็บข้อมูลส่วนบุคคลของผู้ชม

```
ThaiVtuberSNA/
├── web/                           # ส่วนแสดงผลเว็บสาธารณะ (Single-page app)
│   ├── index.html                 # หน้าเว็บหลัก (รองรับ Network Graph, Surface, Research v2)
│   ├── network-ui.js              # ตัวควบคุมและการแสดงผลกราฟความสัมพันธ์
│   ├── research.js                # ตัวแสดงผล Dashboard: Surface Analytics + Research v2
│   ├── data.json                  # ข้อมูลโครงสร้างเครือข่ายสำหรับ Graph UI
│   └── research/
│       ├── dashboard_data.json    # ตัวชี้วัดรายปีของระบบเครือข่าย
│       ├── surface_analytics_v1.json # ข้อมูล Strict 229+ Virtual Cohort
│       └── data/research_v2.json  # ข้อมูล Longitudinal Cohort Pulse & Outlook
├── data/
│   └── registry/                  # ทะเบียนครีเอเตอร์และสถานะตัวตนหลัก (Canonical Registry)
│       ├── creators.json          # ทะเบียนทางการ (1,370 baseline + 392 accepted discovery)
│       └── identity_resolutions.json # ประวัติการจับคู่บัญชีกับตัวตน
├── scripts/                       # เครื่องมือสำหรับประมวลผลข้อมูลและตรวจสอบความปลอดภัย
│   ├── build_creator_registry.py  # สร้าง canonical creators.json แบบ deterministic
│   ├── build_surface_analytics.py # สรุปตัวชี้วัด Surface Analytics
│   ├── build_web_data.py          # ประกอบไฟล์ข้อมูลสำหรับเว็บ
│   ├── privacy_audit.py           # ตรวจสอบการไม่รั่วไหลของข้อมูลส่วนบุคคล (PII)
│   └── audit_data_security.py     # ตรวจสอบความปลอดภัยของ Git Object
└── tests/                         # ชุดทดสอบความถูกต้องและข้อกำหนดของระบบ
```

---

## 2. ข้อมูลและการจัดกลุ่ม (Data & Cohorts)

### Canonical Creator Registry
- **Baseline YouTube Channels**: 1,370 ช่อง
- **Accepted Discovery Accounts**: 392 บัญชี (ผ่านการคัดกรองและตรวจสอบตัวตน)
- **Total Registered Creators**: 1,645 คน (รวม 1,755 บัญชี)
- **Deduplicated / Excluded**: 292 บัญชีซ้ำกับ baseline, 106 บัญชีถูกตัดออก (ไม่ใช่ VTuber / กลุ่ม Virtual), 94 บัญชีไม่สามารถเข้าถึงได้

### Surface Analytics Cohort
- นับเฉพาะช่องที่ผ่านเกณฑ์ `STRICT_VIRTUAL` จากหลักฐานที่ตรวจสอบแล้ว
- ใช้เป็น denominator หลักของหน้าเว็บเพื่อความแม่นยำสูง

### Research v2 Longitudinal Cohort
- ใช้ cohort คงที่ในการติดตามแนวโน้มข้ามปี
- มุ่งเน้นการวิเคราะห์เชิงโครงสร้าง (Macro Trends) โดยไม่เปลี่ยนฐานตัวอย่างระหว่างทาง

---

## 3. นโยบายความเป็นส่วนตัวและความปลอดภัย (Privacy Policy)

1. **ไม่เผยแพร่ข้อมูลผู้ชมรายบุคคล (Zero Viewer PII)**:
   - ไม่มีการเก็บหรือเผยแพร่ชื่อผู้ใช้, email, IP address, หรือ raw viewer hash ใดๆ บนหน้าเว็บสาธารณะ
   - ทุกตัวชี้วัดบนเว็บเป็นข้อมูลรวมเชิงสถิติ (Aggregate Level) เท่านั้น
2. **ขอบเขตการเก็บข้อมูล (Public Interactions Only)**:
   - รวบรวมเฉพาะปฏิสัมพันธ์สาธารณะที่เปิดเผยบน YouTube
   - เส้นเชื่อมระหว่างช่องสะท้อนการพบผู้มีปฏิสัมพันธ์ร่วมกันในตัวอย่างที่เก็บได้ ไม่ใช่การรับรองความสัมพันธ์ส่วนตัวหรือการเป็นผู้ชมทั้งหมด

---

## 4. การทดสอบและดูแลรักษาระบบ (Maintenance & Testing)

### การรันชุดทดสอบ
```bash
python -m pytest tests/ -q
```

### การตรวจสอบความเป็นส่วนตัว (Privacy Audit)
```bash
python scripts/privacy_audit.py
```

### การสร้าง Canonical Registry ใหม่
```bash
python scripts/build_creator_registry.py \
  --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json \
  --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json \
  --resolutions data/registry/identity_resolutions.json \
  --output data/registry/creators.json
```

### การเปิดหน้าเว็บบนเครื่อง
```bash
python -m http.server 8000 -d web
```
เข้าชมผ่านเบราว์เซอร์ที่: `http://localhost:8000`
