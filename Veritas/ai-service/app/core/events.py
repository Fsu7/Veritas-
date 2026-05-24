from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging


async def on_startup() -> None:
    """应用启动事件：初始化日志、记录关键配置信息"""
    setup_logging(settings.LOG_LEVEL)

    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"LLM_MODE={settings.LLM_MODE}")
    logger.info(f"EMBEDDING_MODEL_PATH={settings.EMBEDDING_MODEL_PATH}")
    logger.info(f"EMBEDDING_DEVICE={settings.EMBEDDING_DEVICE}")
    logger.info(f"CHROMA_PATH={settings.CHROMA_PATH}")
    logger.info(f"DEBUG={settings.DEBUG}")
    logger.info(f"AGENT_TIMEOUT={settings.AGENT_TIMEOUT}s, AGENT_FULL_TIMEOUT={settings.AGENT_FULL_TIMEOUT}s")
    logger.info(f"AI Service started successfully")


async def on_shutdown() -> None:
    """应用关闭事件：记录关闭日志"""
    logger.info("AI Service shut down")
