# AutoAnalyst Dashboard

Streamlit executive dashboard for the synthetic GTech SaaS dataset. Reads from dbt reporting marts in PostgreSQL and surfaces KPIs, revenue trends, engagement, and anomaly signals.

The **Anomalies** page also integrates the **AutoAnalyst agent** (`src/agent/`), which investigates flagged metrics with SQL evidence and saves markdown reports to `reports/investigations/`.

## What it shows

The dashboard visualizes metrics built by the AutoAnalyst pipeline:

- **Revenue** — MRR, active subscriptions, plan mix (starter / pro / business)
- **Engagement** — daily active users, product events
- **Reliability** — churn rate, transaction failure rate
- **Anomalies** — flagged metrics, agent investigations, saved markdown reports
- **About This Data** — origins and limitations of the synthetic GTech dataset

Data comes from dbt marts in the `analytics` schema, not from raw CSVs.

## Project layout

```text
dashboard/
├── README.md
├── app.py                  # Entry point: navigation + page config
├── pages/
│   ├── 1_overview.py       # KPI cards, MRR trend, engagement snapshot
│   ├── 2_revenue.py        # MRR trends and plan breakdown
│   ├── 3_engagement.py     # Product usage and DAU
│   ├── 4_transactions.py   # Transaction volume and failure rate
│   ├── 5_anomalies.py      # Anomaly table, agent button, investigation reports
│   └── 6_about.py          # Synthetic data documentation
├── utils/
│   ├── config.py           # colors, KPI definitions, CSS
│   └── data.py             # mart loaders (via src/utils/db) and date filtering
└── components/
    ├── charts.py           # Plotly chart builders
    └── ui.py               # Sidebar filters, KPI cards, tables, report viewer

Database connection: ../src/utils/db.py (shared with ingestion)
AutoAnalyst agent:     ../src/agent/ (investigation workflow + report writer)
Report output:         ../reports/investigations/*.md
```

## Prerequisites

- Docker: run `./scripts/bootstrap.sh` from repo root (see main [README.md](../README.md))
- Or local Python 3.12+ with project venv (`pip install -r requirements.txt`)
- PostgreSQL with `analytics` marts already built
- Repo `.env` with `POSTGRES_PASSWORD` set
- dbt models run at least once (`cd dbt && dbt run`)
- Optional: `OPENAI_API_KEY` in `.env` for full LLM investigation reports

## Run

**Docker (recommended):**

```bash
docker compose up -d app
# → http://localhost:8501
```

**Local venv:**

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

## AutoAnalyst agent

The dashboard does not embed agent logic directly. The **Anomalies** page calls into `src/agent/` to investigate the top flagged anomaly and display saved reports.


| Agent file             | Role                                                                             |
| ---------------------- | -------------------------------------------------------------------------------- |
| `autoanalyst_agent.py` | Main controller — `run_investigation()`                                          |
| `tools.py`             | SQL evidence from dbt marts (`get_top_anomaly`, `get_transaction_context`, etc.) |
| `prompts.py`           | LLM instructions (evidence-only, no invented causes)                             |
| `report_writer.py`     | Saves/loads `reports/investigations/{date}_{metric_name}.md`                     |


**On the Anomalies page:**

1. **Run investigation** (sidebar) — picks the highest-priority row in `mart_anomaly_candidates` with `should_investigate = true`, routes by category, collects evidence, writes a report
2. **Investigation Reports** (main area) — renders markdown files from `reports/investigations/` for the selected date range

**Outside the dashboard:**

```bash
python src/agent/autoanalyst_agent.py
```

Set `OPENAI_API_KEY` in `.env` for full LLM-written reports. Without it, the agent still saves a structured fallback report from SQL evidence.

Agent workflow:

```text
mart_anomaly_candidates
        ↓
src/agent/autoanalyst_agent.py   ← classify → tools.py → LLM/fallback
        ↓
reports/investigations/*.md
        ↓
components/ui.render_investigation_reports()   ← Anomalies page
```

Full agent docs: [../src/agent/README.md](../src/agent/README.md)

## Pages

Navigation is defined in `app.py` via `st.navigation` with explicit sidebar titles:


