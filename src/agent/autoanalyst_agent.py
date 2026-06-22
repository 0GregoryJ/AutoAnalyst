"""
AutoAnalyst agent controller.

Workflow:
1. Get top anomaly
2. Route by category / metric name
3. Collect supporting SQL evidence
4. Generate investigation report (LLM or fallback)
5. Save markdown to reports/investigations/
"""

import sys
from pathlib import Path
from datetime import date

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import json
import os
from typing import Any

from src.agent import prompts
from src.agent import tools
from src.agent.report_writer import report_path_for, save_report


def classify_anomaly(anomaly: dict) -> str:
    category = anomaly.get("metric_category", "")
    metric_name = anomaly.get("metric_name", "")

    if category == "reliability":
        if metric_name == "event_failure_rate":
            return "engagement"
        return "transaction"

    if category == "revenue":
        return "revenue"
    if category == "retention":
        return "churn"
    if category == "engagement":
        return "engagement"

    return "revenue"


def collect_evidence(investigation_type: str, anomaly: dict) -> dict[str, Any]:
    metric_date = anomaly["metric_date"]

    evidence: dict[str, Any] = {
        "investigation_type": investigation_type,
        "plan_context": tools.get_plan_context(metric_date),
    }

    if investigation_type == "transaction":
        evidence["transaction_context"] = tools.get_transaction_context(metric_date)
    elif investigation_type == "revenue":
        evidence["revenue_context"] = tools.get_revenue_context(metric_date)
    elif investigation_type == "churn":
        evidence["churn_context"] = tools.get_churn_context(metric_date)
    elif investigation_type == "engagement":
        evidence["engagement_context"] = tools.get_engagement_context(metric_date)

    return evidence


def _format_anomaly_summary(anomaly: dict) -> str:
    current = anomaly.get("current_value")
    previous = anomaly.get("previous_value")
    pct = anomaly.get("percent_change")
    metric_name = anomaly["metric_name"].replace("_", " ")

    if pct is not None and not (isinstance(pct, float) and str(pct) == "nan"):
        change = f"{float(pct):+.1%}"
    else:
        change = f"{float(anomaly.get('absolute_change', 0)):+.4g}"

    return (
        f"{metric_name.title()} moved from {previous} to {current} "
        f"({change}) on {anomaly['metric_date']}."
    )


def _fallback_report(anomaly: dict, evidence: dict) -> str:
    summary = _format_anomaly_summary(anomaly)
    bullets: list[str] = []

    tx = evidence.get("transaction_context", {})
    failures = tx.get("failure_breakdown", [])
    if failures:
        top = failures[0]
        bullets.append(
            f"Top failure pattern: {top.get('failure_reason')} via "
            f"{top.get('payment_method')} ({top.get('failed_count')} failures)."
        )

    plan_rows = evidence.get("plan_context", {}).get("plan_performance", [])
    if plan_rows:
        worst = max(
            plan_rows,
            key=lambda row: row.get("transaction_failure_rate") or 0,
            default=None,
        )
        if worst and worst.get("transaction_failure_rate"):
            bullets.append(
                f"Highest plan failure rate: {worst.get('plan_id')} "
                f"at {float(worst['transaction_failure_rate']):.1%}."
            )

    revenue = evidence.get("revenue_context", {})
    if revenue.get("plan_performance"):
        bullets.append("Plan-level MRR and subscription counts were pulled for the anomaly date.")

    churn = evidence.get("churn_context", {})
    if churn.get("churn_trend"):
        latest = churn["churn_trend"][-1]
        bullets.append(
            f"Daily churn rate on anomaly date: {float(latest.get('daily_churn_rate', 0)):.2%}."
        )

    engagement = evidence.get("engagement_context", {})
    if engagement.get("engagement_trend"):
        latest = engagement["engagement_trend"][-1]
        bullets.append(
            f"Daily active users: {latest.get('daily_active_users')} "
            f"with {latest.get('events_per_active_user'):.2f} events per active user."
        )

    if not bullets:
        bullets.append("Supporting mart queries were run, but no strong pattern emerged in the evidence.")

    return f"""# AutoAnalyst Investigation Report

## Anomaly Summary
{summary}

Severity: **{anomaly.get('severity', 'unknown')}** · Category: **{anomaly.get('metric_category')}**

## Likely Root Cause
Based on the available evidence, the anomaly appears linked to the patterns below. 
Set `OPENAI_API_KEY` for a full LLM-written root-cause analysis.

## Supporting Evidence
{chr(10).join(f"- {item}" for item in bullets)}

## Recommended Next Steps
- Review the underlying operational tables for {anomaly['metric_date']}.
- Monitor the metric on the following day for persistence.
- Re-run this investigation after the daily pipeline refresh.
"""


def generate_report(anomaly: dict, evidence: dict, investigation_type: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_report(anomaly, evidence)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    user_prompt = f"""
{prompts.INVESTIGATION_PROMPTS[investigation_type]}

Anomaly record:
{json.dumps(anomaly, indent=2, default=str)}

Evidence:
{json.dumps(evidence, indent=2, default=str)}
""".strip()

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or _fallback_report(anomaly, evidence)


def run_investigation(metric_date: str | None = None) -> dict:
    """
    Run the full investigation workflow.

    Returns metadata about the anomaly and saved report path.
    """
    anomaly = tools.get_top_anomaly(metric_date)
    if anomaly is None:
        print("No anomalies flagged for investigation, skipping...")
        return None

    report_path = report_path_for(anomaly)
    if report_path.is_file():
        print(f"Report already exists: {report_path.name}, skipping...")
        return None

    investigation_type = classify_anomaly(anomaly)
    evidence = collect_evidence(investigation_type, anomaly)
    report_text = generate_report(anomaly, evidence, investigation_type)
    save_report(anomaly, report_text)
    print(f"Investigation saved to {report_path}")
    return {
        "anomaly": anomaly,
        "investigation_type": investigation_type,
        "report_path": str(report_path),
    }


if __name__ == "__main__":
    run_investigation(date.today().isoformat())

