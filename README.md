# ThaiVtuberSNA

> Minimalist audience network telemetry & relational graph modeling.

## Overview

An experimental, privacy-preserving telemetry pipeline for longitudinal audience graph analysis and community structure mapping.

Designed for low-resource environments with local zero-cloud storage and deterministic one-way identity pseudonymization.

## Telemetry Pipeline

```
[ Ingestion & Discovery ]
          │
          ▼
[ Ephemeral Processing & HMAC Pseudonymization ]
          │
          ▼
[ Partitioned Columnar Storage (Parquet) ]
          │
          ▼
[ In-Process OLAP & Graph Analytics ]
```

- **Identity**: In-memory HMAC-SHA256 pseudonymization (zero message text or personal data persistence).
- **Storage**: Snappy-compressed columnar Parquet files.
- **Analytics**: Embedded OLAP engine (DuckDB) and graph centrality algorithms (NetworkX).

## Setup

```bash
pip install -r requirements.txt
python -m core.hasher --verify-key
```

## Usage

```bash
# Run pipeline
python main.py

# Run verification suite
python -m pytest -v
```

## Privacy & Compliance

- Zero message payload, display name, avatar, or comment body persistence.
- Strict one-way irreversible cryptographic hashing at ingestion boundaries.
- Continuous identity continuity validation across all analytical snapshots.

## License

Internal Research / All Rights Reserved.
