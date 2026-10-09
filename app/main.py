from uuid import uuid4
from fastapi import FastAPI,Request

from app.api.v1.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="EKIP",
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

    app.include_router(
        health_router,
        prefix="/api/v1",
    )

    return app


app = create_app()
        