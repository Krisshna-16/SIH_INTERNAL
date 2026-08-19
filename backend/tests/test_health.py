from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_health_check_endpoint():
    """Test that GET /api/v1/health returns HTTP 200 and expected payload."""
    response = client.get(f"{settings.API_V1_PREFIX}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.APP_NAME
    assert data["env"] == settings.ENV
    assert "timestamp" in data


def test_root_endpoint():
    """Test that GET / returns HTTP 200 and docs pointer."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"
    assert data["health"] == f"{settings.API_V1_PREFIX}/health"
