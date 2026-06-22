import json
from datetime import date, timedelta

import pandas as pd

from src.utils.db import query_df

SEVERITY_ORDER = """
    case severity
        when 'critical' then 1
        when 'high' then 2
        when 'medium' then 3
        when 'low' then 4
        else 5
    end
"""


def _records(df: pd.DataFrame, limit: int = 25) -> list[dict]:
    if df.empty:
        return []
    return json.loads(df.head(limit).to_json(orient="records", date_format="iso"))


def _metric_date_str(metric_date) -> str:
    if isinstance(metric_date, date):
        return metric_date.isoformat()
    return pd.Timestamp(metric_date).date().isoformat()


def _date_window(metric_date: str, days: int = 7) -> tuple[date, date]:
    end = date.fromisoformat(metric_date)
    start = end - timedelta(days=days)
    return start, end


def get_top_anomaly(metric_date: str | None = None) -> dict | None:
    """Return the highest-priority anomaly flagged for investigation."""
    params: dict = {}
    date_filter = ""
    if metric_date:
        date_filter = "and metric_date = %(metric_date)s"
        params["metric_date"] = date.fromisoformat(metric_date)

    df = query_df(
        f"""
        select *
        from analytics.mart_anomaly_candidates
        where should_investigate = true
        {date_filter}
        order by {SEVERITY_ORDER}, metric_date desc, metric_name
        limit 1
        """,
        params=params or None,
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    row["metric_date"] = _metric_date_str(row["metric_date"])
    return row


def get_revenue_context(metric_date: str) -> dict:
    start, end = _date_window(metric_date)
    mrr = query_df(
        """
        select *
        from analytics.mart_mrr
        where metric_date between %(start_date)s and %(end_date)s
        order by metric_date
        """,
        params={"start_date": start, "end_date": end},
    )
    plan_performance = query_df(
        """
        select metric_date, plan_id, active_subscriptions, mrr, churn_rate,
               completed_transaction_volume, transaction_failure_rate
        from analytics.mart_plan_performance
        where metric_date = %(metric_date)s
        order by plan_id
        """,
        params={"metric_date": end},
    )
    daily = query_df(
        """
        select metric_date, mrr, completed_transaction_volume, active_subscriptions
        from analytics.mart_daily_kpis
        where metric_date between %(start_date)s and %(end_date)s
        order by metric_date
        """,
        params={"start_date": start, "end_date": end},
    )
    return {
        "mrr_trend": _records(mrr),
        "plan_performance": _records(plan_performance),
        "daily_kpis": _records(daily),
    }


def get_churn_context(metric_date: str) -> dict:
    start, end = _date_window(metric_date)
    churn = query_df(
        """
        select *
        from analytics.mart_churn
        where metric_date between %(start_date)s and %(end_date)s
        order by metric_date
        """,
        params={"start_date": start, "end_date": end},
    )
    plan_performance = query_df(
        """
        select metric_date, plan_id, active_subscriptions, cancelled_subscriptions,
               churn_rate, mrr
        from analytics.mart_plan_performance
        where metric_date = %(metric_date)s
        order by plan_id
        """,
        params={"metric_date": end},
    )
    return {
        "churn_trend": _records(churn),
        "plan_performance": _records(plan_performance),
    }


def get_engagement_context(metric_date: str) -> dict:
    start, end = _date_window(metric_date)
    engagement = query_df(
        """
        select *
        from analytics.mart_user_engagement
        where metric_date between %(start_date)s and %(end_date)s
        order by metric_date
        """,
        params={"start_date": start, "end_date": end},
    )
    feature_adoption = query_df(
        """
        select metric_date, feature_id, feature_name, active_feature_users,
               total_feature_events, feature_event_failure_rate
        from analytics.mart_feature_adoption
        where metric_date = %(metric_date)s
        order by total_feature_events desc
        limit 15
        """,
        params={"metric_date": end},
    )
    return {
        "engagement_trend": _records(engagement),
        "top_features": _records(feature_adoption),
    }


def get_plan_context(metric_date: str) -> dict:
    end = date.fromisoformat(metric_date)
    plan_performance = query_df(
        """
        select *
        from analytics.mart_plan_performance
        where metric_date = %(metric_date)s
        order by plan_id
        """,
        params={"metric_date": end},
    )
    return {"plan_performance": _records(plan_performance)}


def get_transaction_context(metric_date: str) -> dict:
    start, end = _date_window(metric_date)
    transaction_health = query_df(
        """
        select *
        from analytics.mart_transaction_health
        where metric_date between %(start_date)s and %(end_date)s
        order by metric_date
        """,
        params={"start_date": start, "end_date": end},
    )
    plan_performance = query_df(
        """
        select metric_date, plan_id, total_transactions, failed_transactions,
               transaction_failure_rate, completed_transaction_volume
        from analytics.mart_plan_performance
        where metric_date = %(metric_date)s
        order by plan_id
        """,
        params={"metric_date": end},
    )
    user_activity = query_df(
        """
        select role, count(*) as users,
               sum(failed_transactions) as failed_transactions,
               sum(total_transactions) as total_transactions,
               avg(transaction_failure_rate) as avg_failure_rate
        from analytics.mart_user_transaction_activity
        where metric_date = %(metric_date)s
        group by role
        order by avg_failure_rate desc nulls last
        """,
        params={"metric_date": end},
    )
    failure_breakdown = query_df(
        """
        select payment_method, failure_reason, count(*) as failed_count
        from analytics.fact_transactions
        where transaction_date = %(metric_date)s
          and transaction_status = 'failed'
        group by payment_method, failure_reason
        order by failed_count desc
        limit 20
        """,
        params={"metric_date": end},
    )
    recent_transactions = query_df(
        """
        select transaction_status, payment_method, service_category,
               count(*) as transaction_count,
               sum(completed_transaction_amount) as completed_amount
        from analytics.fact_transactions
        where transaction_date = %(metric_date)s
        group by transaction_status, payment_method, service_category
        order by transaction_count desc
        limit 20
        """,
        params={"metric_date": end},
    )
    return {
        "transaction_health_trend": _records(transaction_health),
        "plan_performance": _records(plan_performance),
        "user_activity_by_role": _records(user_activity),
        "failure_breakdown": _records(failure_breakdown),
        "transaction_summary": _records(recent_transactions),
    }
