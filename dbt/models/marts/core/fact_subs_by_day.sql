{{ config(materialized='table') }}

with subscriptions as (

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
        updated_at
    from {{ ref('stg_subscriptions') }}

),

date_bounds as (

    select
        min(started_at)::date as start_date,
        max(
            greatest(
                coalesce(started_at::date, '1900-01-01'::date),
                coalesce(cancelled_at::date, '1900-01-01'::date),
                coalesce(updated_at::date, '1900-01-01'::date)
            )
        ) as end_date
    from subscriptions

),

date_spine as (

    select
        generate_series(
            start_date,
            end_date,
            interval '1 day'
        )::date as metric_date
    from date_bounds

),

subscription_daily as (

    select
        d.metric_date,

        s.subscription_id,
        s.account_id,
        s.plan_id,
        s.monthly_price,
        s.billing_period,

        s.subscription_status,
        s.started_at,
        s.cancelled_at,
        s.cancel_reason,

        s.payment_method,
        s.auto_renew,
        s.discount_percent,
        s.sales_assisted,

        case
            when s.billing_period = 'annual'
                then s.monthly_price
            else s.monthly_price
        end as normalized_monthly_price,

        case
            when s.started_at::date <= d.metric_date
                and (
                    s.cancelled_at is null
                    or s.cancelled_at::date > d.metric_date
                )
                and s.subscription_status in ('active', 'past_due', 'cancelled')
                then true
            else false
        end as is_active_subscription,

        case
            when s.cancelled_at::date = d.metric_date
                then true
            else false
        end as is_cancelled_on_date,

        case
            when s.started_at::date = d.metric_date
                then true
            else false
        end as is_new_subscription_on_date

    from date_spine d
    join subscriptions s
        on s.started_at::date <= d.metric_date
        and (
            s.cancelled_at is null
            or s.cancelled_at::date >= d.metric_date
        )

)

select *
from subscription_daily