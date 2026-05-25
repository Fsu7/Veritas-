from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（从环境变量/.env文件读取）"""

    APP_NAME: str = "Literature Assistant AI Service"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CHROMA_PATH: str = "./data/vector_db"

    EMBEDDING_MODEL_PATH: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_EXPECTED_DIMENSION: int = 1024
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE: str = ""
    EMBEDDING_API_MODEL: str = ""

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v4"
    DASHSCOPE_EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    LLM_MODE: str = "api"
    LLM_BUILTIN_URL: str = ""
    LLM_BUILTIN_API_KEY: str = ""
    LLM_BUILTIN_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = ""
    LLM_MODEL_NAME: str = ""
    LLM_LOCAL_MODEL_PATH: str = ""
    LLM_TIMEOUT: int = 30
    LLM_RETRY_COUNT: int = 1
    LLM_RETRY_INTERVAL: int = 3

    AGENT_TIMEOUT: int = 30
    AGENT_FULL_TIMEOUT: int = 120
    AGENT_MAX_REGENERATE: int = 1

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
