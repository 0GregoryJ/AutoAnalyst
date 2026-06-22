"""
Page 1 — Overview.

Streamlit home page with KPI cards and a high-level view of MRR and engagement.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.charts import chart_engagement, chart_mrr_trend
from components.ui import render_filters, render_kpi_row, setup_page

setup_page(
    "GTech Metrics",
    "Executive overview of revenue, retention, engagement, and reliability.",
)

daily, mrr, _, _, _ = render_filters()

st.subheader("Key Performance Indicators")
render_kpi_row(daily)

st.divider()

left, right = st.columns(2)
with left:
    st.plotly_chart(chart_mrr_trend(daily), width="stretch")
with right:
    st.plotly_chart(chart_engagement(daily), width="stretch")
