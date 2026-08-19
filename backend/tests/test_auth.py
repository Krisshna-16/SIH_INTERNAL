from unittest.mock import patch
from app.models.user import User, UserRole
from app.auth.security import get_password_hash


# 1. Test Login Success
def test_login_success(unauthenticated_client, test_db):
    user = User(username="auth_user", hashed_password=get_password_hash("secret123"), role=UserRole.INVESTIGATOR)
    test_db.add(user)
    test_db.commit()

    res = unauthenticated_client.post("/api/v1/auth/login", json={"username": "auth_user", "password": "secret123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "auth_user"


# 2. Test Login Invalid Password Generic 401
def test_login_invalid_password(unauthenticated_client, test_db):
    user = User(username="auth_user_2", hashed_password=get_password_hash("correctpass"), role=UserRole.INVESTIGATOR)
    test_db.add(user)
    test_db.commit()

    res = unauthenticated_client.post("/api/v1/auth/login", json={"username": "auth_user_2", "password": "wrongpass"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid username or password."


# 3. Test Protected Endpoint Rejects Unauthenticated Request
def test_protected_endpoint_rejects_unauthenticated(unauthenticated_client):
    res = unauthenticated_client.get("/api/v1/reports")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


# 4. Test Protected Endpoint Accepts Authenticated Request
def test_protected_endpoint_accepts_authenticated(client):
    res = client.get("/api/v1/reports")
    assert res.status_code == 200


# 5. Test Registration Endpoint
def test_registration_flow(unauthenticated_client, test_db):
    res = unauthenticated_client.post("/api/v1/auth/register", json={"username": "new_investigator", "password": "newpassword123"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "new_investigator"
    assert data["role"] == "INVESTIGATOR"
