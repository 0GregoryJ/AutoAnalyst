{{ config(materialized='table') }}

with subscriptions as (

    select *
    from {{ ref('fact_subs_by_day') }}

),

plans as (

    select
        plan_id
    from {{ ref('dim_plans') }}

),

transactions as (

    select *
    from {{ ref('fact_transactions') }}

),

product_events as (

    select *
    from {{ ref('fact_product_events') }}

),

users as (

    select
        user_id,
        account_id,
        onboarding_completed
    from {{ ref('dim_users') }}

),

date_bounds as (

    select
        least(
            (select min(metric_date) from subscriptions),
            (select min(transaction_date) from transactions),
            (select min(event_date) from product_events)
        ) as start_date,
        greatest(
            (select max(metric_date) from subscriptions),
            (select max(transaction_date) from transactions),
            (select max(event_date) from product_events)
        ) as end_date

),

date_spine as (

    select
        generate_series(
            (select start_date from date_bounds),
            (select end_date from date_bounds),
            interval '1 day'
        )::date as metric_date

),

calendar as (

    select
        d.metric_date,
        p.plan_id
    from date_spine d
    cross join plans p

),

subscription_metrics as (

    select
        metric_date,
        plan_id,

        count(distinct subscription_id) filter (
            where is_active_subscription = true
        ) as active_subscriptions,

        count(distinct subscription_id) filter (
            where is_new_subscription_on_date = true
        ) as new_subscriptions,

        count(distinct subscription_id) filter (
            where is_cancelled_on_date = true
        ) as cancelled_subscriptions,

        sum(monthly_price) filter (
            where is_active_subscription = true
        ) as mrr

    from subscriptions

    group by
        metric_date,
        plan_id

),

plan_mrr_pivot as (

    select
        metric_date,

        sum(mrr) filter (
            where plan_id = 'starter'
        ) as starter_mrr,

        sum(mrr) filter (
            where plan_id = 'pro'
        ) as pro_mrr,

        sum(mrr) filter (
            where plan_id = 'business'
        ) as business_mrr

    from subscription_metrics

    group by
        metric_date

),

account_plans as (

    select
        metric_date,
        account_id,
        plan_id
    from subscriptions
    where is_active_subscription = true

),

transaction_metrics as (

    select
        t.transaction_date as metric_date,
        ap.plan_id,

        count(*) as total_transactions,

        count(*) filter (
            where t.is_completed_transaction = true
        ) as completed_transactions,

        count(*) filter (
            where t.is_failed_transaction = true
        ) as failed_transactions,

        sum(t.completed_transaction_amount) as completed_transaction_volume,

        sum(t.failed_transaction_count)::float / nullif(count(*), 0) as transaction_failure_rate

    from transactions t

    inner join users ua
        on t.user_id = ua.user_id

    inner join account_plans ap
        on ua.account_id = ap.account_id
        and t.transaction_date = ap.metric_date

    group by
        t.transaction_date,
        ap.plan_id

),

event_metrics as (

    select
        pe.event_date as metric_date,
        ap.plan_id,

        count(*) as total_product_events,

        count(distinct pe.user_id) as active_users,

        count(*)::float / nullif(count(distinct pe.user_id), 0) as events_per_active_user,

        sum(pe.failed_event_count)::float / nullif(count(*), 0) as event_failure_rate,

        count(distinct case
            when u.onboarding_completed = true then pe.user_id
        end) as active_onboarded_users,

        count(distinct case
            when u.onboarding_completed = true then pe.user_id
        end)::float / nullif(count(distinct pe.user_id), 0) as onboarded_active_user_rate

    from product_events pe

    inner join users ua
        on pe.user_id = ua.user_id

    inner join account_plans ap
        on ua.account_id = ap.account_id
        and pe.event_date = ap.metric_date

    left join users u
        on pe.user_id = u.user_id

    group by
        pe.event_date,
        ap.plan_id

),

final as (

    select
        c.metric_date,
        c.plan_id,

        coalesce(s.active_subscriptions, 0) as active_subscriptions,
        coalesce(s.new_subscriptions, 0) as new_subscriptions,
        coalesce(s.cancelled_subscriptions, 0) as cancelled_subscriptions,

        coalesce(s.cancelled_subscriptions, 0)::float
            / nullif(coalesce(s.active_subscriptions, 0), 0) as churn_rate,

        coalesce(s.mrr, 0) as mrr,

        coalesce(s.mrr, 0)
            / nullif(coalesce(s.active_subscriptions, 0), 0) as avg_revenue_per_subscription,

        coalesce(t.total_transactions, 0) as total_transactions,
        coalesce(t.completed_transactions, 0) as completed_transactions,
        coalesce(t.failed_transactions, 0) as failed_transactions,
        coalesce(t.transaction_failure_rate, 0) as transaction_failure_rate,
        coalesce(t.completed_transaction_volume, 0) as completed_transaction_volume,

        coalesce(e.total_product_events, 0) as total_product_events,
        coalesce(e.active_users, 0) as active_users,
        coalesce(e.events_per_active_user, 0) as events_per_active_user,
        coalesce(e.event_failure_rate, 0) as event_failure_rate,

        coalesce(e.active_onboarded_users, 0) as active_onboarded_users,
        coalesce(e.onboarded_active_user_rate, 0) as onboarded_active_user_rate,

        coalesce(p.starter_mrr, 0) as starter_mrr,
        coalesce(p.pro_mrr, 0) as pro_mrr,
        coalesce(p.business_mrr, 0) as business_mrr

    from calendar c

    left join subscription_metrics s
        on c.metric_date = s.metric_date
        and c.plan_id = s.plan_id

    left join plan_mrr_pivot p
        on c.metric_date = p.metric_date

    left join transaction_metrics t
        on c.metric_date = t.metric_date
        and c.plan_id = t.plan_id

    left join event_metrics e
        on c.metric_date = e.metric_date
        and c.plan_id = e.plan_id

)

select *
from final
