import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_invite_token
from app.main import app


@pytest.mark.asyncio
async def test_cross_tenant_takeover_prevention():
    """
    Test that:
    1. Users cannot register into an existing tenant ('Acme Corp') by name.
    2. Users cannot grant themselves roles (e.g. 'admin') from the client.
    3. Joining a tenant requires a signed invite token from that tenant's admin.
    4. Forged and expired invite tokens are rejected.
    5. Non-admins cannot generate invite tokens.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        tenant_name = f"Acme_Corp_{suffix}"

        # 1. Legitimate admin registers 'Acme Corp'
        admin_email = f"owner_{suffix}@acme.com"
        admin_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "password123",
                "tenant_name": tenant_name,
            },
        )
        assert admin_reg.status_code == 201
        admin_data = admin_reg.json()
        assert admin_data["role"] == "admin"
        tenant_id = uuid.UUID(admin_data["tenant_id"])

        # Login admin
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "password123"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Attacker attempts to register into 'Acme Corp' without invite -> 409 Conflict
        attacker_email = f"attacker_{suffix}@evil.com"
        takeover_attempt = await client.post(
            "/api/v1/auth/register",
            json={
                "email": attacker_email,
                "password": "attackerpassword",
                "tenant_name": tenant_name,
                "role": "admin",  # Attacker attempts to inject role: admin
            },
        )
        assert takeover_attempt.status_code == 409
        assert "already exists" in takeover_attempt.json()["detail"]

        # 3. Legitimate admin creates a 'viewer' invite token
        invite_res = await client.post(
            "/api/v1/auth/invite",
            headers=admin_headers,
            json={"role": "viewer", "expires_hours": 24},
        )
        assert invite_res.status_code == 201
        viewer_invite = invite_res.json()["invite_token"]

        # 4. User registers using viewer invite, but tries to inject role: "admin" -> Role must remain "viewer"
        invited_user_email = f"employee_{suffix}@acme.com"
        reg_with_invite = await client.post(
            "/api/v1/auth/register",
            json={
                "email": invited_user_email,
                "password": "employeepassword",
                "invite_token": viewer_invite,
                "role": "admin",  # Ignored by server
            },
        )
        assert reg_with_invite.status_code == 201
        invited_user_data = reg_with_invite.json()
        assert invited_user_data["role"] == "viewer"
        assert invited_user_data["tenant_id"] == str(tenant_id)

        # 5. Non-admin cannot generate invite tokens -> 403 Forbidden
        user_login = await client.post(
            "/api/v1/auth/login",
            json={"email": invited_user_email, "password": "employeepassword"},
        )
        assert user_login.status_code == 200
        viewer_token = user_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        forbidden_invite = await client.post(
            "/api/v1/auth/invite",
            headers=viewer_headers,
            json={"role": "admin"},
        )
        assert forbidden_invite.status_code == 403

        # 6. Attacker attempts to register with forged invite token -> 400 Bad Request
        forged_attempt = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"forged_{suffix}@evil.com",
                "password": "password123",
                "invite_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            },
        )
        assert forged_attempt.status_code == 400

        # 7. Attacker attempts to register with expired invite token -> 400 Bad Request
        expired_token = create_invite_token(
            tenant_id=tenant_id,
            role="admin",
            expires_delta=timedelta(seconds=-10),  # expired
        )
        expired_attempt = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"expired_{suffix}@evil.com",
                "password": "password123",
                "invite_token": expired_token,
            },
        )
        assert expired_attempt.status_code == 400
