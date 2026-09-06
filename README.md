# Thai VTuber Audience Network (SNA)

ระบบวิเคราะห์ความสัมพันธ์ของฐานผู้ชมในวงการ VTuber ไทยด้วย Social Network Analysis (SNA) โดยออกแบบให้เป็นระบบ **Lightweight, Zero Cloud Cost, และ Privacy by Design** ไม่บันทึกข้อความแชตใด ๆ ทั้งสิ้น และเก็บเฉพาะ Viewer Presence ที่จำเป็นต่อการคำนวณ Audience Overlap

---

## สถาปัตยกรรมหลัก (System Architecture)

```
Thai VTuber Directories / Seeds
          ↓
     Discovery (Deduplicate by Channel ID)
          ↓
    First Filter (Rule-based: Thai & VTuber Signals)
          ↓
  Google Sheets / Local CSV Registry (Control Plane)
          ↓
Subscriber Priority & Stream Detection
          ↓
   Worker Scheduler (Baseline Priority Queue & PSO)
          ↓
  Collector Workers (Privacy: HMAC-SHA256 Hashing)
          ↓
   Partitioned Apache Parquet Storage (Snappy)
          ↓
   DuckDB OLAP Engine (High-speed Overlap Matrix)
          ↓
Social Network Analysis (NetworkX: Louvain & Bridges)
          ↓
Interactive Web Visualizer / Google Sheets / Gephi
```

---

## จุดเด่นของระบบ (Core Features)

1. **Privacy by Design (100% ปลอดภัยต่อผู้ชม)**:
   - ไม่เก็บข้อความแชต (Chat text) หรือคอมเมนต์ใด ๆ ทั้งสิ้น
   - ไม่ใช้ Display Name เป็น Identity
   - ใช้ YouTube Channel ID แปลงเป็น `HMAC-SHA256(salt, channel_id)` ทันทีตั้งแต่จุดรับเข้า (One-way pseudonymization)
   - ข้อมูลภายนอกแสดงเฉพาะระดับ VTuber และภาพรวมเครือข่าย

2. **Zero Cloud Database Cost**:
   - ไม่ต้องใช้ PostgreSQL, MongoDB, Redis, หรือ Kafka
   - **Registry & Control Plane**: ใช้ Google Sheets (รองรับ Local CSV/JSON อัตโนมัติเมื่อออฟไลน์)
   - **Event Storage**: บันทึกลง Apache Parquet แบ่ง Partition ตาม `data/events/YYYY/MM/video_id.parquet` บีบอัด Snappy ประหยัดเนื้อที่ดิสก์
   - **Query Engine**: ใช้ Embedded DuckDB คำนวณ Intersect ของ Viewer ข้ามช่องได้ในระดับมิลลิวินาที

3. **Smart Scheduler & Resource Allocation (PSO)**:
   - จัดการ Worker ที่มีจำกัดเมื่อมีช่อง Live พร้อมกันหลายช่อง
   - รองรับทั้ง Baseline Greedy Priority Queue และ **Particle Swarm Optimization (PSO)**
   - ปรับแต่งค่าน้ำหนักได้ตามสูตร:
     $$\text{Fitness} = 0.60 \times \text{Sub Priority} + 0.20 \times \text{Data Gap} + 0.10 \times \text{Live Urgency} + 0.10 \times \text{Recency}$$

4. **SNA & Overlap Analytics**:
   - **Shared Viewers**: $|A \cap B|$
   - **Jaccard Similarity**: $\frac{|A \cap B|}{|A \cup B|}$
   - **Simpson Overlap Coefficient**: $\frac{|A \cap B|}{\min(|A|, |B|)}$ (สำคัญมากสำหรับช่องอินดี้ขนาดเล็ก)
   - **Community Detection**: Louvain Algorithm แบ่งกลุ่มคอมมูนิตี้
   - **Bridge Detection**: Betweenness Centrality ค้นหาช่องที่ทำหน้าที่เชื่อมระหว่างกลุ่มผู้ชม

5. **Interactive Network Visualizer Dashboard**:
   - เว็บแอปพลิเคชันแบบ Standalone (HTML5 Canvas + Vanilla CSS) สไตล์ Cyberpunk Dark Theme
   - ระบบฟิสิกส์จำลองแรงดึงดูด (Force-directed graph)
   - Filter ค่าย (Agency), Subscriber Tier, Overlap Threshold
   - โหมด Spotlight Bridge VTubers พร้อม Flyout Inspector แสดงสถิติและคู่ทับซ้อน

---

## การติดตั้งและเริ่มต้นใช้งาน (Getting Started)

