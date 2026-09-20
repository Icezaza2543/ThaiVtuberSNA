# Thai VTuber Social Network Analysis & Virtual Creator Registry

โครงการวิจัยและสารบบข้อมูลผู้ผลิตคอนเทนต์เสมือนจริง (VTuber / Virtual Creator) ของประเทศไทย ประกอบด้วย 2 เสาหลักที่ทำงานร่วมกันอย่างสมบูรณ์:
1. **Audience Network Analysis & Observatory (SNA)**: สำรวจโครงสร้างเครือข่ายความสัมพันธ์และแนวโน้มการเติบโตเชิงสถิติ
2. **Evidence-Backed Virtual Creator Registry**: สารบบตัวตนและบัญชีทางการข้ามแพลตฟอร์มที่ตรวจสอบด้วยหลักฐานปฐมภูมิ

---

## 1. ขอบเขตและสถาปัตยกรรมของโครงการ (Architecture)

โครงการเป็น **Unified Static Web Application & Data Pipeline** ที่ประมวลผลข้อมูลจากชุดหลักฐานคงที่ (Sealed Datasets) และเผยแพร่ผ่านหน้าเว็บสาธารณะ 2 ส่วนควบคู่กัน:

```
ThaiVtuberSNA/
├── web/                               # ส่วนแสดงผลเว็บสาธารณะ (Unified Frontend)
│   ├── index.html                     # เว็บหลัก SNA: Network Constellation Graph & Surface Analytics
│   ├── registry.html                  # เว็บทำเนียบ: Thai Virtual Creator Registry (React + Vite + TypeScript)
│   ├── network-ui.js / network.css    # ตัวควบคุมและการแสดงผลกราฟความสัมพันธ์
│   ├── research.js / research.css     # ตัวแสดงผล Dashboard: Surface Analytics + Research v2
│   ├── data.json                      # ข้อมูลโครงสร้างเครือข่ายสำหรับ Graph UI
│   ├── copy-sna-assets.cjs            # สคริปต์ประกอบ static SNA assets เข้า web/dist อัตโนมัติ
│   ├── src/                           # Source code ของ Creator Registry (Views, Components, CSS Tokens)
│   └── research/                      # ข้อมูล Cohort และ Analytics รายปี
├── data/
│   ├── registry.json                  # ฐานข้อมูลสารบบตัวตนข้าม 10 แพลตฟอร์ม (Evidence-Backed SQLite JSON)
│   └── registry/                      # ข้อมูล Canonical Registry เฉพาะกลุ่มประชากร YouTube SNA
│       ├── creators.json              # ทะเบียนทางการ (1,370 baseline + 392 accepted discovery)
│       └── identity_resolutions.json  # ประวัติการจับคู่บัญชีกับตัวตน
├── registry/                          # โมดูล Python หลักสำหรับจัดการสารบบ (CLI, Store, Discovery, Pipeline)
├── scripts/                           # เครื่องมือประมวลผลข้อมูลและตรวจสอบความปลอดภัย
│   ├── build_distribution.py          # Master Script สำหรับตรวจสอบและ build web distribution ทั้งหมด
│   ├── privacy_audit.py               # ตรวจสอบการไม่รั่วไหลของข้อมูลส่วนบุคคล (Zero Viewer PII)
│   ├── audit_data_security.py         # ตรวจสอบความปลอดภัยของ Git Object และประวัติ Commit
│   └── maintenance/export_frontend.py # Export ข้อมูล registry.json สำหรับหน้าเว็บ
└── tests/                             # ชุดทดสอบระบบ 220+ test cases ครอบคลุมทั้ง SNA และ Registry
```

---

## 2. เสาหลักข้อมูลและสารบบ (Data & System Components)

