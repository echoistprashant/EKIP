import uuid

import pytest
from fastapi import APIRouter, HTTPException
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app_with_test_routes():
    test_app = create_app()
    router = APIRouter(prefix="/api/v1/test-errors")

    @router.get("/http-error")
    async def trigger_http_error():
        raise HTTPException(status_code=403, detail="Custom permission denied error")

    @router.post("/validation-error")
    async def trigger_validation_error(data: dict[str, int]):
        return data

    @router.get("/unhandled-error")
    async def trigger_unhandled_error():
        raise RuntimeError("Unexpected boom in worker")

    test_app.include_router(router)
    return test_app


@pytest.mark.asyncio
async def test_http_exception_returns_json_with_request_id(app_with_test_routes):
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        custom_req_id = f"custom-req-{uuid.uuid4().hex[:8]}"
        res = await client.get(
            "/api/v1/test-errors/http-error",
            headers={"X-Request-ID": custom_req_id},
        )
        assert res.status_code == 403
        data = res.json()
        assert data["detail"] == "Custom permission denied error"
        assert data["request_id"] == custom_req_id
        assert res.headers["X-Request-ID"] == custom_req_id


@pytest.mark.asyncio
async def test_validation_exception_returns_json_with_request_id(app_with_test_routes):
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/test-errors/validation-error",
            json="not a dictionary",
        )
        assert res.status_code == 422
        data = res.json()
        assert "detail" in data
        assert "request_id" in data
        assert uuid.UUID(data["request_id"])
        assert res.headers["X-Request-ID"] == data["request_id"]


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_with_request_id(app_with_test_routes):
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        custom_req_id = f"crash-req-{uuid.uuid4().hex[:8]}"
        res = await client.get(
            "/api/v1/test-errors/unhandled-error",
            headers={"X-Request-ID": custom_req_id},
        )
        assert res.status_code == 500
        data = res.json()
        assert data["detail"] == "Internal server error"
        assert data["request_id"] == custom_req_id
        assert res.headers["X-Request-ID"] == custom_req_id
