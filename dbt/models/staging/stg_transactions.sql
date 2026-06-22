{{ config(materialized='view') }}

select
    transaction_id,
    user_id,
    transaction_timestamp::timestamp as transaction_timestamp,
    transaction_amount::numeric as transaction_amount,
    lower(transaction_status) as transaction_status,
    lower(payment_method) as payment_method,
    lower(service_category) as service_category,
    lower(customer_type) as customer_type,
    lower(failure_reason) as failure_reason,
    lower(refund_reason) as refund_reason
from {{ source('raw', 'raw_transactions') }}