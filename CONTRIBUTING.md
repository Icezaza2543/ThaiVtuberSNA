# ส่งรายชื่อและแก้ข้อมูล

เสนอช่องผ่าน Issue template "เสนอครีเอเตอร์" โดยใส่ public persona name, platform URL, หลักฐานว่าเป็น virtual creator และหลักฐานความเกี่ยวข้องกับไทย การส่งรายชื่อไม่ทำให้ได้รับสถานะ verified โดยอัตโนมัติ

การแก้สถานะหรือประวัติ ให้ใส่ URL ประกาศเจ้าตัว/ค่าย วันที่มีผล และคำอธิบายว่าข้ออ้างเดิมคลาดเคลื่อนอย่างไร การแจ้งแก้ไขหรือนำข้อมูลออกติดต่อผ่านช่องทางใน LICENSE ได้

สำหรับผู้แก้ทะเบียน ใช้ [คู่มือ review](docs/review.md) และทดสอบก่อนส่ง pull request:

```sh
python -m unittest discover -s tests -v
python -m registry apply --file reviews/your-reviewed-change.json --dry-run
python -m registry validate
python -m registry report --as-of 2026-09-12
```

ไม่ส่ง credentials ข้อมูลหลัง login ที่ไม่อนุญาตให้เปิดเผย หรือการเชื่อมตัวบุคคลที่เจ้าตัวไม่ได้ประกาศ เก็บเฉพาะข้อมูลที่จำเป็นต่อทะเบียนสาธารณะ
