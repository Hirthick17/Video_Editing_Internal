-- Hirthick's Vision Studio SQLite Schema DDL
-- Enforces relational integrity, UTC timestamps, and event auditability.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    short_id TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    state_version INTEGER NOT NULL DEFAULT 1,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    state_version INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_log (
    event_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    node_name TEXT,
    payload_json TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS approval_records (
    approval_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    feedback TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS node_retries (
    job_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (job_id, node_name),
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_event_log_job_id ON event_log(job_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_approvals_job_id ON approval_records(job_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_job_id ON checkpoints(job_id);

