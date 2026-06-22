{{ config(materialized='table') }}

with product_events as (

    select *
    from {{ ref('fact_product_events') }}

),

features as (

    select
        feature_id,
        feature_name,
        feature_category,
        minimum_plan,
        is_core_feature
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

calendar as (

    select
        d.metric_date,
        f.feature_id,
        f.feature_name,
        f.feature_category,
        f.minimum_plan,
        f.is_core_feature
    from date_spine d
    cross join features f

),

feature_usage as (

    select
        pe.event_date as metric_date,
        f.feature_id,

        count(*) as total_feature_events,
        count(distinct pe.user_id) as active_feature_users,
        count(distinct pe.session_id) as feature_sessions,

        sum(pe.successful_event_count) as successful_feature_events,
        sum(pe.failed_event_count) as failed_feature_events,

        count(*) filter (
            where u.role = 'owner'
        ) as owner_feature_events,

        count(*) filter (
            where u.role = 'admin'
        ) as admin_feature_events,

        count(*) filter (
            where u.role = 'staff'
        ) as staff_feature_events,

        count(distinct case
            when u.onboarding_completed = true then pe.user_id
        end) as onboarded_feature_users,

        count(distinct case
            when u.is_active_user = true then pe.user_id
        end) as active_users_using_feature,

        count(distinct case
            when u.is_new_user_30d = true then pe.user_id
        end) as new_users_using_feature,

        count(*) filter (
            where pe.device_type = 'desktop'
        ) as desktop_events,

        count(*) filter (
            where pe.device_type = 'mobile'
        ) as mobile_events,

        count(*) filter (
            where pe.device_type = 'tablet'
        ) as tablet_events,

        count(*)::float / nullif(count(distinct pe.user_id), 0) as events_per_active_user,

        sum(pe.failed_event_count)::float / nullif(count(*), 0) as feature_event_failure_rate

    from product_events pe

    inner join features f
        on pe.feature_id = f.feature_id

    left join users u
        on pe.user_id = u.user_id

    group by
        pe.event_date,
        f.feature_id

),

final as (

    select
        c.metric_date,
        c.feature_id,
        c.feature_name,
        c.feature_category,
        c.minimum_plan,
        c.is_core_feature,

        coalesce(u.total_feature_events, 0) as total_feature_events,
        coalesce(u.active_feature_users, 0) as active_feature_users,
        coalesce(u.feature_sessions, 0) as feature_sessions,

        coalesce(u.successful_feature_events, 0) as successful_feature_events,
        coalesce(u.failed_feature_events, 0) as failed_feature_events,

        coalesce(u.owner_feature_events, 0) as owner_feature_events,
        coalesce(u.admin_feature_events, 0) as admin_feature_events,
        coalesce(u.staff_feature_events, 0) as staff_feature_events,

        coalesce(u.onboarded_feature_users, 0) as onboarded_feature_users,
        coalesce(u.active_users_using_feature, 0) as active_users_using_feature,
        coalesce(u.new_users_using_feature, 0) as new_users_using_feature,

        coalesce(u.desktop_events, 0) as desktop_events,
        coalesce(u.mobile_events, 0) as mobile_events,
        coalesce(u.tablet_events, 0) as tablet_events,

        coalesce(u.events_per_active_user, 0) as events_per_active_user,
        coalesce(u.feature_event_failure_rate, 0) as feature_event_failure_rate

    from calendar c

    left join feature_usage u
        on c.metric_date = u.metric_date
        and c.feature_id = u.feature_id

)

select *
from final
