{{ config(materialized='view') }}

select  
    user_id,
    account_id,
    first_name,
    last_name,
    email,
    lower(role) as role,
    lower(user_status) as user_status,
    lower(device_preference) as device_preference,
    lower(notification_preference) as notification_preference,
    onboarding_completed::boolean as onboarding_completed,
    created_at::timestamp as created_at,
    last_login_at::timestamp as last_login_at,
    lower(user_timezone) as user_timezone

from {{ source('raw', 'raw_users') }}