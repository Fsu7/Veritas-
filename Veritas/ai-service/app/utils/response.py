"""统一响应包装器 — task24 产出

提供 ok() / fail() / fail_response() / now_ts_ms() 工厂函数。
所有 endpoint 的 success 路径必须用 ok() 包装返回，确保响应根级
恒含 {code, message, data, timestamp} 4 个字段。
"""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi.responses import JSONResponse


def now_ts_ms() -> int:
    """返回当前 UTC 毫秒时间戳（与 Java 端 System.currentTimeMillis() 一致）"""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def ok(data: Any = None, message: str = "success", code: int = 200) -> Dict[str, Any]:
    """成功响应包装

    Args:
        data: 业务数据（dict / list / 标量），Pydantic 模型需在 endpoint 内 model_dump(by_alias=True)
        message: 人类可读消息
        code: 业务状态码（HTTP 状态码由 FastAPI status_code 决定）

    Returns:
        符合 Java 端 ApiResponse<T> 反序列化约定的字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": now_ts_ms(),
    }


def fail(message: str, code: int = 500, data: Any = None) -> Dict[str, Any]:
    """业务失败响应包装

    Args:
        message: 错误描述（中文友好）
        code: 业务状态码
        data: 可选附加信息（如校验错误详情）
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": now_ts_ms(),
    }


def fail_response(message: str, code: int = 500, data: Any = None) -> JSONResponse:
    """返回带正确 HTTP 状态码的失败响应

    与 fail() 不同，此函数返回 JSONResponse 且 HTTP 状态码与业务码一致，
    Java 端 WebClient 可根据 HTTP 状态码判断请求是否成功。
    适用于 endpoint 中直接 return 的错误路径。
    """
    return JSONResponse(status_code=code, content=fail(message=message, code=code, data=data))
