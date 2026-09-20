# สถาปัตยกรรม Creator-Link Pipeline

เส้นทาง enrichment เดิมของ pipeline นี้เริ่มจากบัญชี YouTube ในทะเบียน แล้วตามลิงก์ที่เจ้าของช่องเผยแพร่ไปยัง X, หน้า hub (Linktree/Carrd ฯลฯ) และแพลตฟอร์มอื่น ไม่เดาจากชื่อหรือรูปโปรไฟล์อย่างเดียว

เส้นทางนี้ **ไม่ใช่เกณฑ์รับรอง virtual creator** ผู้ที่มี Twitch/TikTok เพียง
บัญชีเดียวใช้หลักฐานจากบัญชีตนเองผ่าน review ได้ตาม [คู่มือ review](review.md)
ไม่มีข้อกำหนดว่าต้องมี YouTube หรือ X ก่อน

รันด้วย `python -m registry map-creators` ผลแต่ละขั้นเป็น JSONL ใน `intake/consolidated/` จากนั้น Stage 4 สร้างข้อเสนอใน `reviews/pending/` ก่อน `python -m registry apply`

```
YouTube seeds (data/registry.json)
        │
        ▼
Stage 1  youtube-to-x
        YouTube About / intake evidence → official X
        │  intake/consolidated/youtube-to-x-<date>.jsonl
        ▼
Stage 2  x-to-hub
        หน้าโปรไฟล์ X → hub URLs และลิงก์แพลตฟอร์มตรง
        │  intake/consolidated/x-profile-links-<date>.jsonl
        ▼
Stage 3  hub-to-platforms
        คลาน hub + ลิงก์จาก YouTube About
        │  intake/consolidated/creator-platform-links-<date>.jsonl
        ▼
Stage 4  build-review
        resolve stable ID, ตัดบัญชีค่าย, ออกข้อเสนอ
        │  reviews/pending/creator-link-map-<date>.json
        ▼
apply --dry-run → apply → validate
        reviews/applied/
```

## หลักฐานที่ยอมรับ

- หน้า YouTube About ชี้ไปยังบัญชีปลายทาง
- โปรไฟล์ X (bio/website) ชี้กลับมา YouTube หรือชี้ไป hub เดียวกัน
- หน้า Linktree/Carrd/lit.link ที่ทั้งสองฝั่งลิงก์ถึง

ไม่ใช้ความคล้ายของชื่อหรือ avatar เป็นหลักฐานเดียว บัญชีค่าย/กลุ่ม (`arp_vtuber`, `21pm.official` ฯลฯ) ไม่ถูกผูกเป็นบัญชีบุคคล

## ความมั่นใจ (confidence)

| ระดับ | ความหมาย |
|---|---|
| high | หลักฐาน owner cross-link จากแพลตฟอร์มใดก็ได้; เป็นลำดับตรวจ ไม่ใช่ verified |
| medium | มี X หรือ hub แต่โซ่ไม่ครบ; ไม่ลดระดับเพียงเพราะเป็น Facebook/Instagram |
| low | ไม่มีโซ่เจ้าของช่อง หรือธงบัญชีค่าย |

`add_account` ใช้เมื่อมี stable ID (TikTok `web_user_id`, Twitch `user_id`)  
`add_candidate` ใช้เมื่อยังไม่มี ID หรือต้องให้คนตรวจ

## โมดูล

| ไฟล์ | หน้าที่ |
|---|---|
| `registry/urls.py` | normalize URL/handle, แยกแพลตฟอร์ม, ดึงลิงก์จาก HTML |
| `registry/web.py` | HTTP stdlib + Playwright |
| `registry/pipeline/runner.py` | orchestrator แต่ละ stage |
| `registry/pipeline/hubs.py` | อ่านโปรไฟล์ X และคลาน hub |
| `registry/pipeline/evidence.py` | โซ่หลักฐาน, resolve ID, ข้อเสนอ review |
| `registry/pipeline/grok_x.py` | ทางเลือก X Search ผ่าน xAI API |

CLI ไม่เลือกไฟล์ `*-pass1-*` เมื่อหา input ของ stage ถัดไป แต่ใช้ไฟล์ที่แก้ล่าสุด

## Stage 4 ที่ไม่บังคับ YouTube

`registry.pipeline.evidence` และ `scripts/review/stage4_classify_and_apply.py`
รับ `source_account_id`, `source_platform`, `source_url`, `source_platform_id`
และ `source_evidence_id` สำหรับบัญชีต้นทางแพลตฟอร์มใดก็ได้ โดยยังอ่าน
`youtube_*` ใน historical input เดิมได้ ไม่ต้องย้ายหรือเขียนทับหลักฐานย้อนหลัง
source แบบใหม่ที่ใช้เตรียม ownership rows ต้องอ้าง evidence หลักที่เก็บไว้จริง

เลือก persona ต้นทางได้ต่อเมื่อมี reviewed ownership link และ reviewed persona
ตรงกันเพียงหนึ่งรายการ หากเป็นบัญชีกลุ่มที่มีหลาย persona จะระบุ
`ambiguous_source_persona` และไม่เลือกตัวแรก/ตัวท้ายแทนผู้ตรวจ
ข้ามเฉพาะบัญชีต้นทางจริง ไม่ข้าม YouTube ทั้งแพลตฟอร์มเมื่อ source เป็น Twitch

Classifier proposals ทุกตัวมี `needs_human_review=true` แม้ confidence เป็น high
`build_apply` ค่าเริ่มต้นสร้าง link เป็น `needs_evidence`; การเตรียม verified rows
ต้องส่ง reviewer และ reviewed_at ที่ระบุชัด แล้ว dry-run/ตรวจ diff ก่อน apply
ไม่มีการสร้าง verified persona หรือ apply เข้าฐานข้อมูลอัตโนมัติจากขั้นตอนนี้
