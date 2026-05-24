import os
import sys

from loguru import logger

LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}"


def setup_logging(level: str = "INFO") -> None:
    """初始化日志配置：控制台彩色输出 + 文件轮转输出

    Args:
        level: 控制台日志级别，默认INFO
    """
    logger.remove()

    logger.add(
        sys.stdout,
        level=level,
        format=LOG_FORMAT,
        colorize=True,
    )

    os.makedirs("logs", exist_ok=True)

    logger.add(
        "logs/ai-service-{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format=LOG_FORMAT,
        rotation="00:00",
        retention="7 days",
        compression="zip",
    )
