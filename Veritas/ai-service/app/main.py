from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.router import api_router
from app.core.config import settings
from app.core.events import app_state, on_shutdown, on_startup
from app.exception import AIServiceException
from app.utils.response import now_ts_ms, ok


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")


# ===== task26 重构：/health 使用 critical_ok 规则 + 统一包装器 =====

def _build_health_data() -> dict:
    """聚合 6 组件状态（task26 FR-002 要求）"""
    return {
        "llm": app_state.llm_service.status if app_state.llm_service else "not_loaded",
        "embedding": (
            app_state.embedding_service.status
            if app_state.embedding_service
            else "not_loaded"
        ),
        "chroma": (
            app_state.vector_store_service.status
            if app_state.vector_store_service
            else "not_connected"
        ),
        "prompts": (
            app_state.prompt_manager.status if app_state.prompt_manager else "not_loaded"
        ),
        "searchService": "ready" if app_state.search_service else "not_initialized",
        "reranker": "ready" if app_state.reranker else "not_initialized",
    }


def _is_critical_ok(data: dict) -> bool:
    """task26 critical_ok 规则：
    llm.status == 'loaded'
    AND embedding.status in ('loaded', 'loaded_api', 'loaded_local')
    AND chroma.status == 'connected'
    """
    return (
        data["llm"] == "loaded"
        and data["embedding"] in ("loaded", "loaded_api", "loaded_local")
        and data["chroma"] == "connected"
    )


@app.get("/health")
async def health_check():
    """健康检查（task26 升级为 critical_ok 规则 + 统一响应格式）"""
    data = _build_health_data()
    critical_ok = _is_critical_ok(data)
    data["status"] = "UP" if critical_ok else "DEGRADED"

    response = ok(data=data, message="success" if critical_ok else "DEGRADED")
    return JSONResponse(
        status_code=200 if critical_ok else 503,
        content=response,
    )


# ===== task24 FR-007：中文友好的 ValidationError 处理器 =====

def _extract_chinese_field_message(errors: List[dict]) -> str:
    """将 Pydantic 校验错误格式化为中文友好 message"""
    if not errors:
        return "参数校验失败"
    parts = []
    for err in errors:
        loc = err.get("loc", [])
        # loc 元组形如 ("body", "userProfile", "educationLevel")
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else (str(loc[0]) if loc else "未知字段")
        msg = err.get("msg", "校验失败")
        err_type = err.get("type", "")
        if err_type == "missing":
            parts.append(f"{field} 字段必填")
        elif err_type == "string_too_short":
            parts.append(f"{field} 不能为空")
        elif err_type in ("enum", "literal_error"):
            parts.append(f"{field} 取值非法")
        elif err_type.startswith("value_error"):
            parts.append(f"{field} 校验失败")
        else:
            parts.append(f"{field}: {msg}")
    return "参数校验失败: " + "; ".join(parts)


@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": now_ts_ms(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 422 校验错误：返回中文友好 message，根级仍为 {code, message, data, timestamp}"""
    error_list = exc.errors() if hasattr(exc, "errors") else []
    message = _extract_chinese_field_message(error_list)
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": message,
            "data": None,
            "timestamp": now_ts_ms(),
        },
    )
