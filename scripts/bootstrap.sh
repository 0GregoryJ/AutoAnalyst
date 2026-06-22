#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "No .env found. Copying from .env.example..."
  cp .env.example .env
  echo ""
  echo "Edit .env and set POSTGRES_PASSWORD, then re-run:"
  echo "  ./scripts/bootstrap.sh"
  exit 1
fi

if [[ ! -f dbt/profiles.yml ]]; then
  echo "Creating dbt/profiles.yml from example..."
  cp dbt/profiles.yml.example dbt/profiles.yml
fi

echo "Building and starting Postgres..."
docker compose up -d --build postgres

echo "Waiting for Postgres..."
until docker compose exec postgres pg_isready -U postgres -d autoanalyst >/dev/null 2>&1; do
  sleep 2
done

run_app() {
  docker compose run --rm --no-deps app "$@"
}

echo "Generating historical backfill CSVs..."
run_app python src/ingestion/generate_historical_backfill.py

echo "Loading raw tables into Postgres..."
run_app python -c "from src.ingestion.load_raw_tables import load_backfill; load_backfill()"

echo "Running dbt models and tests..."
run_app bash -c "cd dbt && dbt run && dbt test"

echo "Starting dashboard..."
docker compose up -d app

echo ""
echo "Bootstrap complete."
echo "  Dashboard:  http://localhost:8501"
echo ""
echo "Optional:"
echo "  Airflow:    docker compose up -d airflow-webserver airflow-scheduler  → http://localhost:8080 (admin / admin)"
echo "  dbt docs:   docker compose up dbt-docs  → http://localhost:8082"
echo "  pgAdmin:    docker compose up -d pgadmin  → http://localhost:5050"
