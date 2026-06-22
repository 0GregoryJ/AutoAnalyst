{{ config(materialized='table') }}

with features as (

    select *
    from {{ ref('stg_features') }}

),

final as (

    select
        feature_id,
        feature_name,
        feature_category,
        minimum_plan,
        is_core_feature,
        feature_status,
        released_at,
        adoption_difficulty,
        retention_impact,

        case minimum_plan
            when 'starter' then 1
            when 'pro' then 2
            when 'business' then 3
        end as minimum_plan_tier_rank,

        initcap(replace(feature_name, '_', ' ')) as feature_display_name,

        case
            when feature_status = 'active'
                then true
            else false
        end as is_active_feature,

        case
            when feature_status = 'beta'
                then true
            else false
        end as is_beta_feature,

        case
            when feature_status = 'deprecated'
                then true
            else false
        end as is_deprecated_feature,

        case
            when minimum_plan = 'starter'
                then true
            else false
        end as is_starter_feature,

        case
            when minimum_plan = 'pro'
                then true
            else false
        end as is_pro_feature,

        case
            when minimum_plan = 'business'
                then true
            else false
        end as is_business_feature,

        case
            when retention_impact = 'high'
                then true
            else false
        end as is_high_retention_feature,

        case
            when adoption_difficulty = 'low'
                then 'easy_adoption'
            when adoption_difficulty = 'medium'
                then 'moderate_adoption'
            else 'hard_adoption'
        end as adoption_segment

    from features

)

select *
from final
