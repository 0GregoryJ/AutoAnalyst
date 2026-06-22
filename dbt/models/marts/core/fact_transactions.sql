{{ config(materialized='table') }}

with transactions as (

    select *
    from {{ ref('stg_transactions') }}

),

final as (

    select
        transaction_id,
        user_id,

        transaction_timestamp,
        transaction_timestamp::date as transaction_date,
        date_trunc('week', transaction_timestamp)::date as transaction_week,
        date_trunc('month', transaction_timestamp)::date as transaction_month,

        transaction_amount,
        transaction_status,
        payment_method,
        service_category,
        customer_type,
        failure_reason,
        refund_reason,

        case
            when transaction_status = 'completed'
                then true
            else false
        end as is_completed_transaction,

        case
            when transaction_status = 'failed'
                then true
            else false
        end as is_failed_transaction,

        case
            when transaction_status = 'refunded'
                then true
            else false
        end as is_refunded_transaction,

        case
            when transaction_status = 'pending'
                then true
            else false
        end as is_pending_transaction,

        case
            when transaction_status = 'completed'
                then transaction_amount
            else 0
        end as completed_transaction_amount,

        case
            when transaction_status = 'failed'
                then 1
            else 0
        end as failed_transaction_count,

        case
            when transaction_status = 'completed'
                then 1
            else 0
        end as completed_transaction_count,

        case
            when transaction_status = 'refunded'
                then 1
            else 0
        end as refunded_transaction_count

    from transactions

)

select *
from final