### ก. สารบบข้ามแพลตฟอร์ม (Thai Virtual Creator Registry)
- **แหล่งข้อมูลหลัก**: `data/registry.json`
- **จำนวนตัวตน**: 895 personas (ยืนยันผ่านหลักฐานปฐมภูมิ 873 คน)
- **จำนวนบัญชี**: 4,721 บัญชี ครอบคลุม YouTube, Twitch, TikTok, X, Facebook, Instagram, Kick, GankNow, ฯลฯ
- **เกณฑ์การตรวจสอบ**: การเชื่อมโยงบัญชีและสถานะเสมือนจริงต้องมาจากหลักฐานของเจ้าของบัญชีโดยตรง (First-Party Evidence) เท่านั้น ไม่ใช้การเดาจากชื่อที่คล้ายคลึงกัน

### ข. การวิเคราะห์เครือข่ายและการเติบโต (SNA & Surface Analytics)
- **แหล่งข้อมูลหลัก**: `data/registry/creators.json` (1,645 คน / 1,755 บัญชี)
- **Surface Analytics Cohort**: วิเคราะห์เฉพาะช่องที่ผ่านเกณฑ์ `STRICT_VIRTUAL` เพื่อความแม่นยำสูง
- **Research v2 Longitudinal Cohort**: ติดตามแนวโน้มการเปลี่ยนแปลงของกลุ่มตัวอย่างข้ามปี

---

## 3. หน้าเว็บและการเผยแพร่ (Unified Web Distribution)

เว็บทั้งสองส่วนเชื่อมโยงกันอย่างไร้รอยต่อ:
- **`web/index.html`**: สำรวจดวงดาวเครือข่าย (Constellation Graph), ชุมชน, Bridge score และ Surface Analytics พร้อมปุ่มสลับไปยัง "ทำเนียบครีเอเตอร์"
- **`web/registry.html`**: ค้นหาทำเนียบครีเอเตอร์, ดูหลักฐานยืนยันตัวตน, เมทริกซ์แพลตฟอร์ม พร้อมปุ่มสลับกลับไปยัง "เครือข่าย SNA"
- **การ Build เพื่อ Deploy**: เมื่อรัน `npm run build` ในโฟลเดอร์ `web/` ระบบจะ build Vite bundle และคัดลอกไฟล์ static ทั้งหมดของ SNA เข้าสู่ `web/dist/` โดยอัตโนมัติ ทำให้ได้ static distribution ที่สมบูรณ์พร้อมโฮสต์บน GitHub Pages หรือ static server ใดๆ

---

## 4. ความปลอดภัยและความเป็นส่วนตัว (Security & Privacy Gates)

1. **Zero Viewer PII**: ห้ามมีข้อมูลส่วนบุคคลของผู้ชม (ชื่อ, email, IP, หรือ raw viewer hash) บนหน้าเว็บหรือใน git repository
2. **Boundary Enforcement**: ทุกไฟล์ใน `web/` จะถูกตรวจสอบโดย `test_frontend_public_boundary.py` เพื่อป้องกันไม่ให้มีบัญชีที่อยู่นอกสารบบหลุดเข้าไป
3. **Deterministic Checksums**: ไฟล์รายงานและการคำนวณถูกกำกับด้วย checksum และการแปลง line ending ที่เข้มงวด

---

## 5. คำสั่งที่สำคัญ (Key Commands)

### การตรวจสอบและ Build ระบบทั้งหมด
```bash
# ตรวจสอบและ export ข้อมูลเว็บทั้งหมด
python scripts/build_distribution.py

# รันชุดทดสอบทั้งหมด (220+ tests)
python -m pytest tests/ -q

# ตรวจสอบความปลอดภัยและความเป็นส่วนตัว
python scripts/privacy_audit.py
python scripts/audit_data_security.py --git-only

# ตรวจสอบความถูกต้องของ canonical registry
python -m registry validate
```

### การเรียกดูเว็บในเครื่อง (Local Preview)
```bash
# ดูผ่าน Python HTTP server
python -m http.server 8000 -d web
```
- เปิดหน้า SNA: `http://localhost:8000/index.html`
- เปิดหน้าทำเนียบ: `http://localhost:8000/registry.html`
