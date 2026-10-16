{{
    config(
        materialized='incremental',
        unique_key=['file_month', 'postcode', 'dwelling_type', 'lodgement_date', 'weekly_rent'],
        incremental_strategy='delete+insert'
    )
}}

with source as (

    select * from read_parquet(
        '{{ var("raw_lodgements_path") }}/lodgements_*.parquet'
    )

    -- Annual roll-up files repeat every row of that year's monthly files,
    -- so loading both would count each bond twice. Monthly files only.
    where file_month not like '%-annual'

    {% if is_incremental() %}
        -- Watermark on arrival time (loaded_at), not event time (lodgement_date).
        -- This ensures late-arriving records are captured on the next run.
        -- A watermark on lodgement_date would silently drop any record whose
        -- lodgement_date falls before the last run's max, even if the file
        -- was ingested after that run.
        and loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}

),

renamed as (

    select
        cast(lodgement_date         as date)           as lodgement_date,
        cast(postcode               as integer)        as postcode,
        dwelling_type,
        try_cast(bedrooms           as integer)        as bedrooms,
        try_cast(weekly_rent        as decimal(10, 2)) as weekly_rent,
        file_month,
        source_file,
        loaded_at

    from source

)

select * from renamed
