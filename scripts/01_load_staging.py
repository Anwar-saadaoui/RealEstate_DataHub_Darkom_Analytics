"""
Step 1 — Load raw CSV into staging.darkom_annonces
"""
import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from datetime import datetime

# ── Connection ────────────────────────────────────────────────
DB = dict(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    user=os.getenv("POSTGRES_USER", "darkom_user"),
    password=os.getenv("POSTGRES_PASSWORD", "darkom_pass123"),
    dbname=os.getenv("POSTGRES_DB", "darkom_dwh"),
)
ENGINE_URL = (
    f"postgresql+psycopg2://{DB['user']}:{DB['password']}"
    f"@{DB['host']}:{DB['port']}/{DB['dbname']}"
)
CSV_PATH = "/app/data/darkom_annonces.csv"

def log(engine, step, status, message, rows=0):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO public.pipeline_logs(step,status,message,rows_count) "
                "VALUES (:step,:status,:message,:rows)"
            ),
            {"step": step, "status": status, "message": message, "rows": rows},
        )
    print(f"[{datetime.now():%H:%M:%S}] [{status}] {step} — {message}")


def main():
    engine = create_engine(ENGINE_URL)

    # ── Read CSV ──────────────────────────────────────────────
    try:
        df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8")
        log(engine, "01_load_staging", "INFO", f"CSV read: {len(df)} rows, {len(df.columns)} cols")
    except Exception as e:
        log(engine, "01_load_staging", "ERROR", f"CSV read failed: {e}")
        raise

    # ── Truncate staging ─────────────────────────────────────
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.darkom_annonces RESTART IDENTITY"))
    log(engine, "01_load_staging", "INFO", "Staging table truncated")

    # ── Load ─────────────────────────────────────────────────
    try:
        df.to_sql(
            "darkom_annonces",
            engine,
            schema="staging",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500,
        )
        log(engine, "01_load_staging", "SUCCESS", f"Loaded {len(df)} rows into staging", len(df))
    except Exception as e:
        log(engine, "01_load_staging", "ERROR", f"Load failed: {e}")
        raise

    # ── Integrity check ───────────────────────────────────────
    with engine.connect() as conn:
        db_count = conn.execute(
            text("SELECT COUNT(*) FROM staging.darkom_annonces")
        ).scalar()

    if db_count == len(df):
        log(engine, "01_load_staging", "SUCCESS", f"Integrity OK — {db_count} rows in DB", db_count)
    else:
        log(engine, "01_load_staging", "WARNING",
            f"Row mismatch: CSV={len(df)}, DB={db_count}")


if __name__ == "__main__":
    main()