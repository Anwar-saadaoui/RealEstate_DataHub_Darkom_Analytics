-- ============================================================
-- STAGING LAYER
-- Raw CSV data loaded as-is (all text to avoid type errors)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.darkom_annonces CASCADE;

CREATE TABLE staging.darkom_annonces (
    annonce_id          TEXT,
    date_publication    TEXT,
    titre               TEXT,
    ville               TEXT,
    quartier            TEXT,
    type_bien           TEXT,
    transaction         TEXT,
    prix                TEXT,
    surface             TEXT,
    nb_chambres         TEXT,
    nb_salles_bain      TEXT,
    etage               TEXT,
    annee_construction  TEXT,
    loaded_at           TIMESTAMP DEFAULT NOW()
);

-- Index on annonce_id for dedup checks
CREATE INDEX IF NOT EXISTS idx_staging_annonce_id ON staging.darkom_annonces(annonce_id);