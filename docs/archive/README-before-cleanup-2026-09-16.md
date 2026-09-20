# Historical README snapshot; not current instructions

# ThaiVirtualCreatorRegistry

ทะเบียนครีเอเตอร์เสมือนที่เกี่ยวข้องกับชุมชนไทย บน YouTube, Twitch, TikTok และ Facebook

เก็บบัญชีสาธารณะ persona หลักฐาน ประวัติสังกัด และเหตุการณ์ debut / redebut / graduation / return เพื่อค้นหาและรายงานจำนวนพร้อมที่มาและวันที่อ้างอิง ใช้เป็นต้นทางทะเบียนให้ [ThaiVtuberSNA](https://github.com/Icezaza2543/ThaiVtuberSNA) ผ่าน snapshot ที่ระบุเวอร์ชัน

**สถานะ ณ 2026-09-16:** Creator-link pipeline ผูกบัญชีข้ามแพลตฟอร์มจาก YouTube About / X / hub แล้ว **845+ persona verified**, ลิงก์ verified ประมาณ **2,400** ครอบคลุม YouTube, TikTok, Twitch, X, Facebook, Instagram ดู [coverage ล่าสุด](reports/current/platform-coverage.json) และ [สถาปัตยกรรม pipeline](docs/architecture.md)

**สถานะ ณ 2026-09-13:** ตรวจโปรไฟล์ TikTok 1,011 URL ได้ **863 บัญชีจริงพร้อมรหัส `web_user_id` จาก TikTok** และบันทึกลง `data/registry.json` แล้ว ในจำนวนนี้ยืนยัน **390 persona บน 391 บัญชี TikTok** ด้วยหลักฐานเจ้าตัว ส่วน YouTube ตั้งต้น 1,370 บัญชีและป้ายกำกับเดิมยังคงเดิม Facebook ยังไม่ได้เริ่มเก็บข้อมูลสด

**รอบ Twitch:** เพิ่ม **646 บัญชีพร้อม numeric `user_id`** จากไดเรกทอรีไทย, vdb, Thai ranking, HoloList, Bācharu และลิงก์เจ้าของ YouTube ยืนยัน **217 persona บน 217 บัญชี Twitch** เป็น persona เดิม 60 และ persona ใหม่ 157; ทั้งทะเบียนจึงมี 547 persona ที่ผ่าน review ยอดข้ามแพลตฟอร์มบวกตรง ๆ ไม่ได้ ดู [บัญชี Twitch](reports/twitch_accounts.csv), [Twitch ที่ยืนยัน persona](reports/verified_twitch.csv) และ [รายงานรอบนี้](intake/2026-09-13-twitch-collection-report.md)

เปิดใช้ [CSV TikTok ที่ยืนยัน persona แล้ว](reports/verified_tiktok.csv) หรือ [CSV บัญชี TikTok ทั้ง 863 บัญชีพร้อมรหัสและหลักฐาน](reports/tiktok_accounts.csv) ได้ทันที ยอดบัญชีรวมมีบัญชีค่าย/กลุ่มและบัญชีที่ยังไม่ได้ยืนยันขอบเขต VTuber จึงไม่เท่ากับยอด persona ดู [บันทึกการรวบรวม](intake/README.md) และ [ผลตรวจความครอบคลุม](intake/2026-09-13-collection-audit.json)

1,370 เป็นจำนวนบัญชีตั้งต้น การยืนยัน persona และสถานะข้ามแพลตฟอร์มอยู่ในคิว review ป้ายกำกับเดิมยังดูได้ในรายงาน เช่น active 1,032 / hiatus 278 / graduated 3 / unknown 57 ซึ่งเป็นสถานะใน snapshot เดิม ไม่ใช่จำนวนปัจจุบันที่ตรวจซ้ำแล้ว

[รายงานทะเบียน](reports/README.md) · [pipeline](docs/data-pipeline.md) · [สถาปัตยกรรม](docs/architecture.md) · [วิธีค้นหา](docs/discovery.md) · [หมวดหมู่และสถานะ](docs/taxonomy.md) · [โครงสร้างข้อมูล](docs/data-model.md) · [วิธี review](docs/review.md)

## Analytics Dashboard

รอบ 2026-09-13 เพิ่มตัวเก็บสถิติ TikTok/Twitch โดยตรง ประวัติ YouTube จาก Chuy-san/Hub
และข้อมูลโปรไฟล์ไทยจาก Bācharu/HoloList/USADA เปิด [Dashboard](dist/2026-09-13-analytics-v1/dashboard.html)
เพื่อค้นบัญชี ดูอันดับแยกแพลตฟอร์ม กราฟผู้ติดตาม/ยอดวิว และรายการคอนเทนต์ที่มีหลักฐาน
ดู [รายงาน analytics](reports/analytics-2026-09-13.md) และ [นิยาม/คำสั่งรัน](docs/analytics.md)
ข้อมูลเป็น snapshot จริงจากต้นทาง ไม่ใช่ live sync; รายการแหล่งรองยังไม่ใช่ persona ที่ผ่าน review

## เริ่มใช้งาน

ใช้ Python 3.11 ขึ้นไป และ standard library ไม่ต้องติดตั้ง dependency เพิ่ม คำสั่งต่อไปนี้รันจากราก repo:

```sh
python -m registry validate
python -m registry report --as-of 2026-09-16
python -m unittest discover -s tests -v
python -m registry map-creators --help
```

รายงานอยู่ที่ `reports/README.md`, `reports/summary.json`, `reports/current/` และ CSV สำหรับบัญชี persona เหตุการณ์ คิวตรวจ และ candidate ระบุ `--as-of` เป็นวันที่ที่ต้องการวิเคราะห์กิจกรรม

## ผูกบัญชีข้ามแพลตฟอร์ม (map-creators)

ตามลิงก์ที่เจ้าของช่อง YouTube เผยแพร่ไปยัง X, hub และแพลตฟอร์มอื่น แล้วออกไฟล์ review:

```sh
python -m registry map-creators --stage youtube-to-x
python -m registry map-creators --stage x-to-hub --headless --profile-dir profiles/x-logged-in
python -m registry map-creators --stage hub-to-platforms
python -m registry map-creators --stage build-review
python -m registry apply --file reviews/applied/CHANGE.json --dry-run
```

รายละเอียดไฟล์และกติกาหลักฐานอยู่ที่ [docs/data-pipeline.md](docs/data-pipeline.md)

## เก็บโปรไฟล์ TikTok จริง

ตัวเก็บ public creator embed ใช้ Python standard library อ่านชื่อ bio รหัสบัญชี และคำบรรยายวิดีโอของเจ้าของบัญชีได้โดยไม่ต้องล็อกอิน คำสั่งนี้ใช้คิว URL จริงที่รวบรวมไว้แล้วและสร้างไฟล์ผลรอบใหม่:

```sh
python -m registry.tiktok --input intake/2026-09-13-tiktok-profile-queue-03.json --output intake/tiktok-next-observation.jsonl --workers 6
```

ชื่อ output ต้องยังไม่มีอยู่ ไฟล์ผลเป็นหลักฐานสังเกตการณ์ การบันทึกบัญชี/persona ใช้ไฟล์ review และ validator ตามขั้นตอนด้านล่าง คำสั่งนี้ตรวจ URL ที่ระบุ ไม่ใช่ API ค้นหาทุกช่องใน TikTok

## เพิ่มรายชื่อด้วยตนเอง

ตัวอย่างต่อไปนี้ใช้ URL สมมติ ให้แทนด้วยบัญชีและแหล่งอ้างอิงจริงก่อนรัน:

```sh
python -m registry candidate --platform tiktok --url "https://www.tiktok.com/@REPLACE_ME" --name "ชื่อที่ใช้สาธารณะ" --source-url "https://www.tiktok.com/@REPLACE_ME" --query "VTuberTH"
```

ใช้ `--platform twitch`, `facebook` หรือ `youtube` ได้ เก็บทุกครั้งที่พบใน `discovery_runs` และ `discovery_hits` รายชื่อยังเป็น `needs_evidence` จนผ่าน review หากยังหา stable platform ID ไม่ได้ ให้เก็บเป็น candidate ต่อไป

## ค้นหา Twitch

ตัวอ่านโปรไฟล์สาธารณะรันจริงแล้ว ไม่ต้องใช้ OAuth และตรวจได้แม้ช่องออฟไลน์:

```sh
python -m registry.twitch_public --input intake/2026-09-13-twitch-expanded-source-queue.json --output intake/twitch-next-observation.jsonl
```

output ต้องเป็นไฟล์ใหม่ อ่าน numeric ID, คำแนะนำตัว, ภาษาที่ตั้งไว้ และ social links; ไม่ยืนยัน persona อัตโนมัติ Public website application ID อ่านจากหน้า Twitch ในหน่วยความจำ ไม่ใช่ access token และไม่บันทึกลง repo วิธีนี้ไม่ใช่ Helix และไม่อ้างว่าค้นพบครบทั้งแพลตฟอร์ม

ตั้ง `TWITCH_CLIENT_ID` และ `TWITCH_ACCESS_TOKEN` ผ่าน environment ของเครื่อง จากนั้น:

```sh
python -m registry twitch-discover --language th --max-pages 3
```

คำสั่งนี้เรียก Twitch Helix จริงเมื่อผู้ใช้รัน จำกัด 1–20 หน้าและครั้งละไม่เกิน 100 สตรีม/หน้า บันทึกคิวตรวจของบัญชีที่พบทั้งหมดในภาษาที่เลือก รวมช่องที่ไม่มีแท็ก VTuber ค่าที่พบจึงเป็น leads และอาจมี streamer ทั่วไป รันเดียวไม่ครอบคลุมผู้ที่ออฟไลน์

ไม่แสดงหรือบันทึก token หาก API ล้มเหลวจะเก็บผลที่ได้พร้อม `http_error` และคืน exit code 1 ไม่มี scheduler ตั้งไว้โดยอัตโนมัติ ดู [ข้อจำกัดแพลตฟอร์ม](docs/discovery.md)

## ค้นหาหลายแพลตฟอร์มด้วย Playwright (discover-all)

รองรับการเปิดเบราว์เซอร์ Chromium ผ่าน Playwright เพื่อค้นหารายชื่อครีเอเตอร์สาธารณะข้ามแพลตฟอร์ม โดยไม่ต้องใช้ API key และไม่มี dependency ของ LLM:
- **Core Tested Platforms**: YouTube, Twitch (พร้อม stable numeric `user_id` resolution), TikTok (พร้อม stable numeric `web_user_id` resolution), GankNow (ค้นหาครีเอเตอร์และเปิดโปรไฟล์ดึง outbound social links แบบ bounded crawl)
- **Experimental Platforms**: Facebook, Instagram, X, Kick, Bilibili, Niconico (อาจพบ login wall หรือ rate limit ตามนโยบายของเว็บ)

ติดตั้ง optional dependency:
```sh
pip install -e ".[discovery]"
playwright install chromium
```

รันการค้นหาแบบเปิดหน้าต่างเบราว์เซอร์ (headed mode เป็นค่าเริ่มต้น):
```sh
python -m registry discover-all
```

หรือรันแบบ headless พร้อมจำกัดแพลตฟอร์มหรือคำค้น:
```sh
python -m registry discover-all --headless --platform youtube --platform twitch --query "VTuberTH" --max-results 20 --max-pages 3
```

ออปชันที่รองรับ:
- `--headless`: รันเบราว์เซอร์ในโหมดเบื้องหลัง
- `--platform <name>`: เลือกระบุแพลตฟอร์ม (ระบุซ้ำได้ เช่น `--platform youtube --platform twitch`)
- `--query <text>`: เลือกระบุคำค้น (ระบุซ้ำได้)
- `--expand-registry`: นำ handle และชื่อจากทะเบียนเดิมมาเป็น search seeds ค้นหาข้ามแพลตฟอร์ม (สร้าง candidate `needs_evidence` โดยไม่ auto-link persona)
- `--max-results <n>`: จำกัดจำนวนผลลัพธ์สูงสุดต่อแพลตฟอร์ม/คำค้น (ค่าเริ่มต้น: 20)
- `--max-pages <n>`: จำกัดจำนวนรอบ bounded scrolling/pagination ต่อคำค้น (ค่าเริ่มต้น: 3)
- `--timeout <seconds>`: กำหนด timeout ในการโหลดหน้าเว็บและ selector readiness (วินาที, ค่าเริ่มต้น: 30)
- `--profile-dir <path>`: กำหนดไดเรกทอรี browser profile ในเครื่อง (ข้อมูล session/auth จะคงอยู่ในเครื่องและไม่ถูกเขียนลงทะเบียนหรือ git)

ระบบแกนหลัก (`validate`, `report`, `candidate`, `apply`, `export`) และ unit tests ทั้งหมดสามารถทำงานได้โดยไม่ต้องติดตั้ง Playwright

## Review และส่งออก

ค้นรายการรอตรวจ กรองแพลตฟอร์มหรือชื่อ และดูหลักฐานที่บันทึกไว้ได้โดยไม่แก้ทะเบียน:

```sh
python -m registry queue --platform tiktok --limit 20
python -m registry queue --kind account_issue --query lifecycle_conflict
python -m registry inspect candidate CANDIDATE_ID
python -m registry inspect account ACCOUNT_ID
```

แทน `CANDIDATE_ID` / `ACCOUNT_ID` ด้วย `record_id` จากคิว ใช้ `--offset 20` เพื่อดูหน้าถัดไป คิวเริ่มจากรายการที่ยังรอตรวจ และแยกจำนวน candidate ออกจากจำนวนปัญหาของบัญชี หลักฐานที่แสดงคงสถานะ review เดิม ไม่ถือว่าการปรากฏในผลค้นเป็นการยืนยัน

เมื่อเตรียมไฟล์ review แล้ว ทดลองตรวจและดูค่าก่อน/หลังด้วย `--dry-run` จากนั้นใช้ไฟล์เดียวกันเพื่อบันทึกจริง:

```sh
python -m registry apply --file reviews/your-reviewed-change.json --dry-run
python -m registry apply --file reviews/your-reviewed-change.json
python -m registry validate
python -m registry report --as-of 2026-09-12 --active-days 90
python -m registry export --as-of 2026-09-12 --output dist/2026-09-12-v1
```

ไฟล์ review ต้องสร้างตาม [คู่มือ](docs/review.md) snapshot ที่ส่งออกมี registry, รายงาน, `approved_youtube.csv` และ manifest SHA256 แต่ละไฟล์ ชื่อโฟลเดอร์ snapshot ต้องใหม่เสมอ การส่งออกไม่ได้อัปโหลดหรือเปลี่ยนข้อมูลใน ThaiVtuberSNA

`approved_youtube.csv` จะมีเฉพาะบัญชีที่เชื่อมกับ persona ที่ผ่าน review และมีช่วงวันที่หลักฐานครอบคลุมวันอ้างอิง ทะเบียนตั้งต้นจึงส่งออกไฟล์นี้เป็นหัวตารางว่างจนกว่าจะตรวจความเชื่อมโยงสำเร็จ

## โครงสร้าง repo

| ส่วน | หน้าที่ |
|---|---|
| `data/registry.json` | ข้อมูลหลักที่ติดตามการเปลี่ยนแปลงด้วย Git |
| `schemas/registry.sql` | สัญญาข้อมูลที่ตัว validator บังคับจริง |
| `registry/` | CLI, import, discovery, review validation, รายงาน และ snapshot |
| `reports/` | สารบัญและตัวเลขที่สร้างจากข้อมูลหลัก |
| `reviews/` | เอกสารวิธีส่งชุดแก้ไขที่ผ่านการตรวจหลักฐาน |
| `docs/` | นิยาม วิธีนับ แผนค้นหา และแหล่งอ้างอิง |
| `tests/` | ทดสอบตัวตนซ้ำ วันอ้างอิง สถานะ และ atomic update ด้วยข้อมูลสมมติ |

ดู [CONTRIBUTING.md](CONTRIBUTING.md) สำหรับการเสนอช่องและแก้ข้อมูล ข้อมูล `unknown` และ `needs_evidence` เป็นส่วนหนึ่งของผลรายงาน เก็บชื่อ/ช่องที่เจ้าตัวใช้สาธารณะและเชื่อม persona ด้วยประกาศที่ตรวจได้

## สิทธิ์และที่มา

คงสถานะ Internal Research / All Rights Reserved ตามโครงการต้นทาง รายละเอียดใน [LICENSE](LICENSE) และ [บันทึกการนำเข้า](docs/provenance.md) ข้อเท็จจริง ชื่อช่อง ตัวละคร และผลงานของบุคคลอื่นยังเป็นของผู้ถือสิทธิ์เดิม การสร้าง repo นี้ไม่ได้เปลี่ยนเป็นใบอนุญาตโอเพนซอร์ส
