"""
Logging Setup - Professional Audit Trail

Why Loguru over print()?
1. Automatic timestamps
2. Log levels (DEBUG, INFO, WARNING, ERROR)
3. File rotation (doesn't fill your disk)
4. Colored output (easier to read)
5. Exception tracking with full traceback

Industry Standard: Logs help debug production issues.
"""

from loguru import logger
import sys
from pathlib import Path


def setup_logger(log_level: str = "INFO"):
    """
    Configure application-wide logging
    
    Output goes to:
    - Console (for development)
    - File (for debugging/audit trail)
    
    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    
    logger.remove()
    
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        "logs/nutritional_arbitrage_{time}.log",
        rotation="10 MB",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )
    
    logger.info(f"Logger initialized at {log_level} level")
    
    return logger
