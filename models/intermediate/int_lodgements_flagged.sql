with source as (

    select * from {{ ref('stg_bond_lodgements') }}

),

flagged as (

    select
        *,

        case
            when weekly_rent is null  then 'null_rent'
            when weekly_rent = 0      then 'zero_rent'
            when weekly_rent < 50     then 'very_low_rent'
            else null
        end as rent_flag,

        case
            when bedrooms is null then 'unknown_bedrooms'
            else null
        end as bedrooms_flag,

        case
            when postcode < 2000 or postcode > 2999 then 'invalid_postcode'
            else null
        end as postcode_flag

    from source

)

select * from flagged
