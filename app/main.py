import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.collections import router as collections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.analytics import router as analytics_router
from app.ui.dashboard_html import DASHBOARD_HTML
from app.workers.worker import run_ingestion_worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(run_ingestion_worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="EKIP - Enterprise Knowledge Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
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
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")

    # Interactive Web Dashboard
    @app.get("/", response_class=HTMLResponse, tags=["Dashboard"], include_in_schema=False)
    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def serve_dashboard():
        return HTMLResponse(content=DASHBOARD_HTML)

    return app


app = create_app()