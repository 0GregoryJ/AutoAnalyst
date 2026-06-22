import sys
from pathlib import Path
from datetime import datetime

from id_utils import init_id_state_from_postgres_tables
from generate_data_utils import generate_daily_data

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.db import query_df


def generate_daily_batch(date: datetime):
    run_date = date.strftime("%Y-%m-%d")

    output_dir = PROJECT_ROOT / f"raw_data/daily/{run_date}"

    # Make generation idempotent so Airflow reruns do not create different IDs.
    if output_dir.exists() and any(output_dir.glob("*.csv")):
        print(f"Daily files already exist for {run_date}. Reusing existing files.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Pull current state so new rows can reference existing accounts/users/features.
    accounts = query_df("select * from raw_accounts")
    users = query_df("select * from raw_users")
    subscriptions = query_df("select * from raw_subscriptions")
    features = query_df("select * from raw_features")

    # Continue sequential IDs from the current postgres state.
    id_state = init_id_state_from_postgres_tables(
        accounts=accounts,
        users=users,
        subscriptions=subscriptions,
        features=features,
    )

    # Generate only today's incremental source rows.
    tables = generate_daily_data(
        date=date,
        existing_accounts=accounts,
        existing_users=users,
        existing_subscriptions=subscriptions,
        features=features,
        id_state=id_state,
    )

    # Save one CSV per raw table for today's batch.
    for table_name, df in tables.items():
        path = output_dir / f"raw_{table_name}.csv"
        df.to_csv(path, index=False)
        print(f"Generated {table_name} for {run_date}: {len(df)} rows.")


if __name__ == "__main__":
    generate_daily_batch(datetime.now())
