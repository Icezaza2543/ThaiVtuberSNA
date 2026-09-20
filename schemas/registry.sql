PRAGMA foreign_keys = ON;

CREATE TABLE evidence (
    id TEXT PRIMARY KEY NOT NULL,
    url TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('legacy_import','official_profile','self_statement','agency_statement','platform_observation','secondary_source')),
    observed_at TEXT NOT NULL,
    published_on TEXT,
    sha256 TEXT,
    summary TEXT NOT NULL
);
CREATE TABLE personas (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('unknown','png','live2d','3d','mixed')),
    roles TEXT NOT NULL,
    thai_relation TEXT NOT NULL CHECK (thai_relation IN ('unknown','thai_language','self_declared_thai','thai_community','thai_agency','multiple')),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    reviewer TEXT,
    reviewed_at TEXT
);
CREATE TABLE accounts (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('youtube','twitch','tiktok','facebook','instagram','x','kick','ganknow','bilibili','niconico','carrd','linktree','litlink','kofi','patreon','vgen','website')),
    platform_id TEXT NOT NULL,
    id_namespace TEXT NOT NULL,
    handle TEXT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    first_discovered_at TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    UNIQUE (platform, id_namespace, platform_id)
);
CREATE TABLE account_links (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    persona_id TEXT NOT NULL REFERENCES personas(id),
    valid_from TEXT,
    valid_to TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT,
    CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to)
);
CREATE TABLE lifecycle_events (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    event_type TEXT NOT NULL CHECK (event_type IN ('debut','redebut','rebrand','model_reveal','hiatus','graduation','return','channel_migration')),
    event_date TEXT,
    date_precision TEXT NOT NULL CHECK (date_precision IN ('day','month','year','unknown')),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT,
    note TEXT NOT NULL
);
CREATE TABLE activity_observations (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    account_id TEXT NOT NULL REFERENCES accounts(id),
    activity_date TEXT NOT NULL,
    activity_type TEXT NOT NULL CHECK (activity_type IN ('live','post','video')),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT
);
CREATE TABLE affiliations (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    organization TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT,
    CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to)
);
CREATE TABLE continuity_links (
    id TEXT PRIMARY KEY NOT NULL,
    from_persona_id TEXT NOT NULL REFERENCES personas(id),
    to_persona_id TEXT NOT NULL REFERENCES personas(id),
    relation TEXT NOT NULL CHECK (relation = 'publicly_disclosed_continuity'),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT,
    CHECK (from_persona_id <> to_persona_id)
);
CREATE TABLE discovery_runs (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('youtube','twitch','tiktok','facebook','instagram','x','kick','ganknow','bilibili','niconico','carrd','linktree','litlink','kofi','patreon','vgen','website')),
    method TEXT NOT NULL CHECK (method IN ('legacy_import','manual_search','official_crosslink','self_submission','twitch_helix','playwright_search','crosslink_crawl')),
    query TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    stop_reason TEXT NOT NULL CHECK (stop_reason IN ('import_complete','manual_batch','page_limit','end_of_results','http_error','completed','partial','login_required','captcha','rate_limited','selector_changed','timeout','blocked')),
    pages INTEGER NOT NULL CHECK (pages >= 0),
    records_seen INTEGER NOT NULL CHECK (records_seen >= 0)
);
CREATE TABLE candidates (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('youtube','twitch','tiktok','facebook','instagram','x','kick','ganknow','bilibili','niconico','carrd','linktree','litlink','kofi','patreon','vgen','website')),
    platform_id TEXT,
    id_namespace TEXT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    review_status TEXT NOT NULL CHECK (review_status IN ('needs_evidence','verified','rejected')),
    account_id TEXT REFERENCES accounts(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    reviewer TEXT,
    reviewed_at TEXT
);
CREATE TABLE discovery_hits (
    id TEXT PRIMARY KEY NOT NULL,
    run_id TEXT NOT NULL REFERENCES discovery_runs(id),
    account_id TEXT REFERENCES accounts(id),
    candidate_id TEXT REFERENCES candidates(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    CHECK ((account_id IS NULL) <> (candidate_id IS NULL)),
    UNIQUE (run_id, account_id),
    UNIQUE (run_id, candidate_id)
);
CREATE TABLE legacy_claims (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL UNIQUE REFERENCES accounts(id),
    source_status TEXT NOT NULL,
    source_activity TEXT NOT NULL,
    source_agency TEXT NOT NULL,
    source_names TEXT NOT NULL,
    source_checked_at TEXT NOT NULL,
    last_video_published_at TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id)
);
CREATE TABLE review_queue (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    reason TEXT NOT NULL CHECK (reason IN ('legacy_scope_review','legacy_identity_collision','lifecycle_conflict')),
    status TEXT NOT NULL CHECK (status IN ('open','resolved','dismissed')),
    note TEXT NOT NULL
);
