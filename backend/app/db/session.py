import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Validate DATABASE_URL configuration before initializing engine
if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Failing fast on database session initialization.")

connect_args = {}
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        # Configure connection pooling for Postgres
        pool_size=10 if not is_sqlite else 5,
        max_overflow=20 if not is_sqlite else 10,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    logger.critical(f"Failed to initialize SQLAlchemy database engine with URL '{settings.DATABASE_URL}': {e}")
    raise RuntimeError(f"Database engine initialization failed: {e}") from e


def get_db() -> Generator[Session, None, None]:
    """Dependency generator providing a database session for FastAPI handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
