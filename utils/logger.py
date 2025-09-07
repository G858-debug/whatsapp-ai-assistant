"""Logging utilities for Refiloe"""
import logging
import sys
from datetime import datetime
import pytz

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def setup_logger(name='refiloe'):
    """Setup and return a logger instance"""
    return logging.getLogger(name)

def log_info(message, **kwargs):
    """Log info message"""
    logger = logging.getLogger('refiloe')
    logger.info(message, **kwargs)

def log_error(message, exc_info=False, **kwargs):
    """Log error message"""
    logger = logging.getLogger('refiloe')
    logger.error(message, exc_info=exc_info, **kwargs)

def log_warning(message, **kwargs):
    """Log warning message"""
    logger = logging.getLogger('refiloe')
    logger.warning(message, **kwargs)

def log_debug(message, **kwargs):
    """Log debug message"""
    logger = logging.getLogger('refiloe')
    logger.debug(message, **kwargs)