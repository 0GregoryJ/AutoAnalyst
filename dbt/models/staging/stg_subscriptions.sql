{{ config(materialized='view') }}

with ranked as (

    select
        subscription_id,
        account_id,
        plan_id,
        monthly_price,
        billing_period,
        subscription_status,
        trial_started_at,
        trial_ended_at,
        started_at,
        cancelled_at,
        cancel_reason,
        payment_method,
        auto_renew,
        discount_percent,
        sales_assisted,
        updated_at,

        row_number() over (
            partition by subscription_id
            order by updated_at desc nulls last
        ) as row_num

    from {{ source('raw', 'raw_subscriptions') }}

)

select
    subscription_id,
    account_id,
    lower(plan_id) as plan_id,
    monthly_price::numeric as monthly_price,
    lower(billing_period) as billing_period,
    lower(subscription_status) as subscription_status,
    trial_started_at::timestamp as trial_started_at,
    trial_ended_at::timestamp as trial_ended_at,
    started_at::timestamp as started_at,
    cancelled_at::timestamp as cancelled_at,
    lower(cancel_reason) as cancel_reason,
    lower(payment_method) as payment_method,
    auto_renew::boolean as auto_renew,
    discount_percent::numeric as discount_percent,
    sales_assisted::boolean as sales_assisted,
    updated_at::timestamp as updated_at

from ranked

where row_num = 1
