-- Unit test: late-arriving records must not be dropped by the watermark.
--
-- Scenario: a bond was lodged in Jan 2026 (lodgement_date) but the source
-- file wasn't ingested until March 2026 (loaded_at). A watermark on
-- lodgement_date would drop this record if the last run's max lodgement_date
-- was already past Jan 2026. A watermark on loaded_at captures it correctly.
--
-- This test fails (returns rows) if staging dropped any late-arriving records.
-- "Late" = loaded_at is more than 60 days after lodgement_date.

with late_in_source as (
    select count(*) as cnt
    from read_parquet('{{ var("raw_lodgements_path") }}/lodgements_*.parquet')
    where cast(loaded_at as timestamp) - cast(lodgement_date as timestamp)
          > interval '60 days'
),

late_in_staging as (
    select count(*) as cnt
    from {{ ref('stg_bond_lodgements') }}
    where cast(loaded_at as timestamp) - cast(lodgement_date as timestamp)
          > interval '60 days'
)

-- Returns rows (test fails) if staging dropped any late-arriving records
select
    s.cnt as source_late_count,
    t.cnt as staging_late_count,
    s.cnt - t.cnt as dropped_count
from late_in_source s, late_in_staging t
where s.cnt != t.cnt
