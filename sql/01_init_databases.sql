-- Create schemas on the darkom_dwh database
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS bi_schema;

-- Pipeline logs table
CREATE TABLE IF NOT EXISTS public.pipeline_logs (
    log_id      SERIAL PRIMARY KEY,
    step        VARCHAR(100),
    status      VARCHAR(50),
    message     TEXT,
    rows_count  INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);