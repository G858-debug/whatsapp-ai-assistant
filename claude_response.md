<!-- Model: Sonnet 3.5 -->
<!-- Cost: $0.0023 -->
<!-- Max Tokens: 8000 -->
## ANALYSIS
The app.py file appears well-structured but needs some improvements for better error handling, configuration validation, and shutdown procedures. We should also add health checks and proper signal handling.

## CHANGES NEEDED

### EDIT: app.py

**Change 1:** Add signal handling and improve cleanup
Location: After line 43
```python
# REMOVE (line 43-44):
import atexit
atexit.register(cleanup)

# ADD:
import signal
import atexit

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log_info(f"Received signal {signum}")
    cleanup()
    exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(cleanup)
```

**Change 2:** Add health check route
Location: After line 32
```python
# ADD:
@app.route('/health')
def health_check():
    """Basic health check endpoint"""
    return {
        'status': 'healthy',
        'environment': os.environ.get('ENVIRONMENT', 'production'),
        'version': os.environ.get('APP_VERSION', '1.0.0')
    }
```

**Change 3:** Enhance configuration validation
Location: After line 21
```python
# REMOVE (lines 21-26):
try:
    Config.validate()
    log_info("Configuration validated successfully")
except ValueError as e:
    log_error(f"Configuration error: {str(e)}")
    raise

# ADD:
# Validate critical configurations
try:
    Config.validate()
    log_info("Configuration validated successfully")
    
    # Validate required environment variables
    required_vars = ['WHATSAPP_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
except ValueError as e:
    log_error(f"Configuration error: {str(e)}")
    raise SystemExit(1)
```

**Change 4:** Enhance shutdown procedure
Location: Function cleanup() at line 35
```python
# REMOVE (lines 35-42):
def cleanup():
    """Cleanup resources on shutdown"""
    try:
        scheduler.shutdown()
        log_info("Scheduler shut down successfully")
    except Exception as e:
        log_error(f"Error during cleanup: {str(e)}")

# ADD:
def cleanup():
    """Cleanup resources on shutdown"""
    log_info("Starting cleanup procedure...")
    try:
        # Shutdown scheduler gracefully
        scheduler.shutdown(wait=True)
        log_info("Scheduler shut down successfully")
        
        # Close any open database connections
        if hasattr(app, 'db'):
            app.db.close()
            log_info("Database connections closed")
            
        # Additional cleanup tasks
        log_info("Cleanup completed successfully")
    except Exception as e:
        log_error(f"Error during cleanup: {str(e)}")
        raise
```

## SUMMARY
The changes improve the application's robustness by:
1. Adding proper signal handling for graceful shutdowns
2. Including a health check endpoint for monitoring
3. Enhancing configuration validation with specific environment variable checks
4. Improving the cleanup procedure with more comprehensive resource management

These changes make the application more production-ready and easier to monitor while maintaining its core functionality.