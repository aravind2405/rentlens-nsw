# RentLens NSW — Project Brief

## Problem
NSW publishes every new rental bond as a raw monthly spreadsheet, 
but there is no open, tested pipeline that turns those files into 
clean, queryable rent medians by postcode — or checks that the 
numbers are correct.

## Users
- Renters comparing two postcodes before signing a lease
- Analysts who need clean monthly rent series without wrangling 
  56 spreadsheets manually
- Hiring managers reading the GitHub repo

## Data
- Source: NSW Fair Trading rental bond lodgements
- URL: nsw.gov.au → Housing → Rental bond data
- Format: Monthly .xlsx files, one per month from 2022 onwards
- Update frequency: Monthly, ~30 days after month end
- Licence: Creative Commons Attribution (CC BY), per the Data.NSW record. Attribution: NSW Fair Trading, © State of New South Wales; state that medians are my own aggregation. Credited in the README, on the dashboard and on the /rentlens page.
- Key fields: postcode, dwelling type, bedrooms, weekly rent, 
  lodgement date
- Known limitation: covers new tenancies only — shows rent agreed 
  at lease signing, not what existing tenants currently pay

## What this project does NOT do
- No dashboards or BI tool
- No machine learning or rent forecasting
- No scraping of listing sites (Domain, realestate.com.au)
- No bond refunds or holdings data
- No real-time feed (batch pipeline only in v0.1–v0.4)

## Tech stack and why
- Python: only viable option for downloading and parsing Excel files
- Parquet: columnar format standard for raw data landing
- dbt Core: analytics engineering standard; in 61% of Sydney 
  data engineering job ads
- DuckDB: free local warehouse; same SQL as Snowflake
- Snowflake: most-named warehouse in AU job ads; deferred to 
  Phase 9 so the 30-day trial is not wasted on early exploration
- Airflow + Cosmos: orchestration standard
- GitHub Actions: free CI; most common CI tool in the market

## Done when (v1.0)
- Pipeline runs end to end: dlt → S3 → Snowflake → dbt → Airflow
- Medians reconcile against official NSW Rent and Sales Report
- Three real findings with numbers in the README
- All design decisions documented in ADRs
- All 15 interview questions answered aloud without notes

## Risks
- File format changes between months → header detection handles it
- Snowflake trial expires mid-build → build on DuckDB first
- Scope creep → strict out-of-scope list above
- SAA-C03 exam clash (2–11 Nov) → Phase 8 planned around it