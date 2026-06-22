import pandas as pd
import random
from datetime import datetime
from faker import Faker

from id_utils import next_prefixed_id, next_daily_id

fake = Faker()


# Daily row volume tuning: (probability per attempt, number of attempts).
# Higher values simulate a growing SaaS with meaningful daily activity.
DAILY_VOLUME = {
    "accounts": (0.14, 8),
    "users": (0.20, 10),
    "subscriptions": (0.12, 6),
    "product_events": (0.42, 120),
    "transactions": (0.32, 60),
}

# Match generate_historical_backfill.py start date for time-based volume ramps.
BACKFILL_START = datetime(2022, 1, 1)
TRANSACTION_GROWTH_RAMP_DAYS = 1460
TRANSACTION_MAX_GROWTH_MULTIPLIER = 2.5

# Per-active-subscription daily cancellation probability (~3-5% monthly churn).
DAILY_CHURN_PROBABILITY = 0.0035

CANCEL_REASONS = [
    "too_expensive",
    "low_usage",
    "missing_features",
    "support_issue",
    "payment_issue",
    "switched_provider",
    "business_closed",
]
CANCEL_REASON_WEIGHTS = [22, 28, 18, 12, 10, 7, 3]


# Define schemas so empty outputs still behave like normal tables.
ACCOUNT_COLUMNS = [
    "account_id",
    "account_name",
    "industry",
    "company_size",
    "region",
    "signup_date",
    "acquisition_channel",
    "account_status",
    "created_at",
    "updated_at",
    "batch_date",
]

USER_COLUMNS = [
    "user_id",
    "account_id",
    "first_name",
    "last_name",
    "email",
    "role",
    "user_status",
    "device_preference",
    "notification_preference",
    "onboarding_completed",
    "created_at",
    "last_login_at",
    "user_timezone",
    "batch_date",
]

SUBSCRIPTION_COLUMNS = [
    "subscription_id",
    "account_id",
    "plan_id",
    "monthly_price",
    "billing_period",
    "subscription_status",
    "trial_started_at",
    "trial_ended_at",
    "started_at",
    "cancelled_at",
    "cancel_reason",
    "payment_method",
    "auto_renew",
    "discount_percent",
    "sales_assisted",
    "updated_at",
    "batch_date",
]

PRODUCT_EVENT_COLUMNS = [
    "event_id",
    "user_id",
    "session_id",
    "feature_id",
    "event_name",
    "event_timestamp",
    "device_type",
    "event_status",
    "failure_reason",
    "batch_date",
]

TRANSACTION_COLUMNS = [
    "transaction_id",
    "user_id",
    "transaction_timestamp",
    "transaction_amount",
    "transaction_status",
    "payment_method",
    "service_category",
    "customer_type",
    "failure_reason",
    "refund_reason",
    "batch_date",
]

FEATURE_COLUMNS = [
    "feature_id",
    "feature_name",
    "feature_category",
    "minimum_plan",
    "is_core_feature",
    "feature_status",
    "released_at",
    "adoption_difficulty",
    "retention_impact",
    "batch_date",
]


# Keep features mostly static so events reference a stable product catalog.
FEATURE_CATALOG = [
    ("login", "core", "starter", True, "low", "medium"),
    ("create_invoice", "billing", "starter", True, "low", "high"),
    ("send_payment_reminder", "billing", "starter", True, "low", "medium"),
    ("process_payment", "payments", "starter", True, "medium", "high"),
    ("book_service", "scheduling", "starter", True, "medium", "medium"),
    ("view_customer_history", "crm", "starter", True, "low", "medium"),
    ("automated_followup", "automation", "pro", False, "medium", "high"),
    ("export_report", "reporting", "pro", False, "medium", "medium"),
    ("advanced_reporting", "reporting", "business", False, "high", "high"),
    ("team_task_assignment", "operations", "pro", False, "medium", "medium"),
    ("client_portal", "crm", "pro", False, "medium", "high"),
    ("recurring_invoice", "billing", "pro", False, "medium", "high"),
    ("contract_template", "operations", "business", False, "high", "medium"),
    ("tax_summary", "reporting", "business", False, "high", "medium"),
    ("integration_settings", "integrations", "business", False, "high", "high"),
]


def empty_df(columns: list[str]) -> pd.DataFrame:
    # Return empty DataFrames instead of None so concat/to_csv always work.
    return pd.DataFrame(columns=columns)


