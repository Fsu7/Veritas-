from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.router import api_router
from app.core import events
from app.core.config import settings
from app.exception import AIServiceException


@asynccontextmanager
async def lifespan(app: FastAPI):
    await events.on_startup()
    yield
    await events.on_shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm": events.llm_service.status if events.llm_service else "not_loaded",
        "embedding": events.embedding_service.status if events.embedding_service else "not_loaded",
        "chroma": events.vector_store_service.status if events.vector_store_service else "not_connected",
        "prompts": events.prompt_manager.status if events.prompt_manager else "not_loaded",
    }


@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": f"参数校验失败: {exc}",
            "data": None,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        },
    )
