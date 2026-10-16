# RentLens NSW

**Actual signed rents across NSW — not asking prices.**

Domain and REA show what landlords are asking. NSW Fair Trading records what tenants actually signed. This project ingests 57 months of official bond lodgement data (Jan 2022 – Sep 2026, 1.8M+ records), runs it through a dbt pipeline on DuckDB, and surfaces median weekly rents by dwelling type, postcode, and month.

**[→ Live dashboard](https://aravind2405.github.io/rentlens-nsw/)**

---

## The gap this closes

When a renter searches on Domain, they see advertised rents — prices set before negotiation, before vacancy pressure, before the actual lease is signed. Bond lodgements capture the rent on the signed lease, submitted within 10 days of move-in. That makes them the most accurate measure of what the market is actually clearing at.

**Key findings — full dataset (Jan 2022 – Sep 2026):**
- Total bonds lodged: **1.5M records** across 57 months
- All-time median flat rent: **$680/wk** · All-time median house rent: **$650/wk**
- Peak single month: **Feb 2025** (31,430 bonds lodged)
- Priciest flat postcode (all-time): Sydney CBD (2000) at **$920/wk**

**Last 12 months (Oct 2025 – Sep 2026):**
- Median flat rent: **$750/wk** (+4.9% year-on-year)
- Median house rent: **$710/wk** (+2.9% year-on-year)
- Peak month in window: Feb 2026 (29,252 bonds lodged)

> Dashboard includes **1Y / 2Y / All** views — switch between the last 12 months, 2 years, or the full Jan 2022 – Sep 2026 history.

---


## Watermark postmortem

**Bug:** `stg_bond_lodgements` was materialised as a `view`, reading all parquet files on every run. When converted to an incremental model, the first implementation used `lodgement_date` (event time) as the watermark — the date the bond was actually signed. This is the classic event-time trap: a bond lodged in January but submitted to NSW Fair Trading in March would have a `lodgement_date` of January. If the pipeline last ran in February, the March batch's January records fall before the watermark and are silently dropped forever.

**Fix:** Watermark on `loaded_at` (arrival time) — the timestamp written by `ingest/load_lodgements.py` when the record lands in the parquet zone. This captures every record in every new file, regardless of when the underlying bond was signed.

```sql
-- Wrong (event-time watermark — drops late records)
where lodgement_date > (select max(lodgement_date) from {{ this }})

-- Correct (arrival-time watermark — captures everything new)
where loaded_at > (select max(loaded_at) from {{ this }})
```

**Test:** `tests/test_late_arriving_record_lands.sql` counts records where `loaded_at` is more than 60 days after `lodgement_date` (genuinely late-arriving bonds) and asserts the count in the staging model equals the count in the raw source. If the watermark were on `lodgement_date`, this test would catch the drop.

## Architecture

```
NSW Fair Trading XLSX (62 files)
        │
        ▼
ingest/load_lodgements.py   ← downloads + lands as Parquet (idempotent)
        │
        ▼
data/raw/lodgements/        ← one .parquet per month/year, no casting
        │
        ▼  dbt build
┌─────────────────────────────────────────┐
│  stg_bond_lodgements                    │  type-cast, rename columns
│        ↓                                │
│  int_lodgements_flagged                 │  flag outliers (rent < $50 or > $5000)
│        ↓                ↓               │
│  rents_by_month    rents_by_postcode    │  mart: median rent aggregations
└─────────────────────────────────────────┘
        │
        ▼
DuckDB (dev.duckdb)
        │
        ▼
dashboard/index.html        ← Chart.js, no build step, deploys to GitHub Pages
```

**Stack:** Python 3.13 · dbt-core · dbt-duckdb · DuckDB · Parquet · Chart.js 4.4.1 · GitHub Actions · GitHub Pages

---

## Repo layout

```
rentlens-nsw/
├── ingest/
│   ├── load_lodgements.py   # download + parquet landing
│   └── sources.csv          # 62 source URLs (2021–2026)
├── models/
│   ├── staging/
│   │   └── stg_bond_lodgements.sql
│   ├── intermediate/
│   │   └── int_lodgements_flagged.sql
│   └── marts/
│       ├── rents_by_month.sql
│       └── rents_by_postcode.sql
├── data/
│   └── raw/lodgements/      # .parquet files (git-ignored)
├── dashboard/
│   └── index.html           # standalone dashboard (no build step)
├── .github/workflows/
│   └── dbt.yml              # CI: dbt build on push
├── dbt_project.yml
├── profiles.yml
└── requirements.txt
```

---

## Quickstart

```bash
git clone https://github.com/aravind2405/rentlens-nsw.git
cd rentlens-nsw
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Download all 62 source files (takes ~5–10 min, idempotent)
python ingest/load_lodgements.py

# Build all dbt models
dbt build --profiles-dir .

# Open the dashboard
open dashboard/index.html
```

---

## Data source

NSW Fair Trading — Rental Bond Board  
[rental-bond-lodgements](https://www.nsw.gov.au/housing-and-construction/renting-a-place-to-live/rental-bonds-online/rental-bond-data)

Bond data is public under the [NSW Government open data licence](https://www.nsw.gov.au/nsw-government/policies-and-initiatives/data/open-data/open-data-licence). Each row is one bond lodgement: postcode, dwelling type, bedrooms, weekly rent, and lodgement date.

**Coverage:** Jan 2022 – Sep 2026 (monthly files) + 2021–2025 annual files  
**Records:** 1,842,751 rows after cleaning  
**Update cadence:** NSW Fair Trading publishes new monthly files ~6 weeks after month-end

---

## CI

GitHub Actions runs `dbt build --profiles-dir .` on every push. The workflow skips the download step when Parquet fixtures are already present, so CI completes in under 60 seconds.

---

## Roadmap

- [ ] `data.json` pipeline — Python queries dbt marts → writes JSON → dashboard reads dynamically
- [ ] dbt column descriptions + `dbt docs generate` published to GitHub Pages
- [ ] SQL agent over DuckDB marts (list_tables / describe_table / run_sql)
- [ ] Mac cron for monthly auto-ingest when NSW publishes new data
