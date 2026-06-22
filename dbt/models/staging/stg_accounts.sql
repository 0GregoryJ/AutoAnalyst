{{ config(materialized='view') }}

select
    account_id,
    account_name,
    lower(industry) as industry,
    lower(company_size) as company_size,
    upper(region) as region,
    signup_date::date as signup_date,
    lower(acquisition_channel) as acquisition_channel,
    lower(account_status) as account_status,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at

from {{ source('raw', 'raw_accounts') }}
