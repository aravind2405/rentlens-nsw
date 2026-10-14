with source as (

    select * from {{ ref('int_lodgements_flagged') }}
    where rent_flag is null
      and postcode_flag is null

),

aggregated as (

    select
        file_month,
        dwelling_type,
        count(*)                                    as lodgement_count,
        percentile_cont(0.5) within group (
            order by weekly_rent
        )                                           as median_weekly_rent,
        avg(weekly_rent)                            as avg_weekly_rent

    from source
    group by file_month, dwelling_type

)

select * from aggregated
order by file_month, dwelling_type