### 1. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 2. รันการทดสอบ Unit Tests
```bash
python -m pytest tests/test_sna_pipeline.py -v
```

### 3. รัน Pipeline แบบ End-to-End Demo
```bash
python main.py --demo
```
คำสั่งนี้จะทำการ:
1. โหลด Seed VTubers และ Deduplicate ด้วย Channel ID
2. รัน First Filter คัดกรองภาษาไทยและสัญญาณ VTuber
3. สร้าง Collection Jobs และรัน PSO Scheduler เพื่อจัดสรร Worker
4. จำลอง Collector และบันทึก Events ลง Parquet
5. รัน DuckDB สรุป Shared Viewers และคำนวณ Jaccard / Overlap Coefficient
6. คำนวณ SNA (Betweenness, PageRank, Louvain Communities)
7. ส่งออกผลลัพธ์เป็น `data/analytics/network_graph.json` และ `network_graph.gexf` สำหรับ Gephi

---

## คำสั่ง CLI แต่ละขั้นตอน

```bash
# รันเฉพาะขั้นตอน Discovery
python main.py --discovery

# รัน First Filter และอัปเดต Registry
python main.py --filter

# รัน Scheduler และ Collector
python main.py --collect --workers 4

# รัน DuckDB OLAP และ SNA Analysis
python main.py --analyze
```

---

## การเปิด Interactive Web Dashboard

เปิดไฟล์ `web/index.html` บนเว็บเบราว์เซอร์ (Chrome, Edge, Firefox, Safari) ได้โดยตรง:
- รองรับการเปิดแบบ Local `file:///.../web/index.html` (มี Embedded Dataset สำรองอัตโนมัติ)
- หรือรัน Local Web Server:
  ```bash
  python -m http.server 8000 --directory web
  ```
  แล้วเปิด `http://localhost:8000`

---

## โครงสร้างโปรเจกต์ (Directory Structure)

```text
ThaiVtuberSNA/
├── config/
│   ├── settings.py           # การตั้งค่าระบบ, พาธ, ค่าน้ำหนัก Scheduler
│   └── seeds_vtuber.json     # รายชื่อเริ่มต้นของ VTuber ไทย
├── core/
│   ├── hasher.py             # HMAC-SHA256 Privacy Pseudonymizer
│   ├── filter_engine.py      # Rule-based First Filter
│   ├── priority.py           # Subscriber Tiers (S, A, B, C, D) & Priority Score
│   ├── registry.py           # Google Sheets & Local CSV/JSON Control Plane
│   └── scheduler.py          # Priority Queue & PSO Scheduler
├── collector/
│   ├── base_collector.py     # Base Collector Interface
│   ├── discovery_adapter.py  # Ingestion & Deduplication จาก Directory
│   ├── mock_collector.py     # Mock Generator สำหรับทดสอบ
│   └── youtube_collector.py  # YouTube Data API v3 Adapter
├── storage/
│   ├── parquet_manager.py    # Partitioned Parquet Writer
│   └── duckdb_engine.py      # DuckDB OLAP Query & Overlap Matrix
├── analytics/
│   ├── overlap_metrics.py    # ฟังก์ชันคำนวณ Jaccard, Simpson Overlap, Cosine
│   ├── network_graph.py      # NetworkX SNA, Louvain & Bridge Detection
│   └── exporter.py           # Export JSON (Web) & GEXF (Gephi)
├── web/
│   ├── index.html            # Web Dashboard
│   ├── styles.css            # Dark Holographic CSS
│   ├── app.js                # Canvas Force Simulation & Interactivity
│   └── data.json             # Network Data สำหรับ Web UI
├── tests/
│   └── test_sna_pipeline.py  # Unit Tests (Pytest)
├── main.py                   # Master CLI Runner
├── requirements.txt
└── README.md
```

---

## การตั้งค่า Google Sheets Control Plane (ตัวเลือกเสริม)

หากต้องการเชื่อมต่อกับ Google Sheets ในโหมด Production:
1. สร้าง Google Spreadsheet และตั้งชื่อ Sheet ย่อย 3 หน้า:
   - `VTUBERS`
   - `SYSTEM`
   - `NETWORK_RESULT`
2. สร้าง Google Service Account และดาวน์โหลดคีย์ JSON มาไว้ที่ `credentials.json`
3. กำหนดค่า Environment Variables:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="credentials.json"
   export VTUBER_SPREADSHEET_ID="YOUR_SPREADSHEET_ID_HERE"
   ```
*หากไม่ได้กำหนดค่า ระบบจะทำงานบน Local CSV/JSON อัตโนมัติโดยไม่มีข้อผิดพลาด*
