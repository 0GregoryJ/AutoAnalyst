{{ config(materialized='table') }}

with product_events as (

    select *
    from {{ ref('fact_product_events') }}

),

features as (

    select
        feature_id,
        feature_category
    from {{ ref('dim_features') }}

),

users as (

    select *
    from {{ ref('dim_users') }}

),

date_bounds as (

    select
        min(event_date) as start_date,
        max(event_date) as end_date
    from product_events

),

date_spine as (

    select
        generate_series(
            (select start_date from date_bounds),
            (select end_date from date_bounds),
            interval '1 day'
        )::date as metric_date

),

daily_engagement as (

    select
        pe.event_date as metric_date,

        count(distinct pe.user_id) as daily_active_users,
        count(*) as total_events,

        count(*)::float / nullif(count(distinct pe.user_id), 0) as events_per_active_user,

        sum(pe.failed_event_count)::float / nullif(count(*), 0) as event_failure_rate,

        count(distinct case
            when u.onboarding_completed = true then pe.user_id
        end) as onboarded_active_users,

        count(distinct case
            when u.onboarding_completed = true then pe.user_id
        end)::float / nullif(count(distinct pe.user_id), 0) as onboarded_active_user_rate,

        count(distinct case
            when pe.device_type = 'mobile' then pe.user_id
        end) as active_mobile_users,

        count(*) filter (
            where f.feature_category = 'core'
        ) as core_events,

        count(*) filter (
            where f.feature_category = 'billing'
        ) as billing_events,

        count(*) filter (
            where f.feature_category = 'payments'
        ) as payments_events,

        count(*) filter (
            where f.feature_category = 'scheduling'
        ) as scheduling_events,

        count(*) filter (
            where f.feature_category = 'crm'
        ) as crm_events,

        count(*) filter (
            where f.feature_category = 'automation'
        ) as automation_events,

        count(*) filter (
            where f.feature_category = 'reporting'
        ) as reporting_events,

        count(*) filter (
            where f.feature_category = 'operations'
        ) as operations_events,

        count(*) filter (
            where f.feature_category = 'integrations'
        ) as integrations_events

    from product_events pe

    left join users u
        on pe.user_id = u.user_id

    left join features f
        on pe.feature_id = f.feature_id

    group by
        pe.event_date

),

final as (

    select
        d.metric_date,

        coalesce(e.daily_active_users, 0) as daily_active_users,
        coalesce(e.total_events, 0) as total_events,

        coalesce(e.events_per_active_user, 0) as events_per_active_user,
        coalesce(e.event_failure_rate, 0) as event_failure_rate,

        coalesce(e.onboarded_active_users, 0) as onboarded_active_users,
        coalesce(e.onboarded_active_user_rate, 0) as onboarded_active_user_rate,

        coalesce(e.active_mobile_users, 0) as active_mobile_users,

        coalesce(e.core_events, 0) as core_events,
        coalesce(e.billing_events, 0) as billing_events,
        coalesce(e.payments_events, 0) as payments_events,
        coalesce(e.scheduling_events, 0) as scheduling_events,
        coalesce(e.crm_events, 0) as crm_events,
        coalesce(e.automation_events, 0) as automation_events,
        coalesce(e.reporting_events, 0) as reporting_events,
        coalesce(e.operations_events, 0) as operations_events,
        coalesce(e.integrations_events, 0) as integrations_events

    from date_spine d

    left join daily_engagement e
        on d.metric_date = e.metric_date

)

select *
from final
