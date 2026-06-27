import time
from collections import defaultdict, deque
from fastapi import Request

from app.exception import RateLimitException


class RateLimiter:
    """内存滑动窗口速率限制器。

    每个独立 key（通常为客户端 IP）维护一个请求时间戳队列，
    超出窗口的旧时间戳被弹出，仅统计窗口内的请求数。
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        """检查 key 是否仍在限额内。若允许则记录本次请求并返回 True。"""
        now = time.time()
        requests = self._requests[key]
        while requests and requests[0] < now - self.window_seconds:
            requests.popleft()
        if len(requests) >= self.max_requests:
            return False
        requests.append(now)
        return True

    def reset(self) -> None:
        """清空所有限流记录（主要用于测试）。"""
        self._requests.clear()


rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def get_client_id(request: Request) -> str:
    """从 Request 中提取客户端标识（优先取 x-forwarded-for 首段）。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    """便捷封装：检查速率限制，超限则抛出 RateLimitException（由全局异常处理器统一返回 429）。"""
    client_id = get_client_id(request)
    if not rate_limiter.check(client_id):
        raise RateLimitException()
