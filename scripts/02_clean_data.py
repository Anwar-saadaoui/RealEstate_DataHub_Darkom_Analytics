"""
Step 2 — Clean staging data and load into clean.darkom_annonces
"""
import os
import re
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

CURRENT_YEAR = datetime.now().year


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


# ── Standardisation maps ──────────────────────────────────────
VILLE_MAP = {
    "casa": "Casablanca", "casablanca": "Casablanca", "dar el beida": "Casablanca",
    "rabat": "Rabat", "salé": "Salé", "sale": "Salé",
    "marrakech": "Marrakech", "marrakesh": "Marrakech",
    "fes": "Fès", "fès": "Fès", "fez": "Fès",
    "tanger": "Tanger", "tangier": "Tanger", "tanja": "Tanger",
    "agadir": "Agadir",
    "meknes": "Meknès", "meknès": "Meknès",
    "oujda": "Oujda",
    "kenitra": "Kénitra", "kénitra": "Kénitra",
    "tetouan": "Tétouan", "tétouan": "Tétouan",
    "el jadida": "El Jadida",
    "safi": "Safi",
    "beni mellal": "Béni Mellal", "béni mellal": "Béni Mellal",
    "nador": "Nador",
    "settat": "Settat",
    "mohammedia": "Mohammedia",
    "khouribga": "Khouribga",
    "berrechid": "Berrechid",
    "temara": "Témara", "témara": "Témara",
}

TYPE_BIEN_MAP = {
    "appartement": "Appartement", "appart": "Appartement", "apt": "Appartement",
    "villa": "Villa", "maison": "Villa",
    "terrain": "Terrain", "lot": "Terrain",
    "bureau": "Bureau", "office": "Bureau", "local commercial": "Bureau",
    "riad": "Riad",
    "studio": "Studio",
    "ferme": "Ferme",
}

TRANSACTION_MAP = {
    "vente": "Vente", "vendre": "Vente", "sale": "Vente",
    "location": "Location", "louer": "Location", "rent": "Location", "loc": "Location",
}


def standardize_text(val, mapping):
    if pd.isna(val):
        return None
    key = str(val).strip().lower()
    return mapping.get(key, str(val).strip().title())


