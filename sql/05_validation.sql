-- ============================================================
-- VALIDATION QUERIES
-- ============================================================

-- Row counts per layer
SELECT 'staging'   AS layer, COUNT(*) AS rows FROM staging.darkom_annonces
UNION ALL
SELECT 'clean',    COUNT(*) FROM clean.darkom_annonces
UNION ALL
SELECT 'fact',     COUNT(*) FROM bi_schema.fact_annonces;

-- Dimension counts
SELECT 'dim_temps'            AS dim, COUNT(*) FROM bi_schema.dim_temps
UNION ALL
SELECT 'dim_localisation',    COUNT(*) FROM bi_schema.dim_localisation
UNION ALL
SELECT 'dim_type_bien',       COUNT(*) FROM bi_schema.dim_type_bien
UNION ALL
SELECT 'dim_caracteristiques',COUNT(*) FROM bi_schema.dim_caracteristiques;

-- Orphan check: facts with no dim match
SELECT COUNT(*) AS orphan_temps
FROM bi_schema.fact_annonces f
LEFT JOIN bi_schema.dim_temps t ON f.temps_id = t.temps_id
WHERE t.temps_id IS NULL;

SELECT COUNT(*) AS orphan_localisation
FROM bi_schema.fact_annonces f
LEFT JOIN bi_schema.dim_localisation l ON f.localisation_id = l.localisation_id
WHERE l.localisation_id IS NULL;

-- Null check on key fact columns
SELECT
    COUNT(*) FILTER (WHERE prix IS NULL)    AS null_prix,
    COUNT(*) FILTER (WHERE surface IS NULL) AS null_surface,
    COUNT(*) FILTER (WHERE prix_m2 IS NULL) AS null_prix_m2
FROM bi_schema.fact_annonces;

-- Price category distribution
SELECT categorie_prix, COUNT(*), ROUND(AVG(prix),2) AS avg_prix
FROM bi_schema.fact_annonces
GROUP BY categorie_prix
ORDER BY avg_prix;

-- Pipeline logs
SELECT * FROM public.pipeline_logs ORDER BY created_at;