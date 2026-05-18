"""
Step 4 — Validate data warehouse integrity
"""
import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

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


def check(engine, label, query, expected_zero=True):
    with engine.connect() as conn:
        result = conn.execute(text(query)).scalar()
    status = "OK" if (result == 0) == expected_zero else "WARN"
    print(f"  [{status}] {label}: {result}")
    return status == "OK", result


def main():
    engine = create_engine(ENGINE_URL)
    errors = 0

    print("\n=== ROW COUNTS ===")
    for schema_table, label in [
        ("clean.darkom_annonces",         "Clean layer"),
        ("bi_schema.fact_annonces",       "Fact annonces"),
        ("bi_schema.dim_temps",           "Dim temps"),
        ("bi_schema.dim_localisation",    "Dim localisation"),
        ("bi_schema.dim_type_bien",       "Dim type bien"),
        ("bi_schema.dim_caracteristiques","Dim caractéristiques"),
    ]:
        ok, count = check(engine, label,
                          f"SELECT COUNT(*) FROM {schema_table}",
                          expected_zero=False)
        if not ok:
            errors += 1

    print("\n=== ORPHAN CHECKS ===")
    orphan_checks = [
        ("Orphans: fact → dim_temps",
         "SELECT COUNT(*) FROM bi_schema.fact_annonces f "
         "LEFT JOIN bi_schema.dim_temps t ON f.temps_id=t.temps_id WHERE t.temps_id IS NULL"),
        ("Orphans: fact → dim_localisation",
         "SELECT COUNT(*) FROM bi_schema.fact_annonces f "
         "LEFT JOIN bi_schema.dim_localisation l ON f.localisation_id=l.localisation_id WHERE l.localisation_id IS NULL"),
        ("Orphans: fact → dim_type_bien",
         "SELECT COUNT(*) FROM bi_schema.fact_annonces f "
         "LEFT JOIN bi_schema.dim_type_bien t ON f.type_bien_id=t.type_bien_id WHERE t.type_bien_id IS NULL"),
    ]
    for label, query in orphan_checks:
        ok, count = check(engine, label, query, expected_zero=True)
        if not ok:
            errors += 1

    print("\n=== NULL CHECKS (FACT) ===")
    null_checks = [
        ("Null prix",    "SELECT COUNT(*) FROM bi_schema.fact_annonces WHERE prix IS NULL"),
        ("Null surface", "SELECT COUNT(*) FROM bi_schema.fact_annonces WHERE surface IS NULL"),
        ("Null prix_m2", "SELECT COUNT(*) FROM bi_schema.fact_annonces WHERE prix_m2 IS NULL"),
    ]
    for label, query in null_checks:
        ok, count = check(engine, label, query, expected_zero=True)
        # NULLs in fact are warnings, not blockers

    print("\n=== PRICE CATEGORY DISTRIBUTION ===")
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT categorie_prix, COUNT(*) AS n, ROUND(AVG(prix),0) AS avg_prix "
            "FROM bi_schema.fact_annonces "
            "GROUP BY categorie_prix ORDER BY avg_prix"
        )).fetchall()
    for row in rows:
        print(f"  {row[0]}: {row[1]} annonces, avg={row[2]} MAD")

    print("\n=== PIPELINE LOGS ===")
    with engine.connect() as conn:
        logs = conn.execute(text(
            "SELECT step, status, message, rows_count, created_at "
            "FROM public.pipeline_logs ORDER BY created_at"
        )).fetchall()
    for row in logs:
        print(f"  [{row[4].strftime('%H:%M:%S')}] [{row[1]}] {row[0]}: {row[2]} ({row[3]} rows)")

    if errors:
        log(engine, "04_validate", "WARNING", f"Validation finished with {errors} issues")
        print(f"\n⚠  Validation finished with {errors} issue(s).")
    else:
        log(engine, "04_validate", "SUCCESS", "All validation checks passed")
        print("\n✓ All validation checks passed.")


if __name__ == "__main__":
    main()