# AutoAnalyst Agent

Investigates flagged anomalies from `mart_anomaly_candidates`, pulls supporting evidence from dbt marts, and writes markdown investigation reports.

The agent separates **data retrieval** (Python/SQL tools) from **explanation** (LLM). Reports are saved to `reports/investigations/` and displayed on the dashboard Anomalies page.

## What it does

When an anomaly is flagged for investigation, the agent:

1. Selects the top priority anomaly from `analytics.mart_anomaly_candidates`
2. Routes it by category and metric name (transaction, revenue, churn, engagement)
3. Runs supporting SQL queries against dbt marts and facts
4. Sends the anomaly record + evidence to the LLM (or a rule-based fallback)
5. Saves a markdown report to `reports/investigations/`

Example flow:

```text
transaction_failure_rate anomaly found
        ↓
route to transaction investigation
        ↓
collect transaction evidence (marts + facts)
        ↓
generate report → reports/investigations/2026-06-13_transaction_failure_rate.md
```

## Project layout

```text
src/agent/
├── README.md
├── autoanalyst_agent.py   # Main controller — run_investigation()
├── tools.py               # SQL evidence functions
├── prompts.py             # LLM system and investigation prompts
└── report_writer.py       # Save/load markdown reports
```

Database access goes through `../utils/db.py` (`query_df()`).

## Prerequisites

- Docker: `./scripts/bootstrap.sh` from repo root (see main [README.md](../../README.md))
- Or Python 3.12+ with project venv and `analytics` marts built (`dbt run`)
- Repo `.env` with `POSTGRES_PASSWORD` set
- Optional: `OPENAI_API_KEY` for full LLM-written reports (falls back to rule-based output without it)

Optional env vars:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini   # default if unset
```

## Run

**Docker:**

```bash
docker compose exec app python src/agent/autoanalyst_agent.py
```

**Local venv:**

```bash
source .venv/bin/activate
python src/agent/autoanalyst_agent.py
```

Or programmatically:

```python
from src.agent.autoanalyst_agent import run_investigation

result = run_investigation()
print(result["report_path"])
```

Pass an optional date to investigate a specific day:

```python
run_investigation(metric_date="2026-06-13")
```

## Files and responsibilities

### `autoanalyst_agent.py`

Main entry point. Orchestrates the full workflow:

| Step | Function |
|------|----------|
| Pick anomaly | `tools.get_top_anomaly()` |
| Route | `classify_anomaly()` |
| Gather evidence | `collect_evidence()` |
| Write narrative | `generate_report()` |
| Persist | `report_writer.save_report()` |

Routing rules:

| Anomaly signal | Investigation type |
|----------------|-------------------|
| `reliability` + `transaction_failure_rate` | transaction |
| `reliability` + `event_failure_rate` | engagement |
| `revenue` | revenue |
| `retention` | churn |
| `engagement` | engagement |

### `tools.py`

Plain Python functions that query dbt marts. Returns JSON-serializable evidence dicts.

| Function | Purpose |
|----------|---------|
| `get_top_anomaly()` | Highest-severity row with `should_investigate = true` |
| `get_transaction_context()` | Transaction health, plan performance, failure breakdown, fact summaries |
| `get_revenue_context()` | MRR trend, plan performance, daily KPIs |
| `get_churn_context()` | Churn trend, plan-level cancellations |
| `get_engagement_context()` | User engagement trend, feature adoption |
| `get_plan_context()` | Plan performance snapshot for the anomaly date |

Example tables queried for a transaction anomaly:

- `analytics.mart_transaction_health`
- `analytics.mart_plan_performance`
- `analytics.mart_user_transaction_activity`
- `analytics.fact_transactions`

### `prompts.py`

LLM instructions. Tells the model to use only provided evidence, not invent causes, and output markdown with:

- Anomaly Summary
- Likely Root Cause
- Supporting Evidence
- Recommended Next Steps

### `report_writer.py`

Handles report file I/O:

- Creates `reports/investigations/` if needed
- Filename format: `{date}_{metric_name}.md`
- `list_reports()` / `filter_reports()` / `load_report()` for the dashboard

## Report output

Example path:

```text
reports/investigations/2026-06-13_transaction_failure_rate.md
```

Example structure:

```markdown
# AutoAnalyst Investigation Report

## Anomaly Summary
Transaction failure rate increased from 7% to 24% on 2026-06-12.

## Likely Root Cause
...

## Supporting Evidence
- ...

## Recommended Next Steps
- ...
```

## Dashboard integration

The **Anomalies** page (`dashboard/pages/5_anomalies.py`) calls `run_investigation()` from the sidebar and renders saved reports for the selected date range.

See [../../dashboard/README.md](../../dashboard/README.md).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No module named 'src'` | Run from repo root, or use `python src/agent/autoanalyst_agent.py` (path bootstrap is built in) |
| `No anomalies flagged for investigation` | Run pipeline + `dbt run`; check `mart_anomaly_candidates` |
| Postgres connection error | Check `.env` `POSTGRES_PASSWORD` |
| Generic fallback report only | Set `OPENAI_API_KEY` in `.env` for LLM output |
| OpenAI connection error | Check API key, network, and proxy settings |

## Related docs

- Dashboard and Anomalies page: [../../dashboard/README.md](../../dashboard/README.md)
- dbt marts: [../../dbt/README.md](../../dbt/README.md)
- Database helper: [../utils/db.py](../utils/db.py)
- Full project: [../../README.md](../../README.md)
