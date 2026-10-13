import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_auth_and_rbac_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Suffix for unique emails per test run
        suffix = uuid.uuid4().hex[:8]

        # 1. TEST: Unauthenticated request must return 401
        res = await client.get("/api/v1/collections")
        assert res.status_code == 401
        assert "detail" in res.json()

        # 2. TEST: Invalid token must return 401
        res = await client.get(
            "/api/v1/collections",
            headers={"Authorization": "Bearer invalid.token.value"}
        )
        assert res.status_code == 401

        # 3. TEST: Register Admin and Login
        admin_email = f"admin_{suffix}@tenanta.com"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "strongpassword123",
                "role": "admin",
                "tenant_name": f"TenantA_{suffix}",
            },
        )
        assert reg_res.status_code == 201
        admin_data = reg_res.json()
        assert admin_data["role"] == "admin"

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "strongpassword123"},
        )
        assert login_res.status_code == 200
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Verify /auth/me
        me_res = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == admin_email

        # 4. TEST: Register Viewer in same tenant
        viewer_email = f"viewer_{suffix}@tenanta.com"
        reg_v_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": viewer_email,
                "password": "viewerpassword123",
                "role": "viewer",
                "tenant_name": f"TenantA_{suffix}",
            },
        )
        assert reg_v_res.status_code == 201

        login_v_res = await client.post(
            "/api/v1/auth/login",
            json={"email": viewer_email, "password": "viewerpassword123"},
        )
        assert login_v_res.status_code == 200
        viewer_token = login_v_res.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # 5. TEST: Viewer attempts admin operation -> 403 Forbidden!
        forbidden_res = await client.post(
            "/api/v1/collections",
            headers=viewer_headers,
            json={"name": "Hacked Collection"},
        )
        assert forbidden_res.status_code == 403
        assert "Operation not permitted" in forbidden_res.json()["detail"]

        # 6. TEST: Admin creates Collection -> 201 Created
        create_col_res = await client.post(
            "/api/v1/collections",
            headers=admin_headers,
            json={"name": f"Engineering Docs {suffix}"},
        )
        assert create_col_res.status_code == 201
        col_id = create_col_res.json()["id"]

        # 7. TEST: Viewer in same tenant lists collections -> sees it
        list_res = await client.get("/api/v1/collections", headers=viewer_headers)
        assert list_res.status_code == 200
        col_names = [c["name"] for c in list_res.json()]
        assert f"Engineering Docs {suffix}" in col_names

        # 8. TEST: Tenant B cannot see Tenant A's collections (Isolation)
        tenant_b_email = f"admin_{suffix}@tenantb.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": tenant_b_email,
                "password": "password123",
                "role": "admin",
                "tenant_name": f"TenantB_{suffix}",
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": tenant_b_email, "password": "password123"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        list_b_res = await client.get("/api/v1/collections", headers=headers_b)
        assert list_b_res.status_code == 200
        col_names_b = [c["name"] for c in list_b_res.json()]
        assert f"Engineering Docs {suffix}" not in col_names_b
