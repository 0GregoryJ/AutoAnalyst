"""
Reusable Streamlit UI pieces for every dashboard page.

Renders the shared sidebar filters, page header styling, KPI metric cards,
and the anomaly candidates table. Pages call these helpers instead of
duplicating layout code.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.config import KPI_CARDS, METRIC_CATEGORIES, METRIC_CSS
from utils.data import filter_by_date, load_anomalies, load_daily_kpis, load_mrr_by_plan


def setup_page(title: str, caption: str) -> None:
    st.markdown(METRIC_CSS, unsafe_allow_html=True)
    st.title(title)
    st.caption(caption)


def render_filters(show_anomaly_filters: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, date, date]:
    daily_all = load_daily_kpis()
    mrr_all = load_mrr_by_plan()
    anomalies_all = load_anomalies()

    if daily_all.empty:
        st.error(
            "No data in `analytics.mart_daily_kpis`. "
            "Run ingestion and `dbt run` first."
        )
        st.stop()

    min_date = daily_all["metric_date"].min().date()
    max_date = daily_all["metric_date"].max().date()
    default_start = max(min_date, max_date - timedelta(days=90))

    with st.sidebar:
        st.header("Filters")
        date_range = st.date_input(
            "Date range",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if show_anomaly_filters:
            show_anomalies_only = st.toggle("Show investigation flags only", value=False)
            anomaly_categories = st.multiselect(
                "Anomaly categories",
                options=METRIC_CATEGORIES,
                default=METRIC_CATEGORIES,
            )
        if st.button("Refresh data"):
            st.cache_data.clear()
            st.rerun()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range if isinstance(date_range, date) else max_date

    daily = filter_by_date(daily_all, start_date, end_date)
    mrr = filter_by_date(mrr_all, start_date, end_date)
    anomalies = filter_by_date(anomalies_all, start_date, end_date)

    if show_anomaly_filters:
        if not anomalies.empty and anomaly_categories:
            anomalies = anomalies[anomalies["metric_category"].isin(anomaly_categories)]
        if show_anomalies_only and not anomalies.empty:
            anomalies = anomalies[anomalies["should_investigate"]]

    return daily, mrr, anomalies, start_date, end_date


def format_value(value, fmt: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return str(value)


def format_delta(value: float | None, field: str) -> str | None:
    if value is None or pd.isna(value):
        return None
    if field == "churn_rate":
        return f"{value:+.2%}"
    if field == "overall_health_score":
        return f"{value:+.1f}"
    if field in ("mrr", "completed_transaction_volume"):
        return f"${value:+,.0f}"
    return f"{value:+,.0f}"


def render_kpi_row(daily: pd.DataFrame) -> None:
    if daily.empty:
        st.warning("No KPI data for the selected date range.")
        return

    latest = daily.iloc[-1]
    previous = daily.iloc[-2] if len(daily) > 1 else None
    cols = st.columns(len(KPI_CARDS))

    for col, (field, label, fmt) in zip(cols, KPI_CARDS):
        current = latest.get(field)
        prev = previous.get(field) if previous is not None else None
        delta = None
        if current is not None and prev is not None and not pd.isna(current) and not pd.isna(prev):
            delta = float(current) - float(prev)
        with col:
            st.metric(label, format_value(current, fmt), format_delta(delta, field))


def render_anomaly_table(anomalies: pd.DataFrame) -> None:
    if anomalies.empty:
        st.info("No anomaly records for the selected filters.")
        return

    table = anomalies[
        [
            "metric_date",
            "metric_name",
            "metric_category",
            "current_value",
            "previous_value",
            "absolute_change",
            "percent_change",
            "severity",
            "anomaly_direction",
            "should_investigate",
        ]
    ].copy()
    table["metric_date"] = table["metric_date"].dt.date
    table["percent_change"] = table["percent_change"].apply(
        lambda x: f"{x:.1%}" if pd.notna(x) else "—"
    )
    st.dataframe(table, width="stretch", hide_index=True)


def render_investigation_reports(start_date: date, end_date: date) -> None:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))

    from src.agent.report_writer import filter_reports, load_report, parse_report_filename

    reports = filter_reports(start=start_date, end=end_date)
    if not reports:
        st.info("No investigation reports for the selected date range.")
        return

    for path in reports:
        meta = parse_report_filename(path)
        label = path.stem.replace("_", " ", 1) if meta else path.name
        with st.expander(label, expanded=len(reports) == 1):
            st.markdown(load_report(path))
