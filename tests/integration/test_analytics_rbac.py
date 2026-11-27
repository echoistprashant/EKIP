import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_analytics_overview_requires_admin_role():
    """
    Test that /api/v1/analytics/overview strictly requires the 'admin' role.
    1. Unauthenticated request -> 401 Unauthorized.
    2. Viewer role -> 403 Forbidden.
    3. Admin role -> 200 OK.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Unauthenticated request -> 401
        unauth_res = await client.get("/api/v1/analytics/overview")
        assert unauth_res.status_code == 401

        # 2. Register Admin for Tenant
        admin_email = f"admin_{suffix}@org.com"
        reg_admin = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "password123",
                "tenant_name": f"AnalyticsOrg_{suffix}",
            },
        )
        assert reg_admin.status_code == 201

        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "password123"},
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 3. Admin creates viewer invite and registers a viewer user
        invite_res = await client.post(
            "/api/v1/auth/invite",
            headers=admin_headers,
            json={"role": "viewer", "expires_hours": 24},
        )
        assert invite_res.status_code == 201
        invite_token = invite_res.json()["invite_token"]

        viewer_email = f"viewer_{suffix}@org.com"
        reg_viewer = await client.post(
            "/api/v1/auth/register",
            json={
                "email": viewer_email,
                "password": "password123",
                "invite_token": invite_token,
            },
        )
        assert reg_viewer.status_code == 201

        viewer_login = await client.post(
            "/api/v1/auth/login",
            json={"email": viewer_email, "password": "password123"},
        )
        viewer_token = viewer_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # 4. Viewer attempts to access analytics overview -> 403 Forbidden!
        viewer_res = await client.get(
            "/api/v1/analytics/overview",
            headers=viewer_headers,
        )
        assert viewer_res.status_code == 403
        assert "Operation not permitted" in viewer_res.json()["detail"]
        assert "admin" in viewer_res.json()["detail"]

        # 5. Admin accesses analytics overview -> 200 OK!
        admin_res = await client.get(
            "/api/v1/analytics/overview",
            headers=admin_headers,
        )
        assert admin_res.status_code == 200
        data = admin_res.json()
        assert "total_queries" in data
        assert "cache_hit_rate" in data
