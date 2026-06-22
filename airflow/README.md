# AutoAnalyst Airflow

Orchestrates the daily AutoAnalyst data pipeline: synthetic data generation, Postgres loading, dbt transformations, tests, and anomaly investigation.

## What runs on a schedule

**DAG:** `autoanalyst_daily_pipeline`  
**Schedule:** `0 6 * * *` (06:00 UTC daily)  
**File:** `dags/autoanalyst_daily_pipeline.py`

```text
generate_daily_batch → load_raw_tables → dbt_run → dbt_test → run_investigation
```

| Task | What it does |
|------|----------------|
| `generate_daily_batch` | Writes today's incremental CSVs to `raw_data/daily/{date}/` |
| `load_raw_tables` | Deletes and reloads today's batch into `raw_*` Postgres tables |
| `dbt_run` | Runs `dbt run` to rebuild `analytics` marts |
| `dbt_test` | Runs `dbt test` on models |
| `run_investigation` | Runs the AutoAnalyst agent; writes a report to `reports/investigations/` |

## Run with Docker (recommended)

From the repo root, after `./scripts/bootstrap.sh`:

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

Open **http://localhost:8080** — login `admin` / `admin`.

Trigger a run from the UI or:

```bash
docker compose exec airflow-webserver airflow dags trigger autoanalyst_daily_pipeline
```

Airflow containers use `/app` as the project root and read `POSTGRES_*` from `.env` via `docker-compose.yml`.

## Folder layout

```text
airflow/
├── Dockerfile
├── requirements.txt
├── README.md
├── dags/
│   └── autoanalyst_daily_pipeline.py
├── plugins/          # optional custom operators
└── logs/             # runtime logs (gitignored)
```

Ingestion scripts live in `../src/ingestion/`. dbt project lives in `../dbt/`. Agent lives in `../src/agent/`.

## One-time backfill (manual)

The daily DAG does **not** run historical backfill. Use bootstrap instead:

```bash
./scripts/bootstrap.sh
```

Or manually:

```bash
docker compose run --rm --no-deps app python src/ingestion/generate_historical_backfill.py
docker compose run --rm --no-deps app python -c "from src.ingestion.load_raw_tables import load_backfill; load_backfill()"
docker compose run --rm --no-deps app bash -c "cd dbt && dbt run && dbt test"
```

## Advanced: local Airflow (without Docker)

Airflow and project deps conflict on SQLAlchemy — use separate venvs:

- `airflow/.venv` — Apache Airflow 2.10.4 (SQLAlchemy 1.4)
- `.venv` — ingestion, dbt, dashboard (SQLAlchemy 2.x)

```bash
python3.12 -m venv airflow/.venv
airflow/.venv/bin/pip install "apache-airflow==2.10.4" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
```

Point Airflow at this repo:

```bash
export AIRFLOW_HOME=/path/to/AutoAnalyst/airflow
export AIRFLOW__CORE__DAGS_FOLDER=/path/to/AutoAnalyst/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
```

Initialize and start:

```bash
airflow/.venv/bin/airflow db migrate
airflow/.venv/bin/airflow standalone
```

Copy `dbt/profiles.yml.example` to `dbt/profiles.yml` (or configure `~/.dbt/profiles.yml` for local Postgres on `localhost`).

## Task details

### `generate_daily_batch`
- Idempotent: skips generation if CSVs already exist for today
- Reads current Postgres state for sequential ID continuity
- Output: `raw_data/daily/YYYY-MM-DD/raw_*.csv`

### `load_raw_tables`
- Default `__main__` loads **today's** daily folder
- Deletes existing rows for `batch_date` before append (safe reruns)

### `dbt_run` / `dbt_test`
- Builds and validates staging views, core dims/facts, and reporting marts
- See `dbt/README.md` for model inventory

### `run_investigation`
- Investigates the top-priority anomaly from `mart_anomaly_candidates`
- See `src/agent/README.md`

## Operational notes

- **Retries:** 1 retry, 5-minute delay between attempts
- **Catchup:** disabled — past dates are not backfilled by Airflow
- **Not scheduled:** `generate_historical_backfill.py` (one-time only)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DAG not visible in UI | Confirm containers are up; check `airflow/dags/` is mounted |
| Postgres connection failed | Check `.env` `POSTGRES_PASSWORD` and that Postgres is healthy |
| `dbt` profile not found | Copy `dbt/profiles.yml.example` to `dbt/profiles.yml` |
| Empty daily CSVs | Normal on some days — generators are probabilistic |
| Duplicate daily rows | Rerun `load_raw_tables` — it deletes today's `batch_date` first |
