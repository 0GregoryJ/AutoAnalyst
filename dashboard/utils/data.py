"""
Data access layer for the dashboard.

Loads dbt marts (`mart_daily_kpis`, `mart_mrr`, `mart_anomaly_candidates`)
and provides date-range filtering for all pages.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from src.utils.db import query_df


@st.cache_data(ttl=300)
def load_daily_kpis() -> pd.DataFrame:
    df = query_df(
        "select * from analytics.mart_daily_kpis order by metric_date",
    )
    if df.empty:
        return df
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    return df


@st.cache_data(ttl=300)
def load_mrr_by_plan() -> pd.DataFrame:
    df = query_df(
        """
        select metric_date, mrr, starter_mrr, pro_mrr, business_mrr,
               active_starter_subscriptions, active_pro_subscriptions,
               active_business_subscriptions
        from analytics.mart_mrr
        order by metric_date
        """,
    )
    if df.empty:
        return df
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    return df


@st.cache_data(ttl=300)
def load_anomalies() -> pd.DataFrame:
    df = query_df(
        """
        select * from analytics.mart_anomaly_candidates
        order by metric_date desc, metric_name
        """,
    )
    if df.empty:
        return df
    df["metric_date"] = pd.to_datetime(df["metric_date"])
    return df


def filter_by_date(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if df.empty:
        return df
    mask = (df["metric_date"].dt.date >= start) & (df["metric_date"].dt.date <= end)
    return df.loc[mask].copy()
