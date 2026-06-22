import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_engine: Engine | None = None


def get_database_url() -> str:
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is not set. Copy .env.example to .env and set it.")

    user = os.getenv("POSTGRES_USER", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    dbname = os.getenv("POSTGRES_DB", "autoanalyst")
    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{dbname}"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url())
    return _engine


def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine(), params=params)
