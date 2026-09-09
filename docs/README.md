# เอกสารโครงการ

**ปิดขอบเขตเฟสวิจัยแล้ว** การเชื่อมระบบนิเวศเพิ่มเติม งานวิจัยใหม่ การเพิ่มฟีเจอร์ และ T20 ยังคงพักอยู่ ช่องว่างหลักฐานเป็นข้อจำกัดที่เก็บไว้ ไม่ใช่งานรอบใหม่ การเปิดหน้าเว็บใช้ snapshot สาธารณะและไม่เริ่มเก็บข้อมูล

## เริ่มอ่านจากที่นี่

| เรื่อง | เอกสารหลัก |
|---|---|
| การใช้งานและความหมายของกราฟ | [README โครงการ](../README.md) |
| โครงสร้างโค้ด คำสั่งที่รองรับ และผล refactor | [สรุปการจัดระเบียบโค้ด](refactor_summary.md) |
| สถาปัตยกรรมข้อมูลและขอบเขตส่วนตัว | [Data storage architecture](data_storage_architecture.md), [Data classification](data_security_classification.md) |
| ข้อตกลงหน้าตา frontend | [DESIGN.md](frontend/DESIGN.md) |
| ผลวิจัย Research v2 | [รายงาน](research_v2/LONG_RUNNING_RESEARCH_REPORT.md), [โมเดล Outlook](research_v2/OUTLOOK_MODEL.md), [สมมติฐานและข้อจำกัด](research_v2/OUTLOOK_HYPOTHESES.md) |
| การแก้ identity และตัวหารล่าสุด | [Source integrity hotfix](research_v2/SOURCE_INTEGRITY_HOTFIX.md) |
| หลักฐานการตรวจ frontend | [Design audit](frontend_design_audit.md), [QA](frontend_design_qa.md) |
| สิทธิและความเป็นส่วนตัว | [Terms](legal/TERMS.md), [Privacy](legal/PRIVACY.md), [คำขอแก้ไข/ลบข้อมูล](legal/RIGHTS_REQUESTS.md) |

## โครงสร้างที่ใช้จริง

- `core/`: identity, policy และกลไกควบคุมร่วม
- `analytics/`: การแปลงข้อมูลและกฎวิเคราะห์ที่เรียกใช้ซ้ำได้
- `storage/`, `collector/`: ขอบเขตจัดเก็บและเก็บข้อมูลเดิม ไม่ได้เปิดให้เริ่ม production รอบใหม่
- `scripts/analysis_dag.py`: ลำดับ rebuild เดิมที่ reproduction และ observatory ใช้ร่วมกัน
- `scripts/`: CLI, ตัวอ่าน/เขียน artifact และตัวสร้างรายงานที่ยังรองรับ
- `tests/`: ชุดทดสอบ offline และ browser regression; ไม่รวม operator diagnostics ใน `scratch/`
- `web/`: frontend และข้อมูลสาธารณะ ไม่เปลี่ยนหน้าตาในเฟสนี้

## คำสั่งสำหรับตรวจแบบ offline

```powershell
python -m scripts.analysis_dag --list
python -m scripts.analysis_dag --audit
python scripts/audit_creator_identity_mapping.py
python scripts/audit_research_v2_consistency.py
python -m pytest
```

`--list` แสดง DAG เท่านั้น ส่วน `--audit` รวม audit เดิมของ research, Git และ privacy canary ที่ใช้ข้อมูลสังเคราะห์ ไม่เรียก workbook, local private-data scan, collection หรือ rebuild การตรวจ Git ใช้ค่า secret ที่มีในเครื่องเฉพาะในหน่วยความจำเพื่อค้นหาการรั่ว และไม่แสดงค่าเหล่านั้น

คำสั่ง build เดิมยังคงอยู่เพื่อความเข้ากันได้ แต่ไม่มีการอนุญาต production rebuild ในเฟสนี้ ใช้ synthetic fixtures และ temporary outputs เมื่อต้องตรวจผลการแปลงข้อมูล

## เอกสารประวัติ

รายงานตาม milestone ใน `research_v2/`, `evidence/` และเอกสารเดิมด้าน collection ยังเก็บไว้เพื่อรักษาผลวิจัยและ provenance ข้อเสนอใน `refactor/` เป็นประวัติการออกแบบ ไม่ใช่แผนที่ต้องดำเนินการต่อ อ่าน `refactor_summary.md` สำหรับขอบเขตและโครงสร้างปัจจุบัน
