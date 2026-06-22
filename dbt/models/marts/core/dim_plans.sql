{{ config(materialized='table') }}

with subscriptions as (

    select *
    from {{ ref('stg_subscriptions') }}

),

features as (

    select *
    from {{ ref('stg_features') }}

),

plans as (

    select distinct
        plan_id,
        monthly_price
    from subscriptions

),

plan_features as (

    select
        p.plan_id,
        count(f.feature_id) as available_feature_count,
        count(f.feature_id) filter (
            where f.is_core_feature = true
        ) as available_core_feature_count
    from plans p
    left join features f
        on (
            p.plan_id = 'starter'
            and f.minimum_plan = 'starter'
        )
        or (
            p.plan_id = 'pro'
            and f.minimum_plan in ('starter', 'pro')
        )
        or (
            p.plan_id = 'business'
            and f.minimum_plan in ('starter', 'pro', 'business')
        )
    group by
        p.plan_id

),

final as (

    select
        p.plan_id,
        p.monthly_price,
        p.monthly_price * 12 as annual_price,

        case p.plan_id
            when 'starter' then 1
            when 'pro' then 2
            when 'business' then 3
        end as plan_tier_rank,

        initcap(p.plan_id) as plan_display_name,

        pf.available_feature_count,
        pf.available_core_feature_count,

        case
            when p.plan_id = 'starter'
                then true
            else false
        end as is_entry_level_plan,

        case
            when p.plan_id = 'business'
                then true
            else false
        end as is_enterprise_plan

    from plans p
    left join plan_features pf
        on p.plan_id = pf.plan_id

)

select *
from final
