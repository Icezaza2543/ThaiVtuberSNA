# รายงานการตรวจสอบและจัดทำทะเบียน Thai VTuber (ระยะที่ 1 - ฉบับสมบูรณ์หลังการตรวจทาน)

**วันที่และเวลาตรวจสอบล่าสุด:** 2026-09-06 15:23:57 UTC  
**สถานะการผ่านเกณฑ์ระยะที่ 1 (Phase 1 Gate Criteria):** **PASSED (100% Resolved)**  
**ข้อห้ามการเก็บข้อมูล:** ไม่มีคอมเมนต์หรือ Live Chat ใด ๆ ถูกเก็บในระยะนี้ (ตรวจสอบเฉพาะ Metadata ช่อง)

---

## 1. สรุปภาพรวมความครอบคลุม (Coverage Overview)

| ตัวชี้วัด | จำนวน | ร้อยละ |
|---|---|---|
| **ช่องที่ผ่านการตรวจสอบทั้งหมด (Total Evaluated)** | **1369** | 100.0% |
| **ยืนยันตัวตน Thai VTuber (CONFIRMED)** | **1363** | 99.56% |
| **ช่องที่คัดออกถาวร (EXCLUDED Non-Thai)** | **6** | 0.44% |
| **ช่องใน Quarantine รอตอบรับ (UNCONFIRMED)** | **0** | **0.0% (ตรวจสอบครบ 100%)** |

> [!NOTE]
> จากเดิมที่มีช่องรอตรวจสอบ (Unconfirmed Quarantine) จำนวน 55 ช่อง ได้รับการสืบค้นและตรวจสอบประวัติจริงครบถ้วน 100% โดย:
> 1. **เลื่อนสถานะ 49 ช่อง** ขึ้นเป็น Thai VTuber ที่ได้รับการยืนยัน (**CONFIRMED**) พร้อมบันทึกสังกัดและสถานะที่ถูกต้อง
> 2. **คัดออก 6 ช่อง** ที่เป็น VTuber / บุคลากรต่างชาติ (**EXCLUDED**) พร้อมบันทึกเหตุผลใน `data/excluded_channels.csv`

---

## 2. สถานะความเคลื่อนไหวของ Thai VTuber (Activity Lifecycle)

คำนวณจากประวัติการเผยแพร่วิดีโอล่าสุดและสถานะการประกาศจบการศึกษา/พักงาน:

| สถานะ (Activity Status) | เกณฑ์การพิจารณา | จำนวนช่อง | ร้อยละ |
|---|---|---|---|
| **Active** | มีการเผยแพร่วิดีโอภายใน 180 วันที่ผ่านมา | **1025** | 75.2% |
| **Hiatus** | ไม่มีความเคลื่อนไหวเกิน 180 วัน | **278** | 20.4% |
| **Graduated / Retired** | ประกาศจบการศึกษาหรือรีไทร์อย่างเป็นทางการ | **3** | 0.2% |
| **Unknown** | ช่องไม่มีวิดีโอสาธารณะ หรือตั้งค่าส่วนตัว | **57** | 4.2% |

---

## 3. การกระจายตัวตามสังกัดและกลุ่ม (Agency & Group Distribution)

Thai VTuber ในทะเบียนแบ่งตามสังกัด (แสดง 15 ลำดับแรก):

| สังกัด / กลุ่ม | จำนวนช่อง | ร้อยละ |
|---|---|---|
| Independent | 1242 | 91.1% |
| Algorhythm Project | 39 | 2.9% |
| Pixela Project | 25 | 1.8% |
| Lumina Live | 19 | 1.4% |
| Euphora Project | 12 | 0.9% |
| Polygon Official | 7 | 0.5% |
| OAL | 3 | 0.2% |
| V.W.Y | 1 | 0.1% |
| ATX | 1 | 0.1% |
| DPX | 1 | 0.1% |
| EXia | 1 | 0.1% |
| ALF | 1 | 0.1% |
| Autumnia | 1 | 0.1% |
| Flora Project | 1 | 0.1% |
| Paralist | 1 | 0.1% |

---

## 4. ผลการตรวจสอบ 55 ช่องที่ได้รับการตรวจทาน (Audit Breakdown)

### 4.1 รายชื่อ Thai VTuber ที่ได้รับการยืนยันเพิ่มเติม (49 ช่อง)

