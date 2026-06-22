from datetime import datetime
import re
import pandas as pd


def init_id_state() -> dict:
    # Track the next available number for each ID type.
    return {
        "account": 1,
        "user": 1,
        "subscription": 1,
        "feature": 1,
        "event": {},
        "transaction": {},
        "session": {},
    }


def next_prefixed_id(state: dict, key: str, prefix: str, width: int = 6) -> str:
    # Generate IDs like acct_000001, usr_000001, sub_000001.
    number = state[key]
    state[key] += 1
    return f"{prefix}{number:0{width}d}"


def next_daily_id(
    state: dict,
    key: str,
    prefix: str,
    date: datetime,
    width: int = 6,
) -> str:
    # Generate high-volume IDs that reset per day, like evt_20260605_000001.
    date_part = date.strftime("%Y%m%d")

    if date_part not in state[key]:
        state[key][date_part] = 1

    number = state[key][date_part]
    state[key][date_part] += 1

    return f"{prefix}{date_part}_{number:0{width}d}"


def get_next_number_from_existing_ids(
    df: pd.DataFrame,
    col: str,
    prefix: str,
) -> int:
    # Find the next available number based on IDs already loaded in Postgres.
    if df.empty or col not in df.columns:
        return 1

    numbers = []

    for value in df[col].dropna().astype(str):
        if value.startswith(prefix):
            match = re.search(r"(\d+)$", value)
            if match:
                numbers.append(int(match.group(1)))

    return max(numbers, default=0) + 1


def init_id_state_from_postgres_tables(
    accounts: pd.DataFrame,
    users: pd.DataFrame,
    subscriptions: pd.DataFrame,
    features: pd.DataFrame,
) -> dict:
    # Initialize daily ID state from existing raw tables.
    state = init_id_state()

    state["account"] = get_next_number_from_existing_ids(
        accounts, "account_id", "acct_"
    )
    state["user"] = get_next_number_from_existing_ids(
        users, "user_id", "usr_"
    )
    state["subscription"] = get_next_number_from_existing_ids(
        subscriptions, "subscription_id", "sub_"
    )
    state["feature"] = get_next_number_from_existing_ids(
        features, "feature_id", "feat_"
    )

    return state