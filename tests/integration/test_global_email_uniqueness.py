import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_global_email_uniqueness_and_login_unambiguity():
    """
    Test that email is globally unique across all tenants:
    1. A user registering an email in Tenant A prevents that same email
       from being registered in Tenant B (either via new tenant or invite).
    2. Attempting duplicate registration returns 409 Conflict.
    3. Login by email always resolves unambiguously to the unique account.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        shared_email = f"shared_{suffix}@domain.com"

        # 1. Register user in Tenant 1
        reg1 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": shared_email,
                "password": "password123",
                "tenant_name": f"Tenant_Alpha_{suffix}",
            },
        )
        assert reg1.status_code == 201
        user1_data = reg1.json()
        assert user1_data["email"] == shared_email

        # 2. Attempt to register same email as a new tenant creator -> 409 Conflict
        reg2 = await client.post(
            "/api/v1/auth/register",
            json={
                "email": shared_email,
                "password": "differentpassword",
                "tenant_name": f"Tenant_Beta_{suffix}",
            },
        )
        assert reg2.status_code == 409
        assert "already exists" in reg2.json()["detail"].lower()

        # 3. Create Tenant Beta with another admin and invite shared_email
        beta_admin_email = f"beta_admin_{suffix}@domain.com"
        reg_beta_admin = await client.post(
            "/api/v1/auth/register",
            json={
                "email": beta_admin_email,
                "password": "password123",
                "tenant_name": f"Tenant_Beta_{suffix}",
            },
        )
        assert reg_beta_admin.status_code == 201

        login_beta = await client.post(
            "/api/v1/auth/login",
            json={"email": beta_admin_email, "password": "password123"},
        )
        beta_token = login_beta.json()["access_token"]

        invite_res = await client.post(
            "/api/v1/auth/invite",
            headers={"Authorization": f"Bearer {beta_token}"},
            json={"role": "viewer", "expires_hours": 24},
        )
        assert invite_res.status_code == 201
        invite_token = invite_res.json()["invite_token"]

        # Attempt to register with invite using already registered email -> 409 Conflict
        reg_invite_dup = await client.post(
            "/api/v1/auth/register",
            json={
                "email": shared_email,
                "password": "password123",
                "invite_token": invite_token,
            },
        )
        assert reg_invite_dup.status_code == 409
        assert "already exists" in reg_invite_dup.json()["detail"].lower()

        # 4. Login by email is completely unambiguous and resolves to user1
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": shared_email, "password": "password123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["id"] == user1_data["id"]
        assert me_res.json()["tenant_id"] == user1_data["tenant_id"]
