{{ config(materialized='table') }}

with users as (

    select *
    from {{ ref('stg_users') }}

),

final as (

    select
        user_id,
        account_id,

        first_name,
        last_name,
        concat_ws(' ', first_name, last_name) as full_name,
        email,

        role,
        user_status,
        device_preference,
        notification_preference,
        user_timezone,

        onboarding_completed,

        created_at,
        created_at::date as user_created_date,

        last_login_at,
        last_login_at::date as last_login_date,

        case
            when onboarding_completed = true
                then 'completed_onboarding'
            else 'not_completed_onboarding'
        end as onboarding_segment,

        case
            when user_status = 'active'
                then true
            else false
        end as is_active_user,

        case
            when last_login_at >= current_date - interval '30 days'
                then true
            else false
        end as is_recently_active_user,

        case
            when created_at >= current_date - interval '30 days'
                then true
            else false
        end as is_new_user_30d

    from users

)

select *
from final