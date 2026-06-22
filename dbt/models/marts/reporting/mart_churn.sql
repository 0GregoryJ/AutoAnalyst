{{ config(materialized='table') }}

with subscriptions as (

    select *
    from {{ ref('fact_subs_by_day') }}

),

cancelled_by_day as (

    select
        cancelled_at::date as metric_date,
        count(distinct subscription_id) as cancelled_subscriptions,

        count(distinct case when plan_id = 'starter' then subscription_id end) as starter_cancellations,
        count(distinct case when plan_id = 'pro' then subscription_id end) as pro_cancellations,
        count(distinct case when plan_id = 'business' then subscription_id end) as business_cancellations

    from subscriptions
    where cancelled_at is not null

    group by 1

),

active_starting_base as (

    select
        metric_date,
        count(distinct subscription_id) as active_subscriptions
    from {{ ref('fact_subs_by_day') }}
    where is_active_subscription = true
    group by 1

),

final as (

    select
        a.metric_date,
        a.active_subscriptions,

        coalesce(c.cancelled_subscriptions, 0) as cancelled_subscriptions,
        coalesce(c.starter_cancellations, 0) as starter_cancellations,
        coalesce(c.pro_cancellations, 0) as pro_cancellations,
        coalesce(c.business_cancellations, 0) as business_cancellations,

        coalesce(c.cancelled_subscriptions, 0)::float
            / nullif(a.active_subscriptions, 0) as daily_churn_rate

    from active_starting_base a
    left join cancelled_by_day c
        on a.metric_date = c.metric_date

)

select *
from final
order by metric_date