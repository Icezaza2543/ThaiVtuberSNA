import duckdb

from storage.local_archive_store import LocalArchiveStore


def test_reads_archived_tab_with_sheet_headers(tmp_path):
    db = tmp_path / "a.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE _archive_meta (tab VARCHAR, rows INTEGER, sha256 VARCHAR, archived_at VARCHAR)")
    con.execute('CREATE TABLE "PRIVATE_DATA_ARCHIVE" (source_path VARCHAR, source_table VARCHAR, '
                'row_number VARCHAR, record_json VARCHAR)')
    con.execute("""INSERT INTO "PRIVATE_DATA_ARCHIVE" VALUES ('p', 'parquet', '1', '{}'), ('q', 'x', '2', NULL)""")
    con.execute("INSERT INTO _archive_meta VALUES ('PRIVATE_DATA_ARCHIVE', 2, 'h', 't')")
    con.close()
    store = LocalArchiveStore(db)
    assert store.has_tab("PRIVATE_DATA_ARCHIVE") and not store.has_tab("VIEWER_INDEX")
    rows = list(store.read_records("PRIVATE_DATA_ARCHIVE",
                                   ["source_path", "source_table", "row_number", "record_json"], batch_size=1))
    assert rows == [{"source_path": "p", "source_table": "parquet", "row_number": "1", "record_json": "{}"},
                    {"source_path": "q", "source_table": "x", "row_number": "2", "record_json": ""}]