def remove_outliers_iqr(series, factor=3.0):
    """Return a boolean mask — True = keep."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    return series.between(lower, upper)


def categorize_prix(prix):
    if pd.isna(prix):
        return None
    if prix < 500_000:
        return "Économique"
    elif prix < 1_500_000:
        return "Moyen"
    elif prix < 4_000_000:
        return "Haut standing"
    else:
        return "Luxe"


def categorize_surface(surface):
    if pd.isna(surface):
        return None
    if surface < 80:
        return "Petit"
    elif surface <= 150:
        return "Moyen"
    else:
        return "Grand"


def main():
    engine = create_engine(ENGINE_URL)

    # ── Load staging ──────────────────────────────────────────
    df = pd.read_sql("SELECT * FROM staging.darkom_annonces", engine)
    log(engine, "02_clean_data", "INFO", f"Loaded {len(df)} rows from staging")

    initial_count = len(df)

    # ── 1. Remove duplicates ──────────────────────────────────
    df = df.drop_duplicates(subset=["annonce_id"])
    df = df.drop_duplicates(
        subset=["titre", "ville", "prix", "surface", "type_bien", "transaction"],
        keep="first",
    )
    log(engine, "02_clean_data", "INFO",
        f"After dedup: {len(df)} rows (removed {initial_count - len(df)})")

    # ── 2. Type conversions ───────────────────────────────────
    df["annonce_id"] = pd.to_numeric(df["annonce_id"], errors="coerce")
    df["prix"] = pd.to_numeric(df["prix"], errors="coerce")
    df["surface"] = pd.to_numeric(df["surface"], errors="coerce")
    df["nb_chambres"] = pd.to_numeric(df["nb_chambres"], errors="coerce")
    df["nb_salles_bain"] = pd.to_numeric(df["nb_salles_bain"], errors="coerce")
    df["etage"] = pd.to_numeric(df["etage"], errors="coerce")
    df["annee_construction"] = pd.to_numeric(df["annee_construction"], errors="coerce")
    df["date_publication"] = pd.to_datetime(df["date_publication"], errors="coerce", dayfirst=True)

    # ── 3. Handle missing values ──────────────────────────────
    # date_publication: drop rows with no date
    df = df.dropna(subset=["date_publication"])

    # quartier: fill unknown
    df["quartier"] = df["quartier"].fillna("Inconnu")

    # nb_chambres, nb_salles_bain: fill with median per type_bien
    for col in ["nb_chambres", "nb_salles_bain"]:
        medians = df.groupby("type_bien")[col].transform("median")
        df[col] = df[col].fillna(medians).fillna(df[col].median())

    # etage: fill 0 (ground floor) for NaN
    df["etage"] = df["etage"].fillna(0)

    # annee_construction: fill with median
    df["annee_construction"] = df["annee_construction"].fillna(
        df["annee_construction"].median()
    )

    # type_bien, transaction: drop if missing
    df = df.dropna(subset=["type_bien", "transaction"])

    # ── 4. Standardize text fields ────────────────────────────
    df["ville"] = df["ville"].apply(lambda x: standardize_text(x, VILLE_MAP))
    df["type_bien"] = df["type_bien"].apply(lambda x: standardize_text(x, TYPE_BIEN_MAP))
    df["transaction"] = df["transaction"].apply(lambda x: standardize_text(x, TRANSACTION_MAP))

    # ── 5. Outlier detection ──────────────────────────────────
    before = len(df)
    df = df[df["prix"].notna() & df["surface"].notna()]
    mask_prix = remove_outliers_iqr(df["prix"])
    mask_surface = remove_outliers_iqr(df["surface"])
    mask_chambres = (df["nb_chambres"] <= 20) | df["nb_chambres"].isna()
    df = df[mask_prix & mask_surface & mask_chambres]
    log(engine, "02_clean_data", "INFO",
        f"After outlier removal: {len(df)} rows (removed {before - len(df)})")

    # ── 6. Feature Engineering ────────────────────────────────
    df["prix_m2"] = (df["prix"] / df["surface"]).round(2)

    df["age_bien"] = (CURRENT_YEAR - df["annee_construction"]).clip(lower=0).astype("Int16")

    df["categorie_prix"] = df["prix"].apply(categorize_prix)
    df["categorie_surface"] = df["surface"].apply(categorize_surface)

    df["annee_publication"] = df["date_publication"].dt.year.astype("Int16")
    df["mois_publication"] = df["date_publication"].dt.month.astype("Int16")
    df["trimestre_publication"] = df["date_publication"].dt.quarter.astype("Int16")

    # ── 7. Drop rows with no annonce_id ───────────────────────
    df = df.dropna(subset=["annonce_id"])
    df["annonce_id"] = df["annonce_id"].astype(int)

    # ── 8. Final column selection & cast ─────────────────────
    int_cols = ["nb_chambres", "nb_salles_bain", "etage", "annee_construction"]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int16")

    keep = [
        "annonce_id", "date_publication", "titre", "ville", "quartier",
        "type_bien", "transaction", "prix", "surface",
        "nb_chambres", "nb_salles_bain", "etage", "annee_construction",
        "prix_m2", "age_bien", "categorie_prix", "categorie_surface",
        "annee_publication", "mois_publication", "trimestre_publication",
    ]
    df = df[keep]

    # ── 9. Load into clean layer ──────────────────────────────
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE clean.darkom_annonces RESTART IDENTITY"))

    df.to_sql(
        "darkom_annonces",
        engine,
        schema="clean",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    log(engine, "02_clean_data", "SUCCESS",
        f"Loaded {len(df)} clean rows", len(df))


if __name__ == "__main__":
    main()