{{ config(materialized='table') }}

with transactions as (

    select *
    from {{ ref('fact_transactions') }}

),

users as (

    select *
    from {{ ref('dim_users') }}

),

user_transactions as (

    select
        u.user_id,
        u.role,
        u.user_status,
        u.device_preference,
        u.onboarding_completed,
        date_trunc('day', t.transaction_timestamp)::date as metric_date,

        count(t.transaction_id) as total_transactions,

        count(t.transaction_id) filter (
            where t.transaction_status = 'completed'
        ) as completed_transactions,

        count(t.transaction_id) filter (
            where t.transaction_status = 'failed'
        ) as failed_transactions,

        sum(t.transaction_amount) filter (
            where t.transaction_status = 'completed'
        ) as completed_transaction_volume,

        count(t.transaction_id) filter (
            where t.transaction_status = 'failed'
        )::float / nullif(count(t.transaction_id), 0) as transaction_failure_rate

    from users u
    left join transactions t
        on u.user_id = t.user_id

    group by
        u.user_id,
        u.role,
        u.user_status,
        u.device_preference,
        u.onboarding_completed,
        date_trunc('day', t.transaction_timestamp)::date

)

select *
from user_transactions
where metric_date is not null