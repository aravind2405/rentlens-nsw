# ADR-001: Use DuckDB locally, Snowflake in production

Date: 2026-10-07
Status: Accepted

## Context
Need a warehouse to develop and test dbt models without cloud 
cost or setup during early development phases.

## Options
1. DuckDB locally + Snowflake only once models are stable
2. Snowflake trial from day one

## Decision
Use DuckDB for all local development and CI. Start the Snowflake 
trial only when models are ready (Phase 9, late November 2026).
Keep DuckDB adapter as a permanent fallback after the trial ends.

## Consequences
- Free and fast local iteration with no cloud dependency
- 30-day Snowflake trial not wasted on early exploration
- Must test for SQL dialect differences between DuckDB and 
  Snowflake when migrating in Phase 9