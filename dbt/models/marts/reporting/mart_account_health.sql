{{ config(materialized='table') }}

with accounts as (

    select
        account_id,
        account_name,
        industry,
        company_size,
        region,
        acquisition_channel,
        account_status,
        signup_date
    from {{ ref('dim_accounts') }}

),

as_of as (

    select max(metric_date) as as_of_date
    from {{ ref('fact_subs_by_day') }}

),

user_metrics as (

    select
        account_id,
        count(*) as total_users,
        count(*) filter (where is_active_user) as active_users,
        count(*) filter (where onboarding_completed) as onboarded_users,
        count(*) filter (where is_recently_active_user) as recently_active_users
    from {{ ref('dim_users') }}
    group by 1

),

subscription_metrics as (

    select
        s.account_id,
        count(distinct s.subscription_id) filter (where s.is_active_subscription) as active_subscriptions,
        sum(s.normalized_monthly_price) filter (where s.is_active_subscription) as current_mrr
    from {{ ref('fact_subs_by_day') }} s
    cross join as_of d
    where s.metric_date = d.as_of_date
    group by 1

),

engagement_metrics as (

    select
        u.account_id,
        count(distinct pe.user_id) as active_users_30d,
        count(*) as total_events_30d,
        sum(pe.failed_event_count)::float / nullif(count(*), 0) as event_failure_rate_30d
    from {{ ref('fact_product_events') }} pe
    join {{ ref('dim_users') }} u
        on pe.user_id = u.user_id
    cross join as_of d
    where pe.event_date > d.as_of_date - interval '30 days'
        and pe.event_date <= d.as_of_date
    group by 1

),

transaction_metrics as (

    select
        u.account_id,
        count(*) as total_transactions_30d,
        count(*) filter (where t.is_failed_transaction) as failed_transactions_30d,
        sum(t.completed_transaction_amount) as completed_volume_30d
    from {{ ref('fact_transactions') }} t
    join {{ ref('dim_users') }} u
        on t.user_id = u.user_id
    cross join as_of d
    where t.transaction_date > d.as_of_date - interval '30 days'
        and t.transaction_date <= d.as_of_date
    group by 1

),

final as (

    select
        a.account_id,
        a.account_name,
        a.industry,
        a.company_size,
        a.region,
        a.acquisition_channel,
        a.account_status,
        a.signup_date,
        d.as_of_date,

        coalesce(u.total_users, 0) as total_users,
        coalesce(u.active_users, 0) as active_users,
        coalesce(u.onboarded_users, 0) as onboarded_users,
        coalesce(u.recently_active_users, 0) as recently_active_users,

        coalesce(s.active_subscriptions, 0) as active_subscriptions,
        coalesce(s.current_mrr, 0) as current_mrr,

        coalesce(e.active_users_30d, 0) as active_users_30d,
        coalesce(e.total_events_30d, 0) as total_events_30d,
        coalesce(e.event_failure_rate_30d, 0) as event_failure_rate_30d,

        coalesce(t.total_transactions_30d, 0) as total_transactions_30d,
        coalesce(t.failed_transactions_30d, 0) as failed_transactions_30d,
        coalesce(t.completed_volume_30d, 0) as completed_volume_30d,

        coalesce(t.failed_transactions_30d, 0)::float
            / nullif(coalesce(t.total_transactions_30d, 0), 0) as transaction_failure_rate_30d,

        case
            when a.account_status = 'churned' then true
            when coalesce(s.current_mrr, 0) > 0
                and coalesce(e.active_users_30d, 0) = 0 then true
            else false
        end as is_at_risk

    from accounts a
    cross join as_of d
    left join user_metrics u
        on a.account_id = u.account_id
    left join subscription_metrics s
        on a.account_id = s.account_id
    left join engagement_metrics e
        on a.account_id = e.account_id
    left join transaction_metrics t
        on a.account_id = t.account_id

)

select *
from final
