from pathlib import Path
from datetime import datetime

import pandas as pd

from id_utils import init_id_state
from generate_data_utils import (
    generate_accounts,
    generate_users,
    generate_subscriptions,
    generate_product_events,
    generate_transactions,
    generate_features,
    apply_subscription_churn,
    empty_df,
    ACCOUNT_COLUMNS,
    USER_COLUMNS,
    SUBSCRIPTION_COLUMNS,
    PRODUCT_EVENT_COLUMNS,
    TRANSACTION_COLUMNS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Backfill historical data once; Airflow should not schedule this file.
def backfill_historical_data(start_date: datetime):
    output_dir = PROJECT_ROOT / "raw_data/backfill"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Start IDs from the beginning for the historical dataset.
    id_state = init_id_state()

    # Create empty tables with fixed schemas before appending rows.
    accounts = empty_df(ACCOUNT_COLUMNS)
    users = empty_df(USER_COLUMNS)
    subscriptions = empty_df(SUBSCRIPTION_COLUMNS)
    product_events = empty_df(PRODUCT_EVENT_COLUMNS)
    transactions = empty_df(TRANSACTION_COLUMNS)

    # Generate product feature catalog once.
    features = generate_features(start_date, id_state)

    # Simulate one day of business activity at a time.
    for date in pd.date_range(start=start_date, end=datetime.now(), freq="D"):
        date = date.to_pydatetime()

        new_accounts = generate_accounts(date, id_state)

        accounts = pd.concat(
            [accounts, new_accounts],
            ignore_index=True
        )

        new_users = generate_users(date, accounts, id_state)

        users = pd.concat(
            [users, new_users],
            ignore_index=True
        )

        new_subscriptions = generate_subscriptions(date, accounts, id_state)

        subscriptions = pd.concat(
            [subscriptions, new_subscriptions],
            ignore_index=True
        )

        subscriptions, _ = apply_subscription_churn(date, subscriptions)

        new_product_events = generate_product_events(
            date,
            users,
            features,
            id_state
        )

        product_events = pd.concat(
            [product_events, new_product_events],
            ignore_index=True
        )

        new_transactions = generate_transactions(date, users, id_state)

        transactions = pd.concat(
            [transactions, new_transactions],
            ignore_index=True
        )

    # Save one raw CSV per source table.
    tables = {
        "accounts": accounts,
        "users": users,
        "subscriptions": subscriptions,
        "product_events": product_events,
        "transactions": transactions,
        "features": features,
    }

    for table_name, df in tables.items():
        path = output_dir / f"raw_{table_name}.csv"
        df.to_csv(path, index=False)
        print(f"Backfilled {table_name} from {start_date.date()} to {datetime.now().date()}.")


if __name__ == "__main__":
    backfill_historical_data(datetime(2022, 1, 1))