def row_count(probability: float, attempts: int) -> int:
    # Each attempt is an independent Bernoulli trial; total rows = number of successes.
    return sum(1 for _ in range(attempts) if random.random() < probability)


def transaction_growth_multiplier(date: datetime) -> float:
    # Ramp transaction probability from 1.0x at backfill start to max over ~4 years.
    days_elapsed = max(0, (date - BACKFILL_START).days)
    progress = min(1.0, days_elapsed / TRANSACTION_GROWTH_RAMP_DAYS)
    return 1.0 + (TRANSACTION_MAX_GROWTH_MULTIPLIER - 1.0) * progress


def pick_existing(df: pd.DataFrame, col: str):
    # Pick an existing parent ID so child records do not create orphan keys.
    values = df[col].dropna().tolist()

    if not values:
        raise ValueError(f"No existing values found for column: {col}")

    return random.choice(values)


def generate_accounts(date: datetime, id_state: dict) -> pd.DataFrame:
    # Generate new accounts for the day.
    probability, attempts = DAILY_VOLUME["accounts"]
    count = row_count(probability, attempts)

    if count == 0:
        return empty_df(ACCOUNT_COLUMNS)

    rows = []

    for _ in range(count):
        rows.append({
            "account_id": next_prefixed_id(id_state, "account", "acct_"),
            "account_name": fake.company(),
            "industry": random.choices(
                ["consulting", "wellness", "cleaning", "auto_repair"],
                weights=[40, 25, 20, 15]
            )[0],
            "company_size": random.choices(
                ["solo", "small", "mid_market"],
                weights=[45, 40, 15]
            )[0],
            "region": random.choices(
                ["CA", "TX", "NY", "FL", "WA"],
                weights=[35, 18, 16, 16, 15]
            )[0],
            "signup_date": date.date(),
            "acquisition_channel": random.choices(
                ["organic", "paid_search", "referral", "social", "partner"],
                weights=[38, 22, 18, 12, 10]
            )[0],
            "account_status": random.choices(
                ["active", "inactive", "churned"],
                weights=[91, 6, 3]
            )[0],
            "created_at": date,
            "updated_at": date,
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=ACCOUNT_COLUMNS)


def generate_users(date: datetime, accounts: pd.DataFrame, id_state: dict) -> pd.DataFrame:
    # Generate new users attached to existing or newly created accounts.
    if accounts.empty:
        return empty_df(USER_COLUMNS)

    probability, attempts = DAILY_VOLUME["users"]
    count = row_count(probability, attempts)

    if count == 0:
        return empty_df(USER_COLUMNS)

    rows = []

    for _ in range(count):
        rows.append({
            "user_id": next_prefixed_id(id_state, "user", "usr_"),
            "account_id": pick_existing(accounts, "account_id"),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "role": random.choices(
                ["owner", "admin", "staff", "billing_manager", "operations_manager"],
                weights=[22, 24, 34, 10, 10]
            )[0],
            "user_status": random.choices(
                ["active", "invited", "deactivated"],
                weights=[93, 5, 2]
            )[0],
            "device_preference": random.choices(
                ["desktop", "mobile", "tablet", "mixed"],
                weights=[52, 28, 5, 15]
            )[0],
            "notification_preference": random.choices(
                ["email", "sms", "in_app", "none"],
                weights=[50, 22, 23, 5]
            )[0],
            "onboarding_completed": random.choices(
                [True, False],
                weights=[84, 16]
            )[0],
            "created_at": date,
            "last_login_at": random.choices(
                [date, None],
                weights=[91, 9]
            )[0],
            "user_timezone": random.choices(
                [
                    "America/Los_Angeles",
                    "America/Chicago",
                    "America/New_York",
                    "America/Denver",
                    "America/Phoenix",
                ],
                weights=[32, 22, 26, 10, 10]
            )[0],
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=USER_COLUMNS)


def generate_subscriptions(
    date: datetime,
    accounts: pd.DataFrame,
    id_state: dict,
) -> pd.DataFrame:
    # Generate account-level subscription records.
    if accounts.empty:
        return empty_df(SUBSCRIPTION_COLUMNS)

    probability, attempts = DAILY_VOLUME["subscriptions"]
    count = row_count(probability, attempts)

    if count == 0:
        return empty_df(SUBSCRIPTION_COLUMNS)

    rows = []

    for _ in range(count):
        plan_id = random.choices(
            ["starter", "pro", "business"],
            weights=[42, 44, 14]
        )[0]

        subscription_status = random.choices(
            ["trialing", "active", "past_due", "cancelled"],
            weights=[6, 88, 3, 3]
        )[0]

        cancelled = subscription_status == "cancelled"

        rows.append({
            "subscription_id": next_prefixed_id(id_state, "subscription", "sub_"),
            "account_id": pick_existing(accounts, "account_id"),
            "plan_id": plan_id,
            "monthly_price": {"starter": 29, "pro": 79, "business": 199}[plan_id],
            "billing_period": random.choices(
                ["monthly", "annual"],
                weights=[78, 22]
            )[0],
            "subscription_status": subscription_status,
            "trial_started_at": random.choices(
                [date, None],
                weights=[70, 30]
            )[0],
            "trial_ended_at": random.choices(
                [date, None],
                weights=[65, 35]
            )[0],
            "started_at": date,
            "cancelled_at": date if cancelled else None,
            "cancel_reason": random.choices(
                [
                    "too_expensive",
                    "low_usage",
                    "missing_features",
                    "support_issue",
                    "payment_issue",
                    "switched_provider",
                    "business_closed",
                ],
                weights=[22, 28, 18, 12, 10, 7, 3]
            )[0] if cancelled else None,
            "payment_method": random.choices(
                ["card", "ach", "wallet"],
                weights=[72, 22, 6]
            )[0],
            "auto_renew": random.choices(
                [True, False],
                weights=[93, 7]
            )[0],
            "discount_percent": random.choices(
                [0, 10, 15, 20, 30],
                weights=[76, 10, 7, 5, 2]
            )[0],
            "sales_assisted": random.choices(
                [True, False],
                weights=[18, 82]
            )[0],
            "updated_at": date,
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=SUBSCRIPTION_COLUMNS)


def apply_subscription_churn(
    date: datetime,
    subscriptions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Cancel a small share of mature active subscriptions each day.
    if subscriptions.empty:
        return subscriptions, empty_df(SUBSCRIPTION_COLUMNS)

    started_at = pd.to_datetime(subscriptions["started_at"], errors="coerce")

    eligible_mask = (
        subscriptions["cancelled_at"].isna()
        & subscriptions["subscription_status"].isin(["active", "trialing", "past_due"])
        & started_at.dt.date.lt(date.date())
    )

    cancelled_idx = [
        idx
        for idx in subscriptions.index[eligible_mask]
        if random.random() < DAILY_CHURN_PROBABILITY
    ]

    if not cancelled_idx:
        return subscriptions, empty_df(SUBSCRIPTION_COLUMNS)

    for idx in cancelled_idx:
        subscriptions.loc[idx, "subscription_status"] = "cancelled"
        subscriptions.loc[idx, "cancelled_at"] = date
        subscriptions.loc[idx, "cancel_reason"] = random.choices(
            CANCEL_REASONS,
            weights=CANCEL_REASON_WEIGHTS,
        )[0]
        subscriptions.loc[idx, "updated_at"] = date
        subscriptions.loc[idx, "batch_date"] = date.date()

    churn_updates = subscriptions.loc[cancelled_idx].copy()
    return subscriptions, churn_updates


def generate_product_events(
    date: datetime,
    users: pd.DataFrame,
    features: pd.DataFrame,
    id_state: dict,
) -> pd.DataFrame:
    # Generate usage events from existing users and known product features.
    if users.empty or features.empty:
        return empty_df(PRODUCT_EVENT_COLUMNS)

    probability, attempts = DAILY_VOLUME["product_events"]
    count = row_count(probability, attempts)

    if count == 0:
        return empty_df(PRODUCT_EVENT_COLUMNS)

    rows = []

    for _ in range(count):
        event_status = random.choices(
            ["success", "failed"],
            weights=[96, 4]
        )[0]

        selected_feature_id = pick_existing(features, "feature_id")
        selected_feature = features.loc[
            features["feature_id"] == selected_feature_id,
            "feature_name"
        ].iloc[0]

        rows.append({
            "event_id": next_daily_id(id_state, "event", "evt_", date),
            "user_id": pick_existing(users, "user_id"),
            "session_id": next_daily_id(id_state, "session", "ses_", date),
            "feature_id": selected_feature_id,
            "event_name": selected_feature,
            "event_timestamp": date,
            "device_type": random.choices(
                ["desktop", "mobile", "tablet"],
                weights=[58, 35, 7]
            )[0],
            "event_status": event_status,
            "failure_reason": random.choices(
                ["validation_error", "timeout", "permission_denied", "integration_error", "unknown"],
                weights=[35, 25, 15, 15, 10]
            )[0] if event_status == "failed" else None,
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=PRODUCT_EVENT_COLUMNS)


def generate_transactions(
    date: datetime,
    users: pd.DataFrame,
    id_state: dict,
) -> pd.DataFrame:
    # Generate transaction records tied to existing users.
    if users.empty:
        return empty_df(TRANSACTION_COLUMNS)

    probability, attempts = DAILY_VOLUME["transactions"]
    probability = min(1.0, probability * transaction_growth_multiplier(date))
    count = row_count(probability, attempts)

    if count == 0:
        return empty_df(TRANSACTION_COLUMNS)

    rows = []

    for _ in range(count):
        transaction_status = random.choices(
            ["completed", "failed", "refunded", "pending"],
            weights=[92, 5, 2, 1]
        )[0]

        rows.append({
            "transaction_id": next_daily_id(id_state, "transaction", "txn_", date),
            "user_id": pick_existing(users, "user_id"),
            "transaction_timestamp": date,
            "transaction_amount": round(random.lognormvariate(4.2, 0.55), 2),
            "transaction_status": transaction_status,
            "payment_method": random.choices(
                ["card", "ach", "wallet"],
                weights=[74, 20, 6]
            )[0],
            "service_category": random.choices(
                ["invoice", "appointment", "deposit", "consultation", "follow_up", "project_milestone", "subscription"],
                weights=[36, 24, 14, 11, 7, 5, 3]
            )[0],
            "customer_type": random.choices(
                ["returning_customer", "new_customer"],
                weights=[72, 28]
            )[0],
            "failure_reason": random.choices(
                ["card_declined", "insufficient_funds", "expired_card", "processor_error", "fraud_flag", "unknown"],
                weights=[35, 25, 15, 15, 5, 5]
            )[0] if transaction_status == "failed" else None,
            "refund_reason": random.choices(
                ["customer_request", "service_cancelled", "duplicate_charge", "billing_error"],
                weights=[40, 25, 20, 15]
            )[0] if transaction_status == "refunded" else None,
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def generate_features(date: datetime, id_state: dict) -> pd.DataFrame:
    # Generate the static feature catalog once during backfill.
    rows = []

    for (
        feature_name,
        feature_category,
        minimum_plan,
        is_core_feature,
        adoption_difficulty,
        retention_impact,
    ) in FEATURE_CATALOG:

        rows.append({
            "feature_id": next_prefixed_id(id_state, "feature", "feat_"),
            "feature_name": feature_name,
            "feature_category": feature_category,
            "minimum_plan": minimum_plan,
            "is_core_feature": is_core_feature,
            "feature_status": "active",
            "released_at": date,
            "adoption_difficulty": adoption_difficulty,
            "retention_impact": retention_impact,
            "batch_date": date.date(),
        })

    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def generate_daily_data(
    date: datetime,
    existing_accounts: pd.DataFrame,
    existing_users: pd.DataFrame,
    existing_subscriptions: pd.DataFrame,
    features: pd.DataFrame,
    id_state: dict,
) -> dict[str, pd.DataFrame]:
    # Generate only today's incremental rows.
    new_accounts = generate_accounts(date, id_state)

    # Include new accounts so same-day users/subscriptions can attach to them.
    all_accounts = pd.concat(
        [existing_accounts, new_accounts],
        ignore_index=True
    )

    new_users = generate_users(date, all_accounts, id_state)

    # Include new users so same-day events/transactions can attach to them.
    all_users = pd.concat(
        [existing_users, new_users],
        ignore_index=True
    )

    new_subscriptions = generate_subscriptions(date, all_accounts, id_state)

    all_subscriptions = pd.concat(
        [existing_subscriptions, new_subscriptions],
        ignore_index=True,
    )
    _, churn_updates = apply_subscription_churn(date, all_subscriptions)

    subscription_batch = pd.concat(
        [new_subscriptions, churn_updates],
        ignore_index=True,
    )

    product_events = generate_product_events(date, all_users, features, id_state)

    transactions = generate_transactions(date, all_users, id_state)

    return {
        "accounts": new_accounts,
        "users": new_users,
        "subscriptions": subscription_batch,
        "product_events": product_events,
        "transactions": transactions,
    }