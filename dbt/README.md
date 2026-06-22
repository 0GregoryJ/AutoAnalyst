# AutoAnalyst dbt

dbt project that transforms raw SaaS operational data into analytics-ready dimensions, facts, and reporting marts for dashboards and the AutoAnalyst agent.

Built for **PostgreSQL** (`autoanalyst` database, `analytics` schema).

**Docker quick start:** from repo root, copy `profiles.yml.example` to `profiles.yml`, set `POSTGRES_PASSWORD` in `.env`, then run `./scripts/bootstrap.sh`.

## Data flow

```
raw_* tables (public)     ← loaded from CSV backfill + daily batches
        ↓
staging (views)           ← cleaned types, naming, deduped subscriptions
        ↓
marts/core (tables)       ← dimensions + facts
        ↓
marts/reporting (tables)  ← daily KPIs, plan performance, anomaly candidates
```

Upstream ingestion lives in `../src/ingestion/`. Run backfill load and daily load **before** `dbt run`.

## Project layout

```
models/
├── sources.yml              # raw_accounts, raw_users, raw_subscriptions, etc.
├── staging/                 # stg_* views
│   ├── stg_accounts.sql
│   ├── stg_users.sql
│   ├── stg_subscriptions.sql
│   ├── stg_features.sql
│   ├── stg_product_events.sql
│   └── stg_transactions.sql
└── marts/
    ├── core/                # dims + facts
    │   ├── dim_accounts.sql
    │   ├── dim_users.sql
    │   ├── dim_plans.sql
    │   ├── dim_features.sql
    │   ├── fact_subs_by_day.sql
    │   ├── fact_product_events.sql
    │   └── fact_transactions.sql
    └── reporting/           # business-facing marts
        ├── mart_mrr.sql
        ├── mart_churn.sql
        ├── mart_user_engagement.sql
        ├── mart_transaction_health.sql
        ├── mart_feature_adoption.sql
        ├── mart_plan_performance.sql
        ├── mart_user_transaction_activity.sql
        ├── mart_daily_kpis.sql          # wide executive snapshot (1 row/day)
        └── mart_anomaly_candidates.sql  # long format for agent investigation
```

Column descriptions and tests are documented in each layer's `schema.yml`.

## Prerequisites

- Python 3.12+ with project venv (from repo root: `pip install -r requirements.txt`)
- dbt Core + `dbt-postgres` adapter
- PostgreSQL running locally with raw tables loaded
- dbt profile `autoanalyst_dbt` — copy `profiles.yml.example` to `profiles.yml` in this directory (or configure `~/.dbt/profiles.yml` for local Postgres on `localhost`)

Example profile:

```yaml
autoanalyst_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: postgres
      password: "{{ env_var('POSTGRES_PASSWORD') }}"
      port: 5432
      dbname: autoanalyst
      schema: analytics
      threads: 4
```

Set `POSTGRES_PASSWORD` in the repo `.env` file.

## Common commands

Run from this directory (`dbt/`):

```bash
# Build all models
dbt run

# Run tests (uniqueness, not_null, relationships, accepted_values)
dbt test

# Build and test
dbt build

# Rebuild a subset
dbt run --select mart_daily_kpis mart_anomaly_candidates

# Generate docs
dbt docs generate && dbt docs serve
```

## Key reporting models

| Model | Grain | Purpose |
|-------|-------|---------|
| `mart_daily_kpis` | 1 row / day | Wide KPI snapshot: MRR, churn, DAU, transactions, features |
| `mart_anomaly_candidates` | 9 rows / day | Long-format metrics with thresholds, severity, `should_investigate` |
| `mart_mrr` | 1 row / day | MRR and active subscriptions by plan |
| `mart_churn` | 1 row / day | Daily cancellations and churn rate |
| `mart_plan_performance` | 1 row / day / plan | Plan-level subscription, usage, and revenue metrics |
| `mart_user_engagement` | 1 row / day | DAU, events per user, failure rates |

## Typical workflow

1. **One-time backfill** (from repo root):
   ```bash
   python src/ingestion/generate_historical_backfill.py
   python src/ingestion/load_raw_tables.py
   ```

2. **Daily incremental**:
   ```bash
   python src/ingestion/generate_daily_batch.py
   python src/ingestion/load_raw_tables.py --daily
   ```

3. **Transform**:
   ```bash
   cd dbt && dbt run && dbt test
   ```

## Notes

- `stg_subscriptions` dedupes to the latest row per `subscription_id` (supports daily cancellation updates).
- `mart_mrr` and `mart_churn` count only subscriptions where `is_active_subscription = true` in `fact_subs_by_day`.
- `mart_anomaly_candidates` unpivots selected KPIs from `mart_daily_kpis` for agent-friendly investigation.
