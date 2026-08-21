import logging
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Validate DATABASE_URL configuration before initializing engine
if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Failing fast on database session initialization.")

db_url = settings.DATABASE_URL
connect_args = {}

# Try connecting to configured DATABASE_URL (Postgres or SQLite)
try:
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        # PostgreSQL Engine with pre-ping health check
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        # Test connection immediately
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Successfully connected to PostgreSQL database.")
except Exception as e:
    if not db_url.startswith("sqlite"):
        logger.warning(f"Failed to connect to PostgreSQL database at '{db_url}': {e}. Falling back to local SQLite database.")
        db_url = "sqlite:///./ufdr.db"
        connect_args = {"check_same_thread": False}
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        logger.critical(f"Failed to initialize SQLite database engine: {e}")
        raise RuntimeError(f"Database engine initialization failed: {e}") from e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_schema_up_to_date(target_engine):
    """
    Safely inspects existing SQLite tables and executes ALTER TABLE statements for
    any missing columns added in recent commits (e.g. content_hash on reports).
    """
    if not str(target_engine.url).startswith("sqlite"):
        return
    try:
        inspector = inspect(target_engine)
        if "reports" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("reports")]
            if "content_hash" not in columns:
                with target_engine.begin() as conn:
                    conn.execute(text("ALTER TABLE reports ADD COLUMN content_hash VARCHAR"))
                logger.info("Automatically added missing 'content_hash' column to SQLite reports table.")
    except Exception as ex:
        logger.warning(f"SQLite schema update check warning: {ex}")


def get_db() -> Generator[Session, None, None]:
    """Dependency generator providing a database session for FastAPI handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
