import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.collections import router as collections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.ui.dashboard_html import DASHBOARD_HTML
from app.workers.worker import run_ingestion_worker_loop

# Initialize structured JSON logging
configure_logging()
logger = get_logger(__name__)


def ensure_upload_dir_writable() -> Path:
    """Create the configured upload directory at startup and verify write access."""
    upload_dir = Path(settings.UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        probe_file = upload_dir / f".write_probe_{uuid4().hex}"
        probe_file.write_bytes(b"")
        probe_file.unlink()
    except OSError as exc:
        logger.critical(
            "Upload directory is not writable; startup aborted",
            upload_dir=str(upload_dir.resolve()),
            error=str(exc),
        )
        raise RuntimeError(f"Upload directory '{upload_dir}' is not writable: {exc}") from exc
    return upload_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dir_writable()
    worker_task = None
    if settings.RUN_IN_PROCESS_WORKER:
        worker_task = asyncio.create_task(run_ingestion_worker_loop())
    yield
    if worker_task is not None:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


def create_app() -> FastAPI:
    app = FastAPI(
        title="EKIP - Enterprise Knowledge Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next,
    ):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response = await call_next(request)
        except StarletteHTTPException as exc:
            headers = dict(exc.headers) if exc.headers else {}
            response = JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": exc.detail,
                    "request_id": request_id,
                },
                headers=headers,
            )
        except RequestValidationError as exc:
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": exc.errors(),
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            logger.error(
                "Unhandled server exception",
                request_id=request_id,
                path=str(request.url.path),
                method=request.method,
                exc_info=exc,
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )
        finally:
            structlog.contextvars.clear_contextvars()

        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        headers = dict(exc.headers) if exc.headers else {}
        headers["X-Request-ID"] = request_id
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": request_id,
            },
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        logger.error(
            "Unhandled server exception",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    # Mount v1 routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(collections_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")

    # Static assets (compiled Tailwind CSS)
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Interactive Web Dashboard
    @app.get("/", response_class=HTMLResponse, tags=["Dashboard"], include_in_schema=False)
    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def serve_dashboard():
        return HTMLResponse(content=DASHBOARD_HTML)

    return app


app = create_app()
