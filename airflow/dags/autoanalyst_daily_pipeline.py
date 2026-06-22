"""
Daily AutoAnalyst pipeline:
  1. Generate today's raw CSV batch
  2. Load daily CSVs into Postgres
  3. Run dbt models
  4. Run dbt tests
  5. Run AutoAnalyst agent investigation
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = Path("/app")
INGESTION_DIR = PROJECT_ROOT / "src" / "ingestion"
AGENT_SCRIPT = PROJECT_ROOT / "src" / "agent" / "autoanalyst_agent.py"
DBT_DIR = PROJECT_ROOT / "dbt"

default_args = {
    "owner": "autoanalyst",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="autoanalyst_daily_pipeline",
    default_args=default_args,
    description="Generate daily raw data, load to Postgres, run dbt, test models, and investigate anomalies",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["autoanalyst", "daily", "dbt"],
) as dag:

    generate_daily_batch = BashOperator(
        task_id="generate_daily_batch",
        bash_command=f"cd {PROJECT_ROOT} && python {INGESTION_DIR / 'generate_daily_batch.py'}",
    )

    load_raw_tables = BashOperator(
        task_id="load_raw_tables",
        bash_command=f"cd {PROJECT_ROOT} && python {INGESTION_DIR / 'load_raw_tables.py'}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

    run_investigation = BashOperator(
        task_id="run_investigation",
        bash_command=f"cd {PROJECT_ROOT} && python {AGENT_SCRIPT}",
    )

    generate_daily_batch >> load_raw_tables >> dbt_run >> dbt_test >> run_investigation