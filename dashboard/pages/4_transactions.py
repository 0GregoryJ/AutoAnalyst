"""
Page 6 — Transactions.

Shows transaction volume, counts, and failure rate over the selected date range.
Uses mart_daily_kpis via the shared sidebar filters.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.charts import chart_transaction_failure_rate, chart_transaction_volume
from components.ui import render_filters, setup_page

setup_page("Transactions", "Payment volume, transaction counts, and failure rates.")

daily, _, _, _, _ = render_filters()

left, right = st.columns(2)
with left:
    st.plotly_chart(chart_transaction_volume(daily), width="stretch")
with right:
    st.plotly_chart(chart_transaction_failure_rate(daily), width="stretch")
