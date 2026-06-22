"""
Page 3 — Engagement.

Shows product events and daily active users over the selected date range.
Uses the shared sidebar filters from components.ui.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.charts import chart_engagement
from components.ui import render_filters, setup_page

st.set_page_config(page_title="Engagement", layout="wide")

setup_page("Engagement", "Product usage and daily active users.")

daily, _, _, _, _ = render_filters()

st.plotly_chart(chart_engagement(daily), width="stretch")
