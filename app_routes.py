from flask import request, jsonify
from datetime import datetime
from utils.logger import log_error, log_info, log_warning

def setup_routes(app):
    """Setup application routes"""
    
    @app.route('/')
    def home():
        """Home page"""
        try:
            return jsonify({
                "status": "active", 
                "service": "Refiloe AI Assistant",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            log_error(f"Error in home route: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
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
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500) 
    def server_error(e):
        """Handle 500 errors"""
        log_error(f"Server error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    log_info("Routes setup complete")