| ลำดับ | ช่อง | Handle | สังกัด | สถานะตรวจสอบ | สถานะระบบ |
|---|---|---|---|---|---|
| 1 | [Reiden_R Ch.](https://www.youtube.com/channel/UC31u9DPv_zbrasL8FTH7K5g) | `@reiden_r` | Independent |  Active | `active` |
| 2 | [NoA Noaris](https://www.youtube.com/channel/UCGAYOnH9azmAmcHpzRWZsOg) | `@noa_noaris` | Independent |  Active | `active` |
| 3 | [fxoverpur](https://www.youtube.com/channel/UCH3mEs_fK3r0M2hJ9NsgNPg) | `@fxoverpur` | Independent |  Active | `active` |
| 4 | [Akaku Mikoni | V.W.Y](https://www.youtube.com/channel/UCUOVWfFzNwIfu3_MfXegyPA) | `@akakumikoni` | V.W.Y |  Active | `active` |
| 5 | [Koharu Channel](https://www.youtube.com/channel/UCUlc9fwNihOqufbS8KtakvA) | `@koharuchannel` | Independent |  Hiatus (>180 วัน) | `hiatus` |
| 6 | [Lyrics 🌙](https://www.youtube.com/channel/UCaCHWJ4_dp4ovreQ91lp3Iw) | `@moonshinelyrics_z` | Independent |  Active | `active` |
| 7 | [Newzkung Raccoonza](https://www.youtube.com/channel/UC_nmh9XycGlquouvai2UC6g) | `@newzkungraccoon` | Independent |  Active | `active` |
| 8 | [Ané Monie Ch. | OAL](https://www.youtube.com/channel/UCsB043n4HJ1SfywowZACmug) | `@monie_oal` | OAL |  Active | `active` |
| 9 | [Byte001_SLR](https://www.youtube.com/channel/UCtECeyZ_Uc-oE4fJCt3YPoA) | `@byte001_slr` | Independent |  Active | `active` |
| 10 | [Titorch Ch.](https://www.youtube.com/channel/UCtHdI-Bb1OWP9VaQpBHy7kg) | `@titorch_ch` | Independent |  Active | `active` |
| 11 | [Zion《ATX》](https://www.youtube.com/channel/UCONVwO_B2jxgzpbsVopQ6fw) | `@zion_atx` | ATX |  Active | `active` |
| 12 | [Weiß](https://www.youtube.com/channel/UCNaHMNS61Q1f1nIRDS0429A) | `@lalalost8e` | Independent |  Hiatus (>180 วัน) | `hiatus` |
| 13 | [Hatsu ch〖DPX〗](https://www.youtube.com/channel/UCOFHRsSrDPOcdiz3Crc2ZBw) | `@hatsuxch` | DPX |  Active | `active` |
| 14 | [Naoki Yuuto Ch.](https://www.youtube.com/channel/UC82qGW5XAba3LYqMEmiVBgg) | `@naokiyuuto` | Independent |  Hiatus (>180 วัน) | `hiatus` |
| 15 | [CHALONETTA | VArtisit](https://www.youtube.com/channel/UCDmay2oK3RLbl8ooxYv-wJg) | `@chalonettavamp` | Independent |  Active | `active` |
| 16 | [Rui Kazu 《 EXia 》](https://www.youtube.com/channel/UCEL3qsIRdudjSuFHMHUxi0Q) | `@ruikazu_exia` | EXia |  Active | `active` |
| 17 | [Yokina Saori](https://www.youtube.com/channel/UCyv2oEiAXQp9xLlBr1Tn6Vg) | `@yokinasaori` | Independent |  Active | `active` |
| 18 | [LUM1N S.](https://www.youtube.com/channel/UCHhEdxjXqC8sbAj7a-PVFlg) | `@lum1ns` | Independent |  Active | `active` |
| 19 | [ZAIN Ch.](https://www.youtube.com/channel/UCpD_Ds-YEOOhPobh2xOGBHA) | `@zainvtuber` | Independent |  Active | `active` |
| 20 | [Jozetté Wrasset Ch. | OAL](https://www.youtube.com/channel/UCpfWYM5nNmWfroMIXBk3Gug) | `@jozette_oal` | OAL |  Active | `active` |
| 21 | [EikiShiro ch.](https://www.youtube.com/channel/UCqUHXBufAIuF9KI-OoMFUQw) | `@eikishiro` | Independent |  Active | `active` |
| 22 | [Zuruya Ch.](https://www.youtube.com/channel/UCpbHtJERmEP-GZJeSpziqCQ) | `@zuruya-zip` | Independent |  Active | `active` |
| 23 | [Z](https://www.youtube.com/channel/UCT0u795YFp9O_k9cL5d0RZg) | `@user-wj8iv9im1u` | Independent |  Hiatus (>180 วัน) | `hiatus` |
| 24 | [shiorichan](https://www.youtube.com/channel/UCRjdIz5ngcJVDZ-bjs2mEzg) | `@shiorichanvt` | Independent |  Active | `active` |
| 25 | [Laychlype「ALF」](https://www.youtube.com/channel/UCSpIYbnsnaXgRpIpipxJRcw) | `@laychlype_alf` | ALF |  Active | `active` |
| 26 | [Minami Lollipopza Ch. ʕ •ᴥ•ʔ](https://www.youtube.com/channel/UCKuzX7wNaRVXEI9a81xeNfA) | `@minamilollipopzach` | Independent |  Active | `active` |
| 27 | [Goozilla Ily Ch. [Autumnia]](https://www.youtube.com/channel/UCKg9vWWT_2yK3FFNNnnhhLw) | `@goozillaily` | Autumnia |  Hiatus (>180 วัน) | `hiatus` |
| 28 | [Vulgtmnahog](https://www.youtube.com/channel/UCLT-U861QLvJmrlP7K6kv2w) | `@vulgt_bgp` | Independent |  Active | `active` |
| 29 | [Rewarin Ch.](https://www.youtube.com/channel/UC4Ty5GzSA5YjeXN-DqPIWfA) | `@rewarinrei` | Independent |  Active | `active` |
| 30 | [Vermillion Ch. Flora Project](https://www.youtube.com/channel/UCc6hwdN1yu2QT9o4yIHUPnQ) | `@vermillvt` | Flora Project |  ไม่มีคลิปสาธารณะ | `unknown` |
| 31 | [Haine『Paralist』](https://www.youtube.com/channel/UCmLd6QDRBcD9TfFrThJucng) | `@haineinwza` | Paralist |  Hiatus (>180 วัน) | `hiatus` |
| 32 | [東雲こね / Shinonome Kone ⌜VZ⌟](https://www.youtube.com/channel/UCkjQ55wHjS7cQ9Xol9qW7Ow) | `@shinonomekone` | VZ |  Active | `active` |
| 33 | [Mysterica X. Ch. | RPG](https://www.youtube.com/channel/UCVogMqMZimg5YbPE48oPrlg) | `@mystyrelife` | RPG |  Graduated (Hiatus) | `graduated` |
| 34 | [^-Maru Chan-^](https://www.youtube.com/channel/UCWp6-EK_2seNDN_HN3mo9gA) | `@marukomaruchan` | Independent |  Active | `active` |
| 35 | [AzuruVT](https://www.youtube.com/channel/UCD2BJUqKTEPOkxdTyxfvCuQ) | `@azuruvt` | Independent |  Active | `active` |
| 36 | [Hajikeru Haruno Ch](https://www.youtube.com/channel/UCCwDLJmhL5pYyXzN7coVwTw) | `@hajikeruharuno` | Independent |  Active | `active` |
| 37 | [Wynn Carwin Ch. | OAL](https://www.youtube.com/channel/UCZq9-nxDs5XXEtAPzAuBnhQ) | `@wynn_oal` | OAL |  Active | `active` |
| 38 | [Fusui Ch.](https://www.youtube.com/channel/UCZsXl4d82Yx76SeGNtWGjlQ) | `@fusuich` | Independent |  Hiatus (>180 วัน) | `hiatus` |
| 39 | [Qmulaz](https://www.youtube.com/channel/UCtk8lcwk_Gx9egTljfiCMYw) | `@qmulaz_vt` | Independent |  Active | `active` |
| 40 | [Folpuzx Ch.](https://www.youtube.com/channel/UCwSohSYD00uLV-kq_UFJb4g) | `@folpuzx` | Independent |  Active | `active` |
| 41 | [Zayn Ch【 HZ 】](https://www.youtube.com/channel/UCvYUivIS4WcgfACH3xBJ0DQ) | `@zayngloucesterchannel` | HZ |  Active | `active` |
| 42 | [Vivera Carmine](https://www.youtube.com/channel/UCPh5ZGdw9LkBXxpCAdSaCrw) | `@vivera_eylz` | EYLZ |  Active | `active` |
| 43 | [Avele Ch. [Pandora]](https://www.youtube.com/channel/UCPW4hvhGciPdGqcsM1OCZ-Q) | `@avele_pdr` | Pandora |  ไม่มีคลิปสาธารณะ | `unknown` |
| 44 | [Miledy Z.Devlin ch.](https://www.youtube.com/channel/UCAid1uC5pxxvPasgFTJZEAw) | `@miledyz_ch` | Independent |  Active | `active` |
| 45 | [Xen Ch. 【Ti19t】](https://www.youtube.com/channel/UChd2cJe7HuTYbZGkOO-QKwg) | `@xen_desu` | Ti19t |  Active | `active` |
| 46 | [AmiLLy](https://www.youtube.com/channel/UCiG3hDSyLNx-tani2z03_Zg) | `@amillyarchive` | Independent |  Active | `active` |
| 47 | [Melantha Vtopia](https://www.youtube.com/channel/UChW_l65xozteVRme3mFE0Jg) | `@melanthavtopia705` | Vtopia |  Hiatus (>180 วัน) | `hiatus` |
| 48 | [Shimonz](https://www.youtube.com/channel/UCt8vlwt6qi6P1mz5uuStJCA) | `@shimonnnnn` | Independent |  Retired / Fandom (นกฮูกไดมอนด์) | `graduated` |
| 49 | [シノライラ - Shino Laila【WACTOR】](https://www.youtube.com/channel/UCFSkExeBcqI4nb_ArHeByNw) | `@-shinolailawactor5871` | WACTOR |  Fandom Wiki (Thai VA) | `graduated` |

### 4.2 รายชื่อช่องต่างชาติที่ถูกคัดออกถาวร (6 ช่อง)

บันทึกแยกไว้ใน `data/excluded_channels.csv` เพื่อป้องกันการดึงข้อมูลผิดพลาดในอนาคต:

| ลำดับ | ช่อง | Handle | ประเทศ/สังกัด | เหตุผลการคัดออก |
|---|---|---|---|---|
| 1 | [こはならむ- Kohana Lam -](https://www.youtube.com/channel/UCW0p7VdWVO0bn0_FELopJpQ) | `@kohanalam` | JP / Avex | Non-Thai: Japanese singer/utaite signed under Avex. Appeared via cross-referencing on Fandom wiki. |
| 2 | [Klara Charmwood 【NIJISANJI EN】](https://www.youtube.com/channel/UCQYwIUCLqFoin7lHKmePjJw) | `@klaracharmwood` | Global (EN) / NIJISANJI EN | Non-Thai: International VTuber affiliated with NIJISANJI EN (Denauth unit). |
| 3 | [Koseki Bijou Ch. hololive-EN](https://www.youtube.com/channel/UC9p_lqQ0FEDz327Vgf5JwqA) | `@kosekibijou` | Global (EN) / hololive English | Non-Thai: International VTuber affiliated with hololive English (-Advent-). |
| 4 | [Nakaru Rikka](https://www.youtube.com/channel/UCQxYe05rfMOW_gesVywQlYA) | `@nakarurikka` | JP / Independent | Non-Thai: Japanese voice actress / singer. Appeared via cross-category link on Fandom wiki. |
| 5 | [Lui ch. 鷹嶺ルイ - holoX -](https://www.youtube.com/channel/UCs9_O1tRPMQTHQ-N_L6FU2g) | `@takanelui` | JP / hololive Japan | Non-Thai: Japanese VTuber affiliated with hololive Japan (Secret Society holoX 6th Gen). |
| 6 | [Yugo Asuma 【NIJISANJI EN】](https://www.youtube.com/channel/UCSc_KzY_9WYAx9LghggjVRA) | `@yugoasuma` | Global (EN) / NIJISANJI EN | Non-Thai: Former international VTuber affiliated with NIJISANJI EN (Noctyx unit). |

---

## 5. Artifacts และไฟล์ผลลัพธ์ที่จัดเก็บ

1. **`data/thai_vtuber_registry.csv`**: ทะเบียนหลัก Thai VTuber จำนวน **1,363 ช่อง** (UTF-8, 20 คอลัมน์)
2. **`data/thai_vtuber_registry.json`**: ทะเบียนหลักรูปแบบ JSON รองรับ API และ Web App
3. **`data/excluded_channels.csv`**: รายชื่อช่องต่างชาติที่ถูกคัดออกถาวรจำนวน **6 ช่อง**
4. **`data/unconfirmed_candidates.csv`**: ช่องที่ค้างในคิวตรวจสอบคงเหลือ **0 ช่อง**
5. **`data/registry_vtubers.csv`**: Control Plane CSV สำหรับระบบจัดตารางเก็บข้อมูลและ DuckDB

---
*รายงานจัดทำโดยระบบตรวจสอบ Thai VTuber Audience Network (Phase 1 Registry Builder)*
