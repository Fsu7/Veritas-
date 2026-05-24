class AIServiceException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class LLMException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)


class VectorStoreException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)


class AgentTimeoutException(AIServiceException):
    def __init__(self, message: str, code: int = 408):
        super().__init__(code=code, message=message)


class ModelNotLoadedException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)
