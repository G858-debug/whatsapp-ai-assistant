from flask import request, jsonify, render_template_string, Response, send_file
from datetime import datetime, timedelta
import pytz
from io import BytesIO
from utils.logger import log_error, log_info, log_warning
from config import Config

def setup_routes(app):
    """Setup application routes"""
    
    @app.route('/')
    def home():
        """Home page"""
        return jsonify({
            "status": "active", 
            "service": "Refiloe AI Assistant",
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            app.config['supabase'].table('trainers').select('id').limit(1).execute()
            db_status = "connected"
        except:
            db_status = "error"
        
        return jsonify({
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        })
    
    # Import existing blueprint that we know exists
    try:
        from routes.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        log_info("Dashboard routes registered")
    except ImportError as e:
        log_warning(f"Could not import dashboard routes: {e}")
    
    # Try to import other route modules if they exist
    # Comment these out for now since they don't exist yet
    """
    try:
        from routes.webhook import webhook_routes
        webhook_routes.register_routes(app)
    except ImportError:
        log_warning("Webhook routes module not found")
    
    try:
        from routes.calendar import calendar_routes
        calendar_routes.register_routes(app)
    except ImportError:
        log_warning("Calendar routes module not found")
    
    try:
        from routes.assessment import assessment_routes
        assessment_routes.register_routes(app)
    except ImportError:
        log_warning("Assessment routes module not found")
    
    try:
        from routes.analytics import analytics_routes
        analytics_routes.register_routes(app)
    except ImportError:
        log_warning("Analytics routes module not found")
    
    try:
        from routes.admin import admin_routes
        admin_routes.register_routes(app)
    except ImportError:
        log_warning("Admin routes module not found")
    """
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500) 
    def server_error(e):
        """Handle 500 errors"""
        log_error(f"Server error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
