# ไฟล์ข้อมูล Creator-Link Pipeline

## ขั้นตอนและไฟล์

รอบ 2026-09-16 ใช้ prefix วันที่ใน `intake/consolidated/`

| Stage | ไฟล์ | เนื้อหา |
|---|---|---|
| 1 | `youtube-to-x-2026-09-16.jsonl` | YouTube → X candidates (`confidence`, `evidence`) |
| 2 | `x-profile-links-2026-09-16.jsonl` | hub URLs และ platform links จากโปรไฟล์ X |
| 3 | `creator-platform-links-2026-09-16.jsonl` | ลิงก์ปลายทางต่อ YouTube (About + hub crawl) |
| 4 | `reviews/pending/creator-link-map-2026-09-16.json` | ข้อเสนอ `add_account` / `add_candidate` |

ไฟล์ที่ apply แล้วอยู่ที่ `reviews/applied/creator-link-map-2026-09-16-*.json` ในรูปแบบตารางทะเบียน (`evidence`, `accounts`, `personas`, `account_links`)

อย่ารัน `--stage youtube-to-x` ทับ JSONL ที่กรองแล้วโดยไม่สำรอง ไฟล์ `*-pass1-*` เป็นรอบย่อย ไม่ใช่ชุดเต็ม

## แหล่งหลักฐานฟรี (ก่อนเรียก X Search)

- `intake/*-youtube-owner-crosslinks*.jsonl` — TikTok/Twitch/hub จาก About (รอบเก็บเดิมไม่เก็บ X)
- `intake/*-youtube-persona-evidence*.jsonl` และ `*-twitch-youtube-owner-evidence*.jsonl` — คำอธิบายช่องที่มี URL
- `scripts/collect/collect_youtube_about.py` — ตอนนี้เก็บ `x_urls` ด้วย

จับคู่ intake ผ่าน `youtube_channel_id` (UC…) กับ `accounts.platform_id` ไม่ใช่ `acct_…`

## คำสั่ง

```sh
python -m registry map-creators --help
python -m registry map-creators --stage hub-to-platforms
python -m registry map-creators --stage build-review
python -m registry apply --file reviews/pending/CHANGE.json --dry-run
python -m registry apply --file reviews/applied/CHANGE.json
python -m registry validate
```

รายงานล่าสุด: `reports/current/platform-coverage.json`, `reports/current/creator-platform-matrix.json`, `reports/archive/2026-09-16/sna-platform-coverage.json`  
ส่งออก SNA ท้องถิ่น (gitignored): `dist/sna/creator-platform-registry.jsonl`

## กติกา apply รอบนี้

- บัญชี TikTok/Twitch ใหม่ต้องมี stable ID
- X ใช้ `id_namespace=handle` จนกว่าจะมี user id
- Facebook ใช้ `profile_id` (ตัวเลข) หรือ `handle` ของเพจ ไม่เก็บ URL `/photos` `/posts`
- Instagram ใช้ `handle`
- ลิงก์ที่ชื่อไม่ตรงหรือเป็นบัญชีค่ายคง `needs_evidence`
- reviewer ของรอบ pipeline นี้เป็นป้ายงานสาธารณะ `grok:creator-link-pipeline`
