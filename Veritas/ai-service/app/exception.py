class AIServiceException(Exception):
    """AI 服务基础异常"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class LLMException(AIServiceException):
    """LLM 调用异常"""

    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)


class VectorStoreException(AIServiceException):
    """向量数据库异常"""

    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)


class AgentTimeoutException(AIServiceException):
    """Agent 执行超时"""

    def __init__(self, message: str, code: int = 408):
        super().__init__(code=code, message=message)


class ModelNotLoadedException(AIServiceException):
    """模型未加载"""

    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)


# ===== task24 FR-004 新增异常 =====

class ValidationException(AIServiceException):
    """业务校验异常（语义层面，与 Pydantic 自动校验 422 区分）

    使用场景：
    - 跨字段组合校验（如 paper_ids 数量与 analysisType 联动）
    - 业务前置条件不满足
    """

    def __init__(self, message: str, code: int = 422):
        super().__init__(code=code, message=message)


class RateLimitException(AIServiceException):
    """限流异常"""

    def __init__(self, message: str = "请求过于频繁，请稍后重试", code: int = 429):
        super().__init__(code=code, message=message)
