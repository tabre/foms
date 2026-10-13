"""Data-store connection (Config layer). Only models touch the data store."""
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

DATABASE_URL = (
    f"postgresql+psycopg://{settings.pg_user}:{quote_plus(settings.pg_password)}"
    f"@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
