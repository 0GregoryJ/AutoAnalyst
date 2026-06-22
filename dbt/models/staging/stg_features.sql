{{ config(materialized='view') }}

select
    feature_id,
    lower(feature_name) as feature_name,
    lower(feature_category) as feature_category,
    lower(minimum_plan) as minimum_plan,
    is_core_feature::boolean as is_core_feature,
    lower(feature_status) as feature_status,
    released_at::date as released_at,
    lower(adoption_difficulty) as adoption_difficulty,
    lower(retention_impact) as retention_impact

from {{ source('raw', 'raw_features') }}
