import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

def safe_handle(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return {
                "success": False,
                "error": f"An error occurred while processing your request: {str(e)}"
            }
    return wrapper