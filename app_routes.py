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

    # Import route modules
    from routes import (
        webhook_routes,
        calendar_routes,
        assessment_routes,
        analytics_routes,
        admin_routes
    )
    
    # Register route modules
    webhook_routes.register_routes(app)
    calendar_routes.register_routes(app)
    assessment_routes.register_routes(app)
    analytics_routes.register_routes(app)
    admin_routes.register_routes(app)
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500) 
    def server_error(e):
        """Handle 500 errors"""
        log_error(f"Server error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500