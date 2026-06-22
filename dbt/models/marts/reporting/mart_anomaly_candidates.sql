{{ config(materialized='table') }}

with daily as (

    select
        metric_date,

        mrr,
        churn_rate,
        daily_active_users,
        events_per_active_user,
        event_failure_rate,
        transaction_failure_rate,
        completed_transaction_volume,
        active_subscriptions,
        cancelled_subscriptions

    from {{ ref('mart_daily_kpis') }}

),

with_previous as (

    select
        metric_date,

        mrr,
        lag(mrr) over (order by metric_date) as previous_mrr,

        churn_rate,
        lag(churn_rate) over (order by metric_date) as previous_churn_rate,

        daily_active_users,
        lag(daily_active_users) over (order by metric_date) as previous_daily_active_users,

        events_per_active_user,
        lag(events_per_active_user) over (order by metric_date) as previous_events_per_active_user,

        event_failure_rate,
        lag(event_failure_rate) over (order by metric_date) as previous_event_failure_rate,

        transaction_failure_rate,
        lag(transaction_failure_rate) over (order by metric_date) as previous_transaction_failure_rate,

        completed_transaction_volume,
        lag(completed_transaction_volume) over (order by metric_date) as previous_completed_transaction_volume,

        active_subscriptions,
        lag(active_subscriptions) over (order by metric_date) as previous_active_subscriptions,

        cancelled_subscriptions,
        lag(cancelled_subscriptions) over (order by metric_date) as previous_cancelled_subscriptions

    from daily

),

unpivoted as (

    select
        metric_date,
        'mrr' as metric_name,
        'revenue' as metric_category,
        mrr::numeric as current_value,
        previous_mrr::numeric as previous_value,
        0.10::numeric as threshold_value,
        'percent_change' as threshold_type,
        'higher_is_better' as direction_preference
    from with_previous

    union all

    select
        metric_date,
        'churn_rate',
        'retention',
        churn_rate::numeric,
        previous_churn_rate::numeric,
        0.02::numeric,
        'absolute_change',
        'lower_is_better'
    from with_previous

    union all

    select
        metric_date,
        'daily_active_users',
        'engagement',
        daily_active_users::numeric,
        previous_daily_active_users::numeric,
        50::numeric,
        'absolute_change',
        'higher_is_better'
    from with_previous

    union all

    select
        metric_date,
        'events_per_active_user',
        'engagement',
        events_per_active_user::numeric,
        previous_events_per_active_user::numeric,
        0.20::numeric,
        'percent_change',
        'higher_is_better'
    from with_previous

    union all

    select
        metric_date,
        'event_failure_rate',
        'reliability',
        event_failure_rate::numeric,
        previous_event_failure_rate::numeric,
        0.05::numeric,
        'absolute_change',
        'lower_is_better'
    from with_previous

    union all

    select
        metric_date,
        'transaction_failure_rate',
        'reliability',
        transaction_failure_rate::numeric,
        previous_transaction_failure_rate::numeric,
        0.05::numeric,
        'absolute_change',
        'lower_is_better'
    from with_previous

    union all

    select
        metric_date,
        'completed_transaction_volume',
        'revenue',
        completed_transaction_volume::numeric,
        previous_completed_transaction_volume::numeric,
        0.25::numeric,
        'percent_change',
        'higher_is_better'
    from with_previous

    union all

    select
        metric_date,
        'active_subscriptions',
        'retention',
        active_subscriptions::numeric,
        previous_active_subscriptions::numeric,
        10::numeric,
        'absolute_change',
        'higher_is_better'
    from with_previous

    union all

    select
        metric_date,
        'cancelled_subscriptions',
        'retention',
        cancelled_subscriptions::numeric,
        previous_cancelled_subscriptions::numeric,
        3::numeric,
        'absolute_change',
        'lower_is_better'
    from with_previous

),

scored as (

    select
        metric_date,
        metric_name,
        metric_category,
        current_value,
        previous_value,

        current_value - previous_value as absolute_change,

        case
            when previous_value is null or previous_value = 0
                then null
            else (current_value - previous_value) / previous_value
        end as percent_change,

        threshold_value,

        case
            when threshold_type = 'percent_change'
                then abs(
                    case
                        when previous_value is null or previous_value = 0
                            then 0
                        else (current_value - previous_value) / previous_value
                    end
                ) / nullif(threshold_value, 0)
            else abs(current_value - coalesce(previous_value, current_value))
                / nullif(threshold_value, 0)
        end as threshold_ratio,

        case
            when current_value > previous_value then 'up'
            when current_value < previous_value then 'down'
            else 'flat'
        end as anomaly_direction,

        direction_preference,
        threshold_type

    from unpivoted

),

final as (

    select
        metric_date,
        metric_name,
        metric_category,
        current_value,
        previous_value,
        absolute_change,
        percent_change,
        threshold_value,

        case
            when previous_value is null then 'none'
            when coalesce(threshold_ratio, 0) >= 2 then 'critical'
            when threshold_ratio >= 1.5 then 'high'
            when threshold_ratio >= 1 then 'medium'
            else 'low'
        end as severity,

        anomaly_direction,

        case
            when previous_value is null then false
            when threshold_type = 'percent_change'
                and abs(coalesce(percent_change, 0)) > threshold_value
                then true
            when threshold_type = 'absolute_change'
                and abs(coalesce(absolute_change, 0)) > threshold_value
                then true
            else false
        end as should_investigate,

        current_timestamp as created_at

    from scored

)

select *
from final
order by
    metric_date desc,
    metric_category,
    metric_name
