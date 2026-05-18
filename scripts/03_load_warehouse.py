"""
Step 3 — Load clean data into star schema (bi_schema)
"""
import os
import pandas as pd
import numpy as np
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

NOM_MOIS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}


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


def load_dim_temps(df, engine):
    dates = df["date_publication"].dropna().unique()
    records = []
    for d in dates:
        dt = pd.Timestamp(d)
        records.append({
            "date_full": dt.date(),
            "annee": int(dt.year),
            "trimestre": int(dt.quarter),
            "mois": int(dt.month),
            "nom_mois": NOM_MOIS[dt.month],
            "semaine": int(dt.isocalendar()[1]),
        })
    dim = pd.DataFrame(records).drop_duplicates(subset=["date_full"])

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE bi_schema.dim_temps RESTART IDENTITY CASCADE"))

    dim.to_sql("dim_temps", engine, schema="bi_schema",
               if_exists="append", index=False, method="multi", chunksize=500)
    return pd.read_sql("SELECT temps_id, date_full FROM bi_schema.dim_temps", engine)


def load_dim_localisation(df, engine):
    dim = (
        df[["ville", "quartier"]]
        .drop_duplicates()
        .dropna(subset=["ville"])
        .reset_index(drop=True)
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE bi_schema.dim_localisation RESTART IDENTITY CASCADE"))

    dim.to_sql("dim_localisation", engine, schema="bi_schema",
               if_exists="append", index=False, method="multi", chunksize=500)
    return pd.read_sql("SELECT localisation_id, ville, quartier FROM bi_schema.dim_localisation", engine)


def load_dim_type_bien(df, engine):
    dim = (
        df[["type_bien", "transaction"]]
        .drop_duplicates()
        .dropna()
        .reset_index(drop=True)
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE bi_schema.dim_type_bien RESTART IDENTITY CASCADE"))

    dim.to_sql("dim_type_bien", engine, schema="bi_schema",
               if_exists="append", index=False, method="multi", chunksize=500)
    return pd.read_sql("SELECT type_bien_id, type_bien, transaction FROM bi_schema.dim_type_bien", engine)


def load_dim_caracteristiques(df, engine):
    dim = (
        df[["nb_chambres", "nb_salles_bain", "etage", "annee_construction", "age_bien", "categorie_surface"]]
        .drop_duplicates(subset=["nb_chambres", "nb_salles_bain", "etage", "annee_construction"])
        .reset_index(drop=True)
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE bi_schema.dim_caracteristiques RESTART IDENTITY CASCADE"))

    dim.to_sql("dim_caracteristiques", engine, schema="bi_schema",
               if_exists="append", index=False, method="multi", chunksize=500)
    return pd.read_sql(
        "SELECT caract_id, nb_chambres, nb_salles_bain, etage, annee_construction "
        "FROM bi_schema.dim_caracteristiques",
        engine,
    )


def main():
    engine = create_engine(ENGINE_URL)

    df = pd.read_sql("SELECT * FROM clean.darkom_annonces", engine)
    log(engine, "03_load_warehouse", "INFO", f"Loaded {len(df)} rows from clean layer")

    # Convert date
    df["date_publication"] = pd.to_datetime(df["date_publication"])

    # ── Load dimensions ───────────────────────────────────────
    dim_temps = load_dim_temps(df, engine)
    log(engine, "03_load_warehouse", "INFO", f"dim_temps: {len(dim_temps)} rows")

    dim_loc = load_dim_localisation(df, engine)
    log(engine, "03_load_warehouse", "INFO", f"dim_localisation: {len(dim_loc)} rows")

    dim_type = load_dim_type_bien(df, engine)
    log(engine, "03_load_warehouse", "INFO", f"dim_type_bien: {len(dim_type)} rows")

    dim_caract = load_dim_caracteristiques(df, engine)
    log(engine, "03_load_warehouse", "INFO", f"dim_caracteristiques: {len(dim_caract)} rows")

    # ── Build fact table ──────────────────────────────────────
    df["date_only"] = df["date_publication"].dt.date.astype(str)
    dim_temps["date_full"] = dim_temps["date_full"].astype(str)

    fact = df.copy()

    # Join temps_id
    fact = fact.merge(
        dim_temps.rename(columns={"date_full": "date_only"}),
        on="date_only", how="left"
    )

    # Join localisation_id
    fact = fact.merge(
        dim_loc, on=["ville", "quartier"], how="left"
    )

    # Join type_bien_id
    fact = fact.merge(
        dim_type, on=["type_bien", "transaction"], how="left"
    )

    # Join caract_id
    fact = fact.merge(
        dim_caract,
        on=["nb_chambres", "nb_salles_bain", "etage", "annee_construction"],
        how="left",
    )

    fact_cols = [
        "annonce_id", "temps_id", "localisation_id", "type_bien_id",
        "caract_id", "prix", "surface", "prix_m2", "categorie_prix", "titre",
    ]
    fact_final = fact[fact_cols].copy()

    # ── Load facts ────────────────────────────────────────────
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE bi_schema.fact_annonces RESTART IDENTITY"))

    fact_final.to_sql(
        "fact_annonces", engine, schema="bi_schema",
        if_exists="append", index=False, method="multi", chunksize=500,
    )
    log(engine, "03_load_warehouse", "SUCCESS",
        f"Loaded {len(fact_final)} rows into fact_annonces", len(fact_final))

    # ── Clean staging after success ───────────────────────────
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.darkom_annonces"))
    log(engine, "03_load_warehouse", "INFO", "Staging truncated after successful load")


if __name__ == "__main__":
    main()