from uuid import uuid4
from fastapi import FastAPI, Request

from app.api.v1.auth import router as auth_router
from app.api.v1.collections import router as collections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="EKIP - Enterprise Knowledge Intelligence Platform",
        version="0.1.0"
    )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next,
    ):
        request_id = str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    # Mount v1 routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(collections_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")

    return app


app = create_app()