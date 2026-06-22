{{ config(materialized='table') }}

select
    metric_date,

    count(distinct subscription_id) as active_subscriptions,

    sum(monthly_price) as mrr,

    sum(case when plan_id = 'starter' then monthly_price else 0 end) as starter_mrr,
    sum(case when plan_id = 'pro' then monthly_price else 0 end) as pro_mrr,
    sum(case when plan_id = 'business' then monthly_price else 0 end) as business_mrr,

    count(distinct case when plan_id = 'starter' then subscription_id end) as active_starter_subscriptions,
    count(distinct case when plan_id = 'pro' then subscription_id end) as active_pro_subscriptions,
    count(distinct case when plan_id = 'business' then subscription_id end) as active_business_subscriptions

from {{ ref('fact_subs_by_day') }}

where is_active_subscription = true

group by 1
order by 1