"""
Dashboard entry point.

Defines sidebar navigation and runs the selected page.
Run with: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(page_title="AutoAnalyst", page_icon="📊", layout="wide")

overview = st.Page("pages/1_overview.py", title="Overview", default=True)
revenue = st.Page("pages/2_revenue.py", title="Revenue")
engagement = st.Page("pages/3_engagement.py", title="Engagement")
transactions = st.Page("pages/4_transactions.py", title="Transactions")
anomalies = st.Page("pages/5_anomalies.py", title="Anomalies")
about = st.Page("pages/6_about.py", title="About This Data")

pg = st.navigation([overview, revenue, engagement, transactions, anomalies, about])
pg.run()
