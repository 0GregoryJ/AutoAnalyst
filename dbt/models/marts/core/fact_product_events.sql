{{ config(materialized='table') }}

with product_events as (

    select *
    from {{ ref('stg_product_events') }}

),

final as (

    select
        event_id,
        user_id,
        session_id,
        feature_id,
        event_name,

        event_timestamp,
        event_timestamp::date as event_date,
        date_trunc('week', event_timestamp)::date as event_week,
        date_trunc('month', event_timestamp)::date as event_month,

        device_type,
        event_status,
        failure_reason,

        case
            when event_status = 'success'
                then true
            else false
        end as is_successful_event,

        case
            when event_status = 'failed'
                then true
            else false
        end as is_failed_event,

        case
            when event_status = 'success'
                then 1
            else 0
        end as successful_event_count,

        case
            when event_status = 'failed'
                then 1
            else 0
        end as failed_event_count

    from product_events

)

select *
from final
