"""
Tests for user registration, authentication, role-based access, and root endpoint.
"""

import pytest


class TestAuthentication:
    """Test user registration, login, and auth tokens."""

    def test_root_endpoint(self, test_client):
        """GET / should return 200 with service info and docs."""
        resp = test_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "PharmaFlow"
        assert data["status"] == "online"
        assert "/docs" in data["docs_url"]

    def test_user_registration(self, test_client):
        """Register a new pharmacist user."""
        resp = test_client.post("/api/auth/register", json={
            "username": "jane_pharmacist",
            "email": "jane@pharmacy.local",
            "password": "securepassword123",
            "role": "PHARMACIST",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "jane_pharmacist"
        assert data["user"]["role"] == "PHARMACIST"

    def test_duplicate_username_rejected(self, test_client):
        """Registering existing username should fail with 400."""
        test_client.post("/api/auth/register", json={
            "username": "dup_user",
            "email": "dup1@pharmacy.local",
            "password": "password123",
        })
        resp = test_client.post("/api/auth/register", json={
            "username": "dup_user",
            "email": "dup2@pharmacy.local",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_login_success(self, test_client):
        """Login with valid password returns access token."""
        test_client.post("/api/auth/register", json={
            "username": "alice",
            "email": "alice@pharmacy.local",
            "password": "mypassword123",
            "role": "ADMIN",
        })

        resp = test_client.post("/api/auth/login", json={
            "username": "alice",
            "password": "mypassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["role"] == "ADMIN"

    def test_login_invalid_password(self, test_client):
        """Login with wrong password fails with 401."""
        test_client.post("/api/auth/register", json={
            "username": "bob",
            "email": "bob@pharmacy.local",
            "password": "correctpassword",
        })

        resp = test_client.post("/api/auth/login", json={
            "username": "bob",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Incorrect username or password" in resp.json()["detail"]

    def test_get_me_authenticated(self, test_client):
        """GET /api/auth/me returns current user profile."""
        reg = test_client.post("/api/auth/register", json={
            "username": "charlie",
            "email": "charlie@pharmacy.local",
            "password": "charliepass123",
        })
        token = reg.json()["access_token"]

        resp = test_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "charlie"

    def test_get_me_unauthenticated(self, test_client):
        """GET /api/auth/me without token fails with 401."""
        resp = test_client.get("/api/auth/me")
        assert resp.status_code == 401
