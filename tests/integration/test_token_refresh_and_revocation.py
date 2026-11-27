import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import decode_access_token
from app.main import app


@pytest.mark.asyncio
async def test_access_token_30_minutes_and_refresh_revocation_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        email = f"tokens_{suffix}@example.com"
        password = "SecurePassword123!"

        # 1. Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "tenant_name": f"TokensTenant_{suffix}",
            },
        )
        assert reg_res.status_code == 201

        # 2. Login: check 30-minute access token and presence of refresh_token
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        assert refresh_token is not None and len(refresh_token) > 20
        assert token_data["expires_in"] == 1800  # 30 minutes in seconds

        # Decode JWT access token to verify claims and 30-min window
        claims = decode_access_token(access_token)
        iat = claims["iat"]
        exp = claims["exp"]
        assert exp - iat == 1800  # Exactly 30 minutes

        # 3. Refresh: exchange refresh token for new access & rotated refresh token
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_res.status_code == 200
        new_token_data = refresh_res.json()
        new_access_token = new_token_data["access_token"]
        new_refresh_token = new_token_data["refresh_token"]

        assert new_access_token != access_token
        assert new_refresh_token != refresh_token
        assert new_token_data["expires_in"] == 1800

        # 4. Old refresh token must be revoked (rotation)
        stale_refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert stale_refresh_res.status_code == 401
        assert "revoked" in stale_refresh_res.json()["detail"].lower()

        # 5. Logout: explicitly revoke new_refresh_token
        logout_res = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": new_refresh_token},
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert logout_res.status_code == 200
        assert logout_res.json()["status"] == "logged_out"

        # 6. Attempting to refresh after logout must be rejected with 401
        post_logout_refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert post_logout_refresh_res.status_code == 401
        assert "revoked" in post_logout_refresh_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_refresh_token_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "non_existent_fake_refresh_token_123"},
        )
        assert res.status_code == 401
        assert "revoked" in res.json()["detail"].lower()
