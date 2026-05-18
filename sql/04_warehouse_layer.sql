-- ============================================================
-- DATA WAREHOUSE — STAR SCHEMA in bi_schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS bi_schema;

-- -------------------------------------------------------
-- DIM: Temps
-- -------------------------------------------------------
DROP TABLE IF EXISTS bi_schema.dim_temps CASCADE;
CREATE TABLE bi_schema.dim_temps (
    temps_id    SERIAL PRIMARY KEY,
    date_full   DATE UNIQUE NOT NULL,
    annee       SMALLINT NOT NULL,
    trimestre   SMALLINT NOT NULL,
    mois        SMALLINT NOT NULL,
    nom_mois    VARCHAR(20),
    semaine     SMALLINT
);
CREATE INDEX IF NOT EXISTS idx_dim_temps_date ON bi_schema.dim_temps(date_full);

-- -------------------------------------------------------
-- DIM: Localisation
-- -------------------------------------------------------
DROP TABLE IF EXISTS bi_schema.dim_localisation CASCADE;
CREATE TABLE bi_schema.dim_localisation (
    localisation_id SERIAL PRIMARY KEY,
    ville           VARCHAR(100) NOT NULL,
    quartier        VARCHAR(200),
    UNIQUE(ville, quartier)
);
CREATE INDEX IF NOT EXISTS idx_dim_loc_ville ON bi_schema.dim_localisation(ville);

-- -------------------------------------------------------
-- DIM: Type de bien
-- -------------------------------------------------------
DROP TABLE IF EXISTS bi_schema.dim_type_bien CASCADE;
CREATE TABLE bi_schema.dim_type_bien (
    type_bien_id    SERIAL PRIMARY KEY,
    type_bien       VARCHAR(50) NOT NULL,
    transaction     VARCHAR(20) NOT NULL,
    UNIQUE(type_bien, transaction)
);

-- -------------------------------------------------------
-- DIM: Caracteristiques du bien
-- -------------------------------------------------------
DROP TABLE IF EXISTS bi_schema.dim_caracteristiques CASCADE;
CREATE TABLE bi_schema.dim_caracteristiques (
    caract_id           SERIAL PRIMARY KEY,
    nb_chambres         SMALLINT,
    nb_salles_bain      SMALLINT,
    etage               SMALLINT,
    annee_construction  SMALLINT,
    age_bien            SMALLINT,
    categorie_surface   VARCHAR(20),
    UNIQUE(nb_chambres, nb_salles_bain, etage, annee_construction)
);

-- -------------------------------------------------------
-- FACT: Annonces
-- -------------------------------------------------------
DROP TABLE IF EXISTS bi_schema.fact_annonces CASCADE;
CREATE TABLE bi_schema.fact_annonces (
    fact_id         SERIAL PRIMARY KEY,
    annonce_id      INTEGER NOT NULL,
    temps_id        INTEGER REFERENCES bi_schema.dim_temps(temps_id),
    localisation_id INTEGER REFERENCES bi_schema.dim_localisation(localisation_id),
    type_bien_id    INTEGER REFERENCES bi_schema.dim_type_bien(type_bien_id),
    caract_id       INTEGER REFERENCES bi_schema.dim_caracteristiques(caract_id),
    prix            NUMERIC(15,2),
    surface         NUMERIC(10,2),
    prix_m2         NUMERIC(12,2),
    categorie_prix  VARCHAR(30),
    titre           TEXT
);

CREATE INDEX IF NOT EXISTS idx_fact_annonce_id ON bi_schema.fact_annonces(annonce_id);
CREATE INDEX IF NOT EXISTS idx_fact_temps      ON bi_schema.fact_annonces(temps_id);
CREATE INDEX IF NOT EXISTS idx_fact_loc        ON bi_schema.fact_annonces(localisation_id);
CREATE INDEX IF NOT EXISTS idx_fact_type       ON bi_schema.fact_annonces(type_bien_id);