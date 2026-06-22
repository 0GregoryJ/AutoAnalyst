"""
Page 4 — Anomalies.

Shows churn/reliability trends, anomaly candidates, and AutoAnalyst
investigation reports saved to reports/investigations/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

import streamlit as st

from components.charts import chart_churn_reliability
from components.ui import (
    render_anomaly_table,
    render_filters,
    render_investigation_reports,
    setup_page,
)
from src.agent.autoanalyst_agent import run_investigation

setup_page("Anomalies", "Reliability signals and metrics flagged for investigation.")

daily, _, anomalies, start_date, end_date = render_filters(show_anomaly_filters=True)

with st.sidebar:
    st.divider()
    st.subheader("AutoAnalyst Agent")
    if st.button("Run investigation", use_container_width=True):
        with st.spinner("Investigating top anomaly..."):
            try:
                result = run_investigation()
                st.success(
                    f"Report saved for {result['anomaly']['metric_name']} "
                    f"on {result['anomaly']['metric_date']}."
                )
                st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Investigation failed: {exc}")

st.plotly_chart(chart_churn_reliability(daily), width="stretch")

st.subheader("Anomaly Candidates")
render_anomaly_table(anomalies)

st.subheader("Investigation Reports")
st.caption("Markdown reports from the AutoAnalyst agent (`reports/investigations/`).")
render_investigation_reports(start_date, end_date)
