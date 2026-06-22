{{ config(materialized='table') }}

with accounts as (

    select *
    from {{ ref('stg_accounts') }}

),

final as (

    select
        account_id,
        account_name,

        industry,
        company_size,
        region,
        acquisition_channel,
        account_status,

        signup_date,
        created_at,
        created_at::date as account_created_date,
        updated_at,
        updated_at::date as account_updated_date,

        initcap(replace(industry, '_', ' ')) as industry_display_name,
        initcap(replace(company_size, '_', ' ')) as company_size_display_name,
        initcap(replace(acquisition_channel, '_', ' ')) as acquisition_channel_display_name,

        case company_size
            when 'solo' then 1
            when 'small' then 2
            when 'mid_market' then 3
        end as company_size_rank,

        case
            when account_status = 'active'
                then true
            else false
        end as is_active_account,

        case
            when account_status = 'churned'
                then true
            else false
        end as is_churned_account,

        case
            when signup_date >= current_date - interval '30 days'
                then true
            else false
        end as is_new_account_30d

    from accounts

)

select *
from final
