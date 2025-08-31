import logging
import json
import traceback
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import os

class ErrorLogger:
    """Custom error logger for Refiloe"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('refiloe')
        self.logger.setLevel(logging.INFO)
        
        # File handler for all logs
        log_file = self.log_dir / f'refiloe_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Error file handler
        error_file = self.log_dir / 'errors.log'
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        # Error tracking
        self.error_counts = {}
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def log_error(self, message, exc_info=False, context=None):
        """Log an error with context"""
        try:
            error_data = {
                'timestamp': datetime.now(self.sa_tz).isoformat(),
                'message': message,
                'context': context or {}
            }
            
            if exc_info:
                error_data['traceback'] = traceback.format_exc()
            
            # Log to file
            self.logger.error(json.dumps(error_data))
            
            # Track error counts
            today = datetime.now(self.sa_tz).date()
            if today not in self.error_counts:
                self.error_counts[today] = 0
            self.error_counts[today] += 1
            
            # Alert if too many errors
            if self.error_counts[today] > 100:
                self.send_alert(f"High error rate: {self.error_counts[today]} errors today")
                
        except Exception as e:
            # Fallback logging
            print(f"Logger error: {e}")
            self.logger.error(f"Logger failed: {e} - Original error: {message}")
    
    def log_info(self, message, context=None):
        """Log info message"""
        info_data = {
            'timestamp': datetime.now(self.sa_tz).isoformat(),
            'message': message,
            'context': context or {}
        }
        self.logger.info(json.dumps(info_data))
    
    def log_warning(self, message, context=None):
        """Log warning message"""
        warning_data = {
            'timestamp': datetime.now(self.sa_tz).isoformat(),
            'message': message,
            'context': context or {}
        }
        self.logger.warning(json.dumps(warning_data))
    
    def get_recent_errors(self, limit=50):
        """Get recent errors for debugging"""
        errors = []
        error_file = self.log_dir / 'errors.log'
        
        if error_file.exists():
            with open(error_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        # Parse JSON log entry
                        if '{' in line:
                            json_start = line.index('{')
                            error_data = json.loads(line[json_start:])
                            errors.append(error_data)
                    except:
                        # Fallback for non-JSON logs
                        errors.append({'message': line.strip()})
        
        return errors
    
    def get_error_count_today(self):
        """Get today's error count"""
        today = datetime.now(self.sa_tz).date()
        return self.error_counts.get(today, 0)
    
    def get_log_file_path(self):
        """Get path to today's log file"""
        return self.log_dir / f'refiloe_{datetime.now().strftime("%Y%m%d")}.log'
    
    def send_alert(self, message):
        """Send alert for critical errors (implement email/SMS later)"""
        self.logger.critical(f"ALERT: {message}")
        # TODO: Implement email/SMS alerts
    
    def cleanup_old_logs(self, days=30):
        """Remove logs older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for log_file in self.log_dir.glob('refiloe_*.log'):
            try:
                # Extract date from filename
                date_str = log_file.stem.replace('refiloe_', '')
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    self.log_info(f"Deleted old log file: {log_file.name}")
                    
            except Exception as e:
                self.log_warning(f"Could not process log file {log_file}: {e}")
    
    def close(self):
        """Close logger handlers"""
        for handler in self.logger.handlers:
            handler.close()

# Global logger instance
_logger = None

def get_logger():
    """Get or create logger instance"""
    global _logger
    if _logger is None:
        _logger = ErrorLogger()
    return _logger

def setup_logger():
    """Initialize the logger system"""
    global _logger
    if _logger is None:
        _logger = ErrorLogger()
    return _logger

# Convenience functions
def log_error(message, exc_info=False, context=None):
    """Log error message"""
    get_logger().log_error(message, exc_info, context)

def log_info(message, context=None):
    """Log info message"""
    get_logger().log_info(message, context)

def log_warning(message, context=None):
    """Log warning message"""
    get_logger().log_warning(message, context)