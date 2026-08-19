import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Register all models with Base.metadata
from app.models.user import User, UserRole
from app.auth.security import get_password_hash, create_access_token
from app.db.session import Base, get_db
from app.main import app

# Shared in-memory SQLite database engine across all test files
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Globally override get_db dependency for TestClient
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_db_rows_between_tests():
    yield
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def unauthenticated_client():
    """Unauthenticated TestClient for testing auth rejection."""
    return TestClient(app)


@pytest.fixture
def client(test_db):
    """
    Authenticated TestClient pre-configured with a valid Bearer JWT token header.
    Ensures all existing phase tests pass seamlessly against protected endpoints.
    """
    test_user = User(
        username="test_investigator",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.INVESTIGATOR,
    )
    test_db.add(test_user)
    test_db.commit()

    token = create_access_token(data={"sub": "test_investigator", "role": "INVESTIGATOR"})
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


@pytest.fixture
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
