"""
Page 2 — Revenue.

Shows MRR trend and MRR breakdown by plan (starter, pro, business).
Uses the shared sidebar filters from components.ui.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.charts import chart_mrr_by_plan, chart_mrr_trend
from components.ui import render_filters, setup_page

st.set_page_config(page_title="Revenue", layout="wide")

setup_page("Revenue", "MRR trends and plan mix.")

daily, mrr, _, _, _ = render_filters()

left, right = st.columns(2)
with left:
    st.plotly_chart(chart_mrr_trend(daily), width="stretch")
with right:
    st.plotly_chart(chart_mrr_by_plan(mrr), width="stretch")
