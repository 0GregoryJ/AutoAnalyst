{{ config(materialized='table') }}

with mrr as (

    select *
    from {{ ref('mart_mrr') }}

),

churn as (

    select
        metric_date,
        cancelled_subscriptions,
        daily_churn_rate as churn_rate
    from {{ ref('mart_churn') }}

),

transactions as (

    select *
    from {{ ref('mart_transaction_health') }}

),

engagement as (

    select
        metric_date,
        daily_active_users,
        total_events as total_product_events,
        events_per_active_user,
        event_failure_rate
    from {{ ref('mart_user_engagement') }}

),

feature_daily as (

    select
        metric_date,

        sum(total_feature_events) as total_feature_events,

        sum(active_feature_users) as active_feature_users,

        sum(failed_feature_events)::float
            / nullif(sum(total_feature_events), 0) as feature_event_failure_rate,

        count(distinct case
            when total_feature_events > 0 then feature_id
        end)::float / nullif(count(distinct feature_id), 0) as feature_adoption_rate

    from {{ ref('mart_feature_adoption') }}

    group by
        metric_date

),

new_subscriptions_daily as (

    select
        metric_date,
        sum(new_subscriptions) as new_subscriptions
    from {{ ref('mart_plan_performance') }}

    group by
        metric_date

),

date_bounds as (

    select
        least(
            (select min(metric_date) from mrr),
            (select min(metric_date) from churn),
            (select min(metric_date) from transactions),
            (select min(metric_date) from engagement),
            (select min(metric_date) from feature_daily)
        ) as start_date,
        greatest(
            (select max(metric_date) from mrr),
            (select max(metric_date) from churn),
            (select max(metric_date) from transactions),
            (select max(metric_date) from engagement),
            (select max(metric_date) from feature_daily)
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

daily_base as (

    select
        d.metric_date,

        coalesce(m.mrr, 0) as mrr,
        coalesce(m.active_subscriptions, 0) as active_subscriptions,
        coalesce(n.new_subscriptions, 0) as new_subscriptions,
        coalesce(c.cancelled_subscriptions, 0) as cancelled_subscriptions,
        coalesce(c.churn_rate, 0) as churn_rate,

        coalesce(e.daily_active_users, 0) as daily_active_users,
        coalesce(e.total_product_events, 0) as total_product_events,
        coalesce(e.events_per_active_user, 0) as events_per_active_user,
        coalesce(e.event_failure_rate, 0) as event_failure_rate,

        coalesce(t.total_transactions, 0) as total_transactions,
        coalesce(t.completed_transactions, 0) as completed_transactions,
        coalesce(t.failed_transactions, 0) as failed_transactions,
        coalesce(t.transaction_failure_rate, 0) as transaction_failure_rate,
        coalesce(t.completed_transaction_volume, 0) as completed_transaction_volume,

        coalesce(f.total_feature_events, 0) as total_feature_events,
        coalesce(f.active_feature_users, 0) as active_feature_users,
        coalesce(f.feature_event_failure_rate, 0) as feature_event_failure_rate,
        coalesce(f.feature_adoption_rate, 0) as feature_adoption_rate

    from date_spine d

    left join mrr m
        on d.metric_date = m.metric_date

    left join churn c
        on d.metric_date = c.metric_date

    left join new_subscriptions_daily n
        on d.metric_date = n.metric_date

    left join transactions t
        on d.metric_date = t.metric_date

    left join engagement e
        on d.metric_date = e.metric_date

    left join feature_daily f
        on d.metric_date = f.metric_date

),

with_changes as (

    select
        *,

        mrr - lag(mrr) over (order by metric_date) as mrr_dod_change,

        (mrr - lag(mrr) over (order by metric_date))
            / nullif(lag(mrr) over (order by metric_date), 0) as mrr_dod_pct_change,

        daily_active_users - lag(daily_active_users) over (order by metric_date) as daily_active_users_dod_change,

        transaction_failure_rate - lag(transaction_failure_rate) over (order by metric_date) as transaction_failure_rate_dod_change,

        churn_rate - lag(churn_rate) over (order by metric_date) as churn_rate_dod_change

    from daily_base

),

final as (

    select
        metric_date,

        mrr,
        active_subscriptions,
        new_subscriptions,
        cancelled_subscriptions,
        churn_rate,

        daily_active_users,
        total_product_events,
        events_per_active_user,
        event_failure_rate,

        total_transactions,
        completed_transactions,
        failed_transactions,
        transaction_failure_rate,
        completed_transaction_volume,

        total_feature_events,
        active_feature_users,
        feature_event_failure_rate,
        feature_adoption_rate,

        coalesce(mrr_dod_change, 0) as mrr_dod_change,
        coalesce(mrr_dod_pct_change, 0) as mrr_dod_pct_change,
        coalesce(daily_active_users_dod_change, 0) as daily_active_users_dod_change,
        coalesce(transaction_failure_rate_dod_change, 0) as transaction_failure_rate_dod_change,
        coalesce(churn_rate_dod_change, 0) as churn_rate_dod_change,

        round(
            (
                least(100, greatest(0, 50 + coalesce(mrr_dod_pct_change, 0) * 100)) * 0.30
                + least(100, greatest(0, 100 - churn_rate * 1000)) * 0.25
                + least(100, greatest(0, 100 - transaction_failure_rate * 200)) * 0.25
                + least(100, greatest(0, 100 - event_failure_rate * 200)) * 0.20
            )::numeric,
            2
        ) as overall_health_score,

        case
            when abs(coalesce(mrr_dod_pct_change, 0)) > 0.10
                or abs(coalesce(churn_rate_dod_change, 0)) > 0.02
                or abs(coalesce(transaction_failure_rate_dod_change, 0)) > 0.05
                or abs(coalesce(daily_active_users_dod_change, 0)) > 50
                then true
            else false
        end as has_anomaly

    from with_changes

)

select *
from final
