import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.db import get_engine

engine = get_engine()


def load_csv_to_postgres(csv_path: Path, table_name: str, replace: bool = False):
    """
    Load one CSV into one raw Postgres table.
    Backfill usually replaces the table.
    Daily loads usually append.
    """
    if not csv_path.exists():
        print(f"Skipping missing file: {csv_path}")
        return

    df = pd.read_csv(csv_path)

    if df.empty:
        print(f"Skipping empty file: {csv_path}")
        return

    if_exists = "replace" if replace else "append"

    with engine.begin() as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists=if_exists,
            index=False,
            schema="public",
        )

    print(f"Loaded {len(df)} rows into {table_name} from {csv_path}")




def load_backfill():
    """
    Load all historical CSVs into raw tables.
    This should usually be run once after generating backfill data.
    """
    backfill_dir = PROJECT_ROOT / "raw_data/backfill"

    tables = [
        "accounts",
        "users",
        "subscriptions",
        "features",
        "product_events",
        "transactions",
    ]

    for table in tables:
        csv_path = backfill_dir / f"raw_{table}.csv"
        table_name = f"raw_{table}"

        load_csv_to_postgres(
            csv_path=csv_path,
            table_name=table_name,
            replace=False
        )

def delete_existing_batch(table_name: str, batch_date: str):
    """
    Delete a previously loaded daily batch so reruns do not duplicate rows.
    """
    query = text(f"""
        delete from {table_name}
        where batch_date = :batch_date
    """)

    with engine.begin() as conn:
        conn.execute(query, {"batch_date": batch_date})


def load_daily(run_date: str):
    """
    Load one daily folder into raw tables.
    Example run_date: '2026-06-05'
    """
    daily_dir = PROJECT_ROOT / f"raw_data/daily/{run_date}"

    tables = [
        "accounts",
        "users",
        "subscriptions",
        "product_events",
        "transactions",
    ]

    for table in tables:
        csv_path = daily_dir / f"raw_{table}.csv"
        table_name = f"raw_{table}"

        if csv_path.exists():
            delete_existing_batch(table_name, run_date)

            load_csv_to_postgres(
                csv_path=csv_path,
                table_name=table_name,
                replace=False
            )


if __name__ == "__main__":
    load_daily(str(datetime.now().strftime("%Y-%m-%d")))
    # load_backfill() - use once after generating backfill data