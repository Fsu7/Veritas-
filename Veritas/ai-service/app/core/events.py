from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging


class AppState:
    embedding_service = None
    vector_store_service = None
    llm_service = None
    prompt_manager = None


app_state = AppState()


async def on_startup() -> None:
    setup_logging(settings.LOG_LEVEL)

    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"LLM_MODE={settings.LLM_MODE}")
    logger.info(f"EMBEDDING_MODEL_PATH={settings.EMBEDDING_MODEL_PATH}")
    logger.info(f"EMBEDDING_DEVICE={settings.EMBEDDING_DEVICE}")
    logger.info(f"CHROMA_PATH={settings.CHROMA_PATH}")
    logger.info(f"DEBUG={settings.DEBUG}")
    logger.info(f"AGENT_TIMEOUT={settings.AGENT_TIMEOUT}s, AGENT_FULL_TIMEOUT={settings.AGENT_FULL_TIMEOUT}s")

    from app.services.embedding_service import EmbeddingService

    app_state.embedding_service = EmbeddingService(settings)
    try:
        await app_state.embedding_service.load_model()
    except Exception as e:
        logger.error(f"EmbeddingService load_model failed: {e}")

    from app.services.vector_store_service import VectorStoreService

    app_state.vector_store_service = VectorStoreService(settings)
    try:
        await app_state.vector_store_service.initialize()
    except Exception as e:
        logger.error(f"VectorStoreService initialize failed: {e}")

    from app.services.llm_service import LLMService

    app_state.llm_service = LLMService(settings)
    try:
        await app_state.llm_service.initialize()
    except Exception as e:
        logger.error(f"LLMService initialize failed: {e}")

    from app.services.prompt_manager import PromptManager

    app_state.prompt_manager = PromptManager()
    try:
        await app_state.prompt_manager.load_templates()
    except Exception as e:
        logger.error(f"PromptManager load_templates failed: {e}")

    logger.info("AI Service started successfully")


async def on_shutdown() -> None:
    if app_state.llm_service is not None:
        try:
            await app_state.llm_service.unload_model()
        except Exception as e:
            logger.error(f"LLMService unload_model failed: {e}")

    if app_state.vector_store_service is not None:
        try:
            await app_state.vector_store_service.close()
        except Exception as e:
            logger.error(f"VectorStoreService close failed: {e}")

    if app_state.embedding_service is not None:
        logger.info("Releasing embedding service resources")

    logger.info("AI Service shut down")
