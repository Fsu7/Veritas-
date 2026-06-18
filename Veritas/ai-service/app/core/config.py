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

    # task47: RRF 融合 k 值（可从环境变量覆盖）
    RRF_K: int = 60
    # task47: Reranker 权重（可从环境变量覆盖）
    RERANKER_WEIGHT_RRF: float = 0.5
    RERANKER_WEIGHT_FIELD: float = 0.3
    RERANKER_WEIGHT_POPULARITY: float = 0.2

    # task51: LLM 流式超时（秒），用于首字节延迟监控
    LLM_STREAM_TIMEOUT: int = 30

    # task53: 外接 Embedding API 多 Provider 配置
    EMBEDDING_PROVIDER: str = "dashscope"  # dashscope / jina / openai
    JINA_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    EMBEDDING_DIMENSION: int = 1024  # 维度校验

    # task54: 检索参数优化（可环境变量覆盖）
    SEARCH_TOP_K: int = 10                  # 范围 [5, 20]
    SEARCH_SIMILARITY_THRESHOLD: float = 0.0  # 范围 [0.0, 0.9]，0.0 不过滤
    CHUNK_SIZE: int = 512                    # 预留（当前论文摘要+标题不分块）

    # task55: 推荐策略权重（可环境变量覆盖）
    RERANK_WEIGHT: float = 0.7        # rerank_score 权重
    RECOMMENDATION_WEIGHT: float = 0.3  # recommendation_score 权重

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
