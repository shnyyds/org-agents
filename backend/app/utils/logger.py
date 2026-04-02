import sys
from loguru import logger

# Configuration for loguru logger
def setup_logger():
    """
    Configures the global logger with custom formats and sinks.
    """
    # Remove default handler
    logger.remove()

    # Add standard output handler (for development)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )

    # Add file handler (for production)
    logger.add(
        "logs/public_service_system.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return logger

# Singleton instance
public_service_logger = setup_logger()
