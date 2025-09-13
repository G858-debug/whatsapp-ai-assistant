"""Logging utilities for the application"""
import logging
import sys
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger('refiloe')

def log_info(message: str, **kwargs):
    """Log info message"""
    logger.info(message, extra=kwargs)

def log_error(message: str, exc_info=False, **kwargs):
    """Log error message"""
    logger.error(message, exc_info=exc_info, extra=kwargs)

def log_warning(message: str, **kwargs):
    """Log warning message"""
    logger.warning(message, extra=kwargs)

def log_debug(message: str, **kwargs):
    """Log debug message"""
    logger.debug(message, extra=kwargs)

def setup_logger(name: str = 'refiloe', level: int = logging.INFO):
    """Setup and return a logger instance"""
    log = logging.getLogger(name)
    log.setLevel(level)
    return log