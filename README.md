# 🏠 Darkom.ma — Data Warehouse Pipeline

> A full industrial data pipeline built for **Darkom.ma**, Morocco's real estate listings platform.  
> Transforms raw CSV listings into a star-schema Data Warehouse optimized for Power BI analytics.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Pipeline Layers](#pipeline-layers)
  - [Staging Layer](#staging-layer)
  - [Clean Layer](#clean-layer)
  - [Data Warehouse Layer](#data-warehouse-layer)
- [Data Model](#data-model)
- [Feature Engineering](#feature-engineering)
- [Power BI Integration](#power-bi-integration)
- [DAX Measures](#dax-measures)
- [Dashboards](#dashboards)
- [Validation & Logging](#validation--logging)
- [Environment Variables](#environment-variables)

---

## Overview

This project implements a complete **ELT data pipeline** for the Moroccan real estate platform Darkom.ma. Raw property listing data (CSV) is ingested, cleaned, modelled into a dimensional warehouse, and served to Power BI for decision-making dashboards.

**Data flow:**

```
CSV Source → Staging Layer → Clean Layer → Data Warehouse (Star Schema) → Power BI
```

The pipeline covers:
- Raw ingestion with integrity checks and logging
- Structured data cleaning (deduplication, null handling, outlier removal, standardization)
- Feature engineering (price per m², property age, price/surface categories, time dimensions)
- A star schema in PostgreSQL (`bi_schema`) optimized for analytical queries
- Power BI connection with DAX measures and 4 interactive dashboards

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                              │
│  ┌─────────────────┐          ┌──────────────────────────┐  │
│  │  darkom_postgres│          │    darkom_pipeline       │  │
│  │  PostgreSQL 15  │◄────────►│    Python 3.11           │  │
│  │                 │          │    (psycopg2, pandas,    │  │
│  │  • staging      │          │     SQLAlchemy)          │  │
│  │  • clean        │          │                          │  │
│  │  • bi_schema    │          │  01_load_staging.py      │  │
│  │  • public.logs  │          │  02_clean_data.py        │  │
│  └─────────────────┘          │  03_load_warehouse.py    │  │
│                                │  04_validate.py          │  │
│                                └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │    Power BI       │
                              │  (bi_schema)      │
                              └──────────────────┘
```

---

## Project Structure

```
darkom-dwh/
│
├── docker-compose.yml          # Orchestrates PostgreSQL + pipeline container
├── Dockerfile.python           # Python pipeline image
├── .env                        # DB credentials (not committed)
├── requirements.txt            # Python dependencies
│
├── data/
│   └── darkom_annonces.csv     # ← Place your source CSV here
│
├── sql/
│   ├── 01_init_databases.sql   # Schema creation, logs table
│   ├── 02_staging_layer.sql    # Raw staging table
│   ├── 03_clean_layer.sql      # Typed, clean table
│   ├── 04_warehouse_layer.sql  # Star schema (bi_schema)
│   └── 05_validation.sql       # Ad-hoc validation queries
│
└── scripts/
    ├── 01_load_staging.py      # CSV → staging
    ├── 02_clean_data.py        # staging → clean (full ETL)
    ├── 03_load_warehouse.py    # clean → star schema
    └── 04_validate.py          # integrity & quality checks
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 15 |
| Pipeline | Python 3.11 |
| ORM / DB | SQLAlchemy + psycopg2 |
| Data processing | pandas, numpy |
| Containerization | Docker + Docker Compose |
| BI / Visualization | Power BI Desktop |
| Query engine | DAX + Power Query (M) |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Power BI Desktop (for dashboard layer)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/darkom-dwh.git
cd darkom-dwh
```

### 2. Add your CSV

```bash
cp /path/to/your/darkom_annonces.csv data/darkom_annonces.csv
```

### 3. Configure environment

Edit `.env` if needed (defaults work out of the box):

```env
POSTGRES_USER=darkom_user
POSTGRES_PASSWORD=darkom_pass123
POSTGRES_DB=darkom_dwh
```

### 4. Run the full pipeline

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL and wait for it to be healthy
2. Run all SQL schema scripts
3. Execute the 4-step Python pipeline
4. Print a full validation report

### 5. Re-run pipeline (without rebuilding)

```bash
docker compose run --rm pipeline sh -c "
  python /app/scripts/01_load_staging.py &&
  python /app/scripts/02_clean_data.py &&
  python /app/scripts/03_load_warehouse.py &&
  python /app/scripts/04_validate.py
"
```

### 6. Access the database directly

```bash
docker exec -it darkom_postgres psql -U darkom_user -d darkom_dwh
```

---

## Pipeline Layers

### Staging Layer

**Schema:** `staging` | **Table:** `darkom_annonces`

- All columns stored as `TEXT` to avoid type-related import failures
- Table is **truncated** before each run (zone tampon / temporary zone)
- Row count verified against CSV after load
- Each run is logged to `public.pipeline_logs`

**Source columns:**

| Column | Description |
|--------|-------------|
| `annonce_id` | Unique listing ID |
| `date_publication` | Publication date |
| `titre` | Listing title |
| `ville` | City |
| `quartier` | Neighborhood |
| `type_bien` | Property type (Appartement, Villa, Terrain, Bureau…) |
| `transaction` | Transaction type (Vente / Location) |
| `prix` | Price in MAD |
| `surface` | Surface area in m² |
| `nb_chambres` | Number of bedrooms |
| `nb_salles_bain` | Number of bathrooms |
| `etage` | Floor number |
| `annee_construction` | Year of construction |

---

### Clean Layer

**Schema:** `clean` | **Table:** `darkom_annonces`

Applied transformations:

| Step | Action |
|------|--------|
| **Deduplication** | Remove exact `annonce_id` duplicates + content-based duplicates |
| **Type casting** | `date_publication → DATE`, numerics → proper types |
| **Missing dates** | Rows with no date are dropped |
| **Missing quartier** | Filled with `"Inconnu"` |
| **Missing nb_chambres / nb_salles_bain** | Filled with median per `type_bien` |
| **Missing etage** | Filled with `0` (ground floor) |
| **Missing annee_construction** | Filled with global median |
| **Missing type_bien / transaction** | Rows dropped |
| **Outlier removal** | IQR × 3 filter on `prix`, `surface`, `nb_chambres` |
| **City standardization** | Normalized to official Moroccan city names |
| **type_bien standardization** | Harmonized to canonical categories |
| **transaction standardization** | Normalized to `Vente` / `Location` |

---

### Data Warehouse Layer

**Schema:** `bi_schema` | **Model:** Star Schema

All dimensions and the fact table are fully indexed and optimized for Power BI DirectQuery or Import mode.

---

## Data Model

```
                    ┌─────────────────────┐
                    │    dim_temps        │
                    │─────────────────────│
                    │ PK temps_id         │
                    │    date_full        │
                    │    annee            │
                    │    trimestre        │
                    │    mois             │
                    │    nom_mois         │
                    │    semaine          │
                    └─────────┬───────────┘
                              │
┌──────────────────┐          │          ┌──────────────────────┐
│ dim_localisation │          │          │   dim_type_bien      │
│──────────────────│          │          │──────────────────────│
│ PK localisation_id│         │          │ PK type_bien_id      │
│    ville          │         │          │    type_bien         │
│    quartier       │         │          │    transaction       │
└────────┬──────────┘         │          └──────────┬───────────┘
         │                    │                     │
         │           ┌────────▼────────┐            │
         └──────────►│  fact_annonces  │◄───────────┘
                     │─────────────────│
                     │ PK fact_id      │
                     │    annonce_id   │
                     │    temps_id  FK │
                     │    localisa. FK │
                     │    type_bien FK │
                     │    caract_id FK │
                     │    prix         │
                     │    surface      │
                     │    prix_m2      │
                     │    categorie_prix│
                     │    titre        │
                     └────────┬────────┘
                              │
                    ┌─────────▼──────────────┐
                    │  dim_caracteristiques  │
                    │────────────────────────│
                    │ PK caract_id           │
                    │    nb_chambres         │
                    │    nb_salles_bain      │
                    │    etage               │
                    │    annee_construction  │
                    │    age_bien            │
                    │    categorie_surface   │
                    └────────────────────────┘
```

---

## Feature Engineering

New columns computed during the clean layer:

| Column | Formula | Description |
|--------|---------|-------------|
| `prix_m2` | `prix / surface` | Price per square meter |
| `age_bien` | `current_year - annee_construction` | Estimated property age |
| `categorie_prix` | Threshold-based | Économique / Moyen / Haut standing / Luxe |
| `categorie_surface` | Threshold-based | Petit (<80 m²) / Moyen (80–150 m²) / Grand (>150 m²) |
| `annee_publication` | `YEAR(date_publication)` | Publication year |
| `mois_publication` | `MONTH(date_publication)` | Publication month |
| `trimestre_publication` | `QUARTER(date_publication)` | Publication quarter |

**Price category thresholds (MAD):**

| Category | Range |
|----------|-------|
| Économique | < 500,000 |
| Moyen | 500,000 – 1,499,999 |
| Haut standing | 1,500,000 – 3,999,999 |
| Luxe | ≥ 4,000,000 |

---

## Power BI Integration

### Connection settings

| Field | Value |
|-------|-------|
| Server | `localhost` |
| Port | `5432` |
| Database | `darkom_dwh` |
| Schema | `bi_schema` |
| Username | `darkom_user` |
| Password | `darkom_pass123` |

### Tables to import

- `bi_schema.fact_annonces`
- `bi_schema.dim_temps`
- `bi_schema.dim_localisation`
- `bi_schema.dim_type_bien`
- `bi_schema.dim_caracteristiques`

### Power Query checks

Once connected, use Power Query to:
- Verify column data types
- Apply any remaining minor filters
- Create calculated columns if needed

---

## DAX Measures

```dax
Total Annonces = COUNTROWS(fact_annonces)

Prix Moyen = AVERAGE(fact_annonces[prix])

Prix Moyen M2 = AVERAGE(fact_annonces[prix_m2])

Surface Moyenne = AVERAGE(fact_annonces[surface])

Prix Moyen par Ville =
CALCULATE(
    AVERAGE(fact_annonces[prix]),
    ALLEXCEPT(fact_annonces, dim_localisation[ville])
)

Annonces Annee Precedente =
CALCULATE(
    [Total Annonces],
    SAMEPERIODLASTYEAR(dim_temps[date_full])
)

Taux Croissance Annonces =
DIVIDE(
    [Total Annonces] - [Annonces Annee Precedente],
    [Annonces Annee Precedente],
    0
)

Repartition Type Bien =
DIVIDE(
    COUNTROWS(fact_annonces),
    CALCULATE(COUNTROWS(fact_annonces), ALL(dim_type_bien[type_bien]))
)

Prix Moyen YTD =
CALCULATE(
    AVERAGE(fact_annonces[prix]),
    DATESYTD(dim_temps[date_full])
)
```

---

## Dashboards

### Dashboard 1 — Vue Globale du Marché
- Total annonces (KPI card)
- Prix moyen du marché (KPI card)
- Surface moyenne (KPI card)
- Répartition des annonces par ville (bar chart)
- Évolution temporelle du volume d'annonces (line chart)
- Répartition par type de bien (donut chart)
- Répartition Vente vs Location (pie chart)

### Dashboard 2 — Analyse des Prix
- Distribution des prix (histogram)
- Prix moyen par m² (bar chart)
- Comparaison des segments (Économique → Luxe)
- Prix par type de bien (grouped bar)
- Analyse par catégorie de prix (treemap)

### Dashboard 3 — Analyse Géographique
- Répartition des annonces par ville (map + bar)
- Classement des zones les plus chères (ranked table)
- Top quartiers par nombre d'annonces
- Prix moyen par ville et quartier (matrix)

### Dashboard 4 — Analyse des Tendances
- Évolution des prix dans le temps (line chart)
- Évolution du volume des annonces (area chart)
- Analyse saisonnière par mois/trimestre (heatmap)
- Comparaison N vs N-1 (dual axis line)

### Interactive Filters (all dashboards)
- 🏙 Ville
- 🏠 Type de bien
- 💰 Transaction (Vente / Location)
- 📊 Plage de prix
- 📐 Surface
- 📅 Période

---

## Validation & Logging

Every pipeline step writes to `public.pipeline_logs`:

```sql
SELECT step, status, message, rows_count, created_at
FROM public.pipeline_logs
ORDER BY created_at;
```

The validation script (`04_validate.py`) checks:
- ✅ Row counts across all layers
- ✅ Orphan foreign key check (facts → all dims)
- ✅ Null checks on critical fact columns
- ✅ Price category distribution
- ✅ Full pipeline log summary

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `darkom_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `darkom_pass123` | PostgreSQL password |
| `POSTGRES_DB` | `darkom_dwh` | Database name |
| `POSTGRES_HOST` | `postgres` (in Docker) | DB host |
| `POSTGRES_PORT` | `5432` | DB port |

> ⚠️ Do not commit `.env` to version control. Add it to `.gitignore`.

---

## .gitignore recommendation

```
.env
data/darkom_annonces.csv
__pycache__/
*.pyc
.DS_Store
```

---
[Dashboard github Link](https://github.com/Anwar-saadaoui/RealEstate_DataHub_Darkom_Analytics_Dashboard.git)
---
*Built as part of a Data Engineering academic project — Darkom.ma real estate analytics pipeline.*
