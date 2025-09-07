"""Logger utility for Refiloe application"""
import logging
import sys
from datetime import datetime

def setup_logger():
    """Setup application logger"""
    logger = logging.getLogger('refiloe')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

def log_info(message):
    """Log info message"""
    logger = logging.getLogger('refiloe')
    logger.info(message)

def log_error(message, exc_info=False):
    """Log error message"""
    logger = logging.getLogger('refiloe')
    logger.error(message, exc_info=exc_info)

def log_warning(message):
    """Log warning message"""
    logger = logging.getLogger('refiloe')
    logger.warning(message)