| Sidebar title   | File                      | Content                                               |
| --------------- | ------------------------- | ----------------------------------------------------- |
| Overview        | `pages/1_overview.py`     | KPI cards, MRR trend, engagement snapshot             |
| Revenue         | `pages/2_revenue.py`      | MRR trend, MRR by plan                                |
| Engagement      | `pages/3_engagement.py`   | Product events and daily active users                 |
| Transactions    | `pages/4_transactions.py` | Transaction volume and failure rate                   |
| Anomalies       | `pages/5_anomalies.py`    | Anomaly table, agent reports, investigation viewer    |
| About This Data | `pages/6_about.py`        | GTech synthetic data origins, pipeline, limitations   |


`app.py` sets global page config and runs the selected page. It is not a dashboard page itself.

## How it works

```text
PostgreSQL (analytics schema)
        ↓
src/utils/db.py        ← get_engine(), query_df() (shared with ingestion + agent)
        ↓
utils/data.py          ← cached mart loaders (5 min TTL)
        ↓
components/ui.py       ← sidebar filters, tables, investigation report viewer
        ↓
components/charts.py   ← Plotly figures
        ↓
pages/*.py             ← page layout and display
        ↑
app.py                 ← st.navigation wiring

Anomalies page only:
pages/5_anomalies.py → src/agent/autoanalyst_agent.py → reports/investigations/*.md
```

1. `**src/utils/db.py**` loads the repo `.env`, creates a SQLAlchemy engine, and runs SQL into pandas DataFrames via `query_df()`.
2. `**utils/data.py**` calls `query_df()` for three marts (with Streamlit caching):
  - `mart_daily_kpis` — wide daily snapshot (KPI cards, most charts)
  - `mart_mrr` — plan-level MRR columns
  - `mart_anomaly_candidates` — long-format anomaly flags
3. `**utils/config.py**` holds dashboard-only constants (colors, KPI cards, CSS).
4. `**components/ui.render_filters()**` renders sidebar controls and returns filtered DataFrames plus the active date range. Pass `show_anomaly_filters=True` on the Anomalies page only.
5. `**components/charts.py**` builds Plotly figures from those DataFrames.
6. **`pages/5_anomalies.py`** triggers the agent and displays saved reports via `render_investigation_reports()`.

## Sidebar filters

**On every page:**

- **Date range** — defaults to the last 90 days of available data
- **Refresh data** — clears Streamlit cache and reloads from Postgres

**On the Anomalies page only:**

- **Show investigation flags only** — limits the anomaly table to `should_investigate = true`
- **Anomaly categories** — revenue, retention, engagement, reliability
- **Run investigation** — runs the AutoAnalyst agent on the top flagged anomaly

## Typical workflow

1. Run the data pipeline (manual or via Airflow):
  ```bash
   python src/ingestion/generate_daily_batch.py
   python src/ingestion/load_raw_tables.py
   cd dbt && dbt run
  ```
2. Launch the dashboard:
  ```bash
   streamlit run dashboard/app.py
  ```
3. Open **Anomalies**, click **Run investigation**, and review the report below the anomaly table.
4. Use **Refresh data** after a new pipeline run.

## Troubleshooting


| Issue                                      | Fix                                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| "No data in `mart_daily_kpis`"             | Run ingestion and `dbt run` first                                                              |
| Postgres connection error                  | Check repo `.env` `POSTGRES_PASSWORD` (read by `src/utils/db.py`) and that Postgres is running |
| Stale numbers after a pipeline run         | Click **Refresh data** in the sidebar                                                          |
| No investigation reports shown             | Run **Run investigation** on the Anomalies page, or `python src/agent/autoanalyst_agent.py`    |
| Generic agent report (no LLM narrative)    | Set `OPENAI_API_KEY` in `.env`                                                                 |
| Import errors from `components` or `utils` | Run from repo root: `streamlit run dashboard/app.py`                                           |


## Related docs

- AutoAnalyst agent: [../src/agent/README.md](../src/agent/README.md)
- dbt models and marts: [../dbt/README.md](../dbt/README.md)
- Daily pipeline and Airflow: [../airflow/README.md](../airflow/README.md)
- Full project overview: [../README.md](../README.md)

