with source as (

    select * from read_parquet(
        '{{ var("raw_lodgements_path") }}/lodgements_*.parquet'
    )

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
