{{ config(materialized='view') }}

select
    event_id,
    user_id,
    session_id,
    feature_id,
    lower(event_name) as event_name,
    event_timestamp::timestamp as event_timestamp,
    lower(device_type) as device_type,
    lower(event_status) as event_status,
    lower(failure_reason) as failure_reason

from {{ source('raw', 'raw_product_events') }}
