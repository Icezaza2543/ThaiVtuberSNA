# Reports

Read [current/README.md](current/README.md) for current counts. All current CSV and JSON reports live in `current/`; dated publications and superseded handoffs live in `archive/`.

Refresh all current reports offline with:

```sh
python scripts/maintenance/refresh_reports.py --as-of YYYY-MM-DD
```

The refresh never changes `data/registry.json` and does not fetch creator profiles. Current platform presence and dated activity have different denominators; see the metadata in each report.
