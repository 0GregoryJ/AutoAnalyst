{{ config(materialized='table') }}

select
    date_trunc('day', transaction_timestamp)::date as metric_date,

    count(*) as total_transactions,

    count(*) filter (
        where transaction_status = 'completed'
    ) as completed_transactions,

    count(*) filter (
        where transaction_status = 'failed'
    ) as failed_transactions,

    count(*) filter (
        where transaction_status = 'refunded'
    ) as refunded_transactions,

    sum(transaction_amount) filter (
        where transaction_status = 'completed'
    ) as completed_transaction_volume,

    count(*) filter (
        where transaction_status = 'failed'
    )::float / nullif(count(*), 0) as transaction_failure_rate

from {{ ref('fact_transactions') }}

group by 1
order by 1