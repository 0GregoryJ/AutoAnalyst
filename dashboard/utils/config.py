"""
Dashboard configuration and shared constants.

Loads the repo `.env` and defines colors, KPI card definitions, and CSS
used across all dashboard pages.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

COLORS = {
    "primary": "#2563EB",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "muted": "#6B7280",
    "starter": "#60A5FA",
    "pro": "#34D399",
    "business": "#A78BFA",
}

PLOTLY_TEMPLATE = "plotly_white"
METRIC_CATEGORIES = ["revenue", "retention", "engagement", "reliability"]

KPI_CARDS = [
    ("mrr", "MRR", "${:,.0f}"),
    ("active_subscriptions", "Active Subscriptions", "{:,.0f}"),
    ("daily_active_users", "Daily Active Users", "{:,.0f}"),
    ("churn_rate", "Churn Rate", "{:.2%}"),
    ("completed_transaction_volume", "Txn Volume", "${:,.0f}"),
    ("overall_health_score", "Health Score", "{:.1f}"),
]

METRIC_CSS = """
<style>
div[data-testid="stMetric"] {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px 16px;
}
div[data-testid="stMetric"] label p,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    color: #64748B !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #0F172A !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: #334155 !important;
}
</style>
"""
