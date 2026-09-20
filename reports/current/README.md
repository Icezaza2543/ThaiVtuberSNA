# สถานะทะเบียน ThaiVirtualCreatorRegistry

วันที่อ้างอิงกิจกรรม: 2026-09-17 · หน้าต่างกิจกรรม 90 วัน

จำนวน inventory รวมการค้นพบที่บันทึกทั้งหมด ส่วน lifecycle ใช้หลักฐานลงวันที่ที่ผ่าน review แล้ว

| แพลตฟอร์ม | บัญชีในทะเบียน | Persona ยืนยันและมีหลักฐานการใช้บัญชี ณ วันอ้างอิง |
|---|---:|---:|
| youtube | 1400 | 0 |
| twitch | 845 | 0 |
| tiktok | 962 | 0 |
| facebook | 211 | 0 |
| instagram | 120 | 0 |
| x | 1150 | 0 |
| kick | 2 | 0 |
| ganknow | 28 | 0 |
| bilibili | 0 | 0 |
| niconico | 0 | 0 |
| carrd | 0 | 0 |
| linktree | 1 | 0 |
| litlink | 2 | 0 |
| kofi | 0 | 0 |
| patreon | 0 | 0 |
| vgen | 0 | 0 |
| website | 0 | 0 |

ดาวน์โหลด [บัญชี TikTok พร้อมรหัสและหลักฐาน](tiktok_accounts.csv) · [TikTok ที่ยืนยัน persona และการใช้บัญชี ณ วันอ้างอิง](verified_tiktok.csv)

`tiktok_accounts.csv` นับบัญชี ส่วน `verified_tiktok.csv` มีหนึ่งแถวต่อคู่ persona/บัญชี จึงอาจมีหลายแถวต่อ persona ได้ คอลัมน์ `platform_id` ต้องนำเข้าเป็นข้อความเมื่อเปิดด้วยสเปรดชีต

Persona ที่ผ่าน review: 873 · Candidates: 878

## สถานะที่ยืนยันได้

| สถานะ | Persona |
|---|---:|
| active_streaming | 0 |
| active_posting | 0 |
| pre_debut | 0 |
| hiatus | 0 |
| graduated | 1 |
| no_recent_evidence | 0 |
| unknown | 872 |
| conflict_needs_review | 0 |

## สถานะที่สืบทอดจากทะเบียนเดิม

ค่าต่อไปนี้เป็นป้ายกำกับในแหล่งเดิม ยังไม่ได้ตรวจซ้ำตามเกณฑ์ข้ามแพลตฟอร์มของ repo นี้

| ป้ายกำกับเดิม | บัญชี |
|---|---:|
| active | 1032 |
| graduated | 3 |
| hiatus | 278 |
| unknown | 57 |

## คิวตรวจ

| เหตุผล | รายการ |
|---|---:|
| legacy_identity_collision | 2 |
| legacy_scope_review | 1370 |
| lifecycle_conflict | 9 |

### Candidate review

| สถานะ candidate | รายการ |
|---|---:|
| needs_evidence | 621 |
| verified | 257 |

คิวปัญหาของบัญชีและ candidate เป็นคนละหน่วย บัญชีหนึ่งมีหลายปัญหาได้

ดู [candidates.csv](candidates.csv) หรือใช้ `python -m registry queue --platform tiktok`
ดูหลักฐานของรายการด้วย `python -m registry inspect candidate CANDIDATE_ID`


ค่า 0 ในหมวดที่ยังไม่มี review หมายถึงยังไม่มีข้อมูลยืนยันในทะเบียน ไม่ได้หมายถึงไม่มีอยู่จริง

## แหล่งที่ทะเบียนเดิมอ้างอิง

หนึ่งบัญชีอ้างอิงหลายแหล่งได้ จึงบวกเป็นจำนวนบัญชีรวมไม่ได้

| แหล่ง | บัญชีที่อ้างถึง |
|---|---:|
| Thai VTuber Ranking | 1335 |
| Virtual YouTuber Fandom Wiki | 143 |
| Manual Audit | 49 |
| User Verification | 7 |
| YouTube Channel | 7 |

## สังกัดตามป้ายกำกับเดิม

| สังกัด | บัญชี |
|---|---:|
| Independent | 1183 |
| Algorhythm Project | 39 |
| Pixela Project | 25 |
| Virtual Zeven (VZ) | 21 |
| Lumina Live | 19 |
| Euphora Project | 12 |
| AStars Production | 10 |
| Autumnia | 8 |
| DPX | 7 |
| Polygon Official | 7 |
| ALF | 5 |
| V.W.Y | 4 |
| Flora Project | 4 |
| OAL | 4 |
| Ti19t | 3 |
| RPG | 3 |
| HZ | 3 |
| EXia | 2 |
| Paralist | 2 |
| Genesis Project | 2 |
| EYLZ | 1 |
| Pandora | 1 |
| Vtopia | 1 |
| Loveland Project | 1 |
| ATX | 1 |
| WACTOR | 1 |
| STP | 1 |

## ประวัติเหตุการณ์

ความต่อเนื่อง persona ที่มีประกาศยืนยัน: 0
เหตุการณ์ยืนยันที่ยังไม่มีวันที่ระดับวัน: 0

ดู lifecycle events รายปีใน [summary.json](summary.json) และข้อมูลแถวใน [lifecycle_events.csv](lifecycle_events.csv)
