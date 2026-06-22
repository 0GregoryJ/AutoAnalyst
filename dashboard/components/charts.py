"""
Plotly chart builders for dashboard pages.

Turns filtered mart DataFrames into reusable figures (MRR, engagement,
transactions, churn/reliability). Each function returns an empty-state chart when data
is missing.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.config import COLORS, PLOTLY_TEMPLATE


def empty_chart(title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="No data for selected filters",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14, "color": COLORS["muted"]},
    )
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        height=380,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def chart_mrr_trend(daily: pd.DataFrame) -> go.Figure:
    if daily.empty:
        return empty_chart("MRR & Active Subscriptions")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["mrr"],
            name="MRR",
            mode="lines",
            line={"color": COLORS["primary"], "width": 2.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["active_subscriptions"],
            name="Active Subscriptions",
            mode="lines",
            yaxis="y2",
            line={"color": COLORS["success"], "width": 2, "dash": "dot"},
        )
    )
    fig.update_layout(
        title="MRR & Active Subscriptions",
        template=PLOTLY_TEMPLATE,
        height=380,
        hovermode="x unified",
        yaxis={"title": "MRR ($)", "tickformat": "$,.0f"},
        yaxis2={"title": "Active Subscriptions", "overlaying": "y", "side": "right", "showgrid": False},
    )
    return fig


def chart_mrr_by_plan(mrr_plan: pd.DataFrame) -> go.Figure:
    if mrr_plan.empty:
        return empty_chart("MRR by Plan")

    melted = mrr_plan[["metric_date", "starter_mrr", "pro_mrr", "business_mrr"]].melt(
        id_vars="metric_date",
        value_vars=["starter_mrr", "pro_mrr", "business_mrr"],
        var_name="plan",
        value_name="plan_mrr",
    )
    melted["plan"] = melted["plan"].str.replace("_mrr", "").str.title()

    fig = px.area(
        melted,
        x="metric_date",
        y="plan_mrr",
        color="plan",
        color_discrete_map={
            "Starter": COLORS["starter"],
            "Pro": COLORS["pro"],
            "Business": COLORS["business"],
        },
        title="MRR by Plan",
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(height=380, hovermode="x unified")
    return fig


def chart_engagement(daily: pd.DataFrame) -> go.Figure:
    if daily.empty:
        return empty_chart("User Engagement")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily["metric_date"],
            y=daily["total_product_events"],
            name="Product Events",
            marker_color=COLORS["primary"],
            opacity=0.35,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["daily_active_users"],
            name="Daily Active Users",
            mode="lines+markers",
            yaxis="y2",
            line={"color": COLORS["success"], "width": 2.5},
        )
    )
    fig.update_layout(
        title="User Engagement",
        template=PLOTLY_TEMPLATE,
        height=380,
        hovermode="x unified",
        yaxis={"title": "Product Events"},
        yaxis2={"title": "Daily Active Users", "overlaying": "y", "side": "right", "showgrid": False},
    )
    return fig


def chart_churn_reliability(daily: pd.DataFrame) -> go.Figure:
    if daily.empty:
        return empty_chart("Churn & Reliability")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["churn_rate"],
            name="Churn Rate",
            mode="lines",
            line={"color": COLORS["danger"], "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["transaction_failure_rate"],
            name="Txn Failure Rate",
            mode="lines",
            line={"color": COLORS["warning"], "width": 2, "dash": "dash"},
        )
    )
    fig.update_layout(
        title="Churn & Reliability",
        template=PLOTLY_TEMPLATE,
        height=380,
        hovermode="x unified",
        yaxis={"title": "Rate", "tickformat": ".1%"},
    )
    return fig


def chart_transaction_volume(daily: pd.DataFrame) -> go.Figure:
    if daily.empty:
        return empty_chart("Transaction Volume")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily["metric_date"],
            y=daily["completed_transactions"],
            name="Completed",
            marker_color=COLORS["success"],
            opacity=0.85,
        )
    )
    fig.add_trace(
        go.Bar(
            x=daily["metric_date"],
            y=daily["failed_transactions"],
            name="Failed",
            marker_color=COLORS["danger"],
            opacity=0.85,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["completed_transaction_volume"],
            name="Completed Volume ($)",
            mode="lines",
            yaxis="y2",
            line={"color": COLORS["primary"], "width": 2.5},
        )
    )
    fig.update_layout(
        title="Transaction Volume",
        template=PLOTLY_TEMPLATE,
        height=380,
        barmode="stack",
        hovermode="x unified",
        yaxis={"title": "Transaction Count"},
        yaxis2={
            "title": "Completed Volume ($)",
            "tickformat": "$,.0f",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
    )
    return fig


def chart_transaction_failure_rate(daily: pd.DataFrame) -> go.Figure:
    if daily.empty:
        return empty_chart("Transaction Failure Rate")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["transaction_failure_rate"],
            name="Failure Rate",
            mode="lines+markers",
            line={"color": COLORS["warning"], "width": 2.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["metric_date"],
            y=daily["total_transactions"],
            name="Total Transactions",
            mode="lines",
            yaxis="y2",
            line={"color": COLORS["muted"], "width": 2, "dash": "dot"},
        )
    )
    fig.update_layout(
        title="Transaction Failure Rate",
        template=PLOTLY_TEMPLATE,
        height=380,
        hovermode="x unified",
        yaxis={"title": "Failure Rate", "tickformat": ".1%"},
        yaxis2={
            "title": "Total Transactions",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
    )
    return fig
