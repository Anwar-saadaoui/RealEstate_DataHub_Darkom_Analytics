-- ============================================================
-- CLEAN LAYER
-- Typed, cleaned, feature-engineered table
-- ============================================================

CREATE SCHEMA IF NOT EXISTS clean;

DROP TABLE IF EXISTS clean.darkom_annonces CASCADE;

CREATE TABLE clean.darkom_annonces (
    annonce_id              INTEGER PRIMARY KEY,
    date_publication        DATE,
    titre                   TEXT,
    ville                   VARCHAR(100),
    quartier                VARCHAR(200),
    type_bien               VARCHAR(50),
    transaction             VARCHAR(20),
    prix                    NUMERIC(15,2),
    surface                 NUMERIC(10,2),
    nb_chambres             SMALLINT,
    nb_salles_bain          SMALLINT,
    etage                   SMALLINT,
    annee_construction      SMALLINT,
    -- Feature engineering
    prix_m2                 NUMERIC(12,2),
    age_bien                SMALLINT,
    categorie_prix          VARCHAR(30),
    categorie_surface       VARCHAR(20),
    annee_publication       SMALLINT,
    mois_publication        SMALLINT,
    trimestre_publication   SMALLINT,
    cleaned_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clean_ville       ON clean.darkom_annonces(ville);
CREATE INDEX IF NOT EXISTS idx_clean_type_bien   ON clean.darkom_annonces(type_bien);
CREATE INDEX IF NOT EXISTS idx_clean_transaction ON clean.darkom_annonces(transaction);
CREATE INDEX IF NOT EXISTS idx_clean_date        ON clean.darkom_annonces(date_publication);