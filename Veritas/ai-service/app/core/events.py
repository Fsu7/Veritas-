from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging

embedding_service = None
vector_store_service = None
llm_service = None
prompt_manager = None


async def on_startup() -> None:
    global embedding_service, vector_store_service, llm_service, prompt_manager

    setup_logging(settings.LOG_LEVEL)

    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"LLM_MODE={settings.LLM_MODE}")
    logger.info(f"EMBEDDING_MODEL_PATH={settings.EMBEDDING_MODEL_PATH}")
    logger.info(f"EMBEDDING_DEVICE={settings.EMBEDDING_DEVICE}")
    logger.info(f"CHROMA_PATH={settings.CHROMA_PATH}")
    logger.info(f"DEBUG={settings.DEBUG}")
    logger.info(f"AGENT_TIMEOUT={settings.AGENT_TIMEOUT}s, AGENT_FULL_TIMEOUT={settings.AGENT_FULL_TIMEOUT}s")

    from app.services.embedding_service import EmbeddingService

    embedding_service = EmbeddingService(settings)
    try:
        await embedding_service.load_model()
    except Exception as e:
        logger.error(f"EmbeddingService load_model failed: {e}")

    from app.services.vector_store_service import VectorStoreService

    vector_store_service = VectorStoreService(settings)
    try:
        await vector_store_service.initialize()
    except Exception as e:
        logger.error(f"VectorStoreService initialize failed: {e}")

    from app.services.llm_service import LLMService

    llm_service = LLMService(settings)
    try:
        await llm_service.initialize()
    except Exception as e:
        logger.error(f"LLMService initialize failed: {e}")

    from app.services.prompt_manager import PromptManager

    prompt_manager = PromptManager()
    try:
        await prompt_manager.load_templates()
    except Exception as e:
        logger.error(f"PromptManager load_templates failed: {e}")

    logger.info("AI Service started successfully")


async def on_shutdown() -> None:
    global embedding_service, vector_store_service, llm_service

    if llm_service is not None:
        try:
            await llm_service.unload_model()
        except Exception as e:
            logger.error(f"LLMService unload_model failed: {e}")

    if vector_store_service is not None:
        try:
            await vector_store_service.close()
        except Exception as e:
            logger.error(f"VectorStoreService close failed: {e}")

    if embedding_service is not None:
        logger.info("Releasing embedding service resources")

    logger.info("AI Service shut down")
