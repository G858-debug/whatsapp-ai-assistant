#!/usr/bin/env python3
"""
Example integration of Social Media Scheduler with Flask app

This shows how to integrate the social media scheduler into your existing Flask application.
"""

from flask import Flask
from supabase import create_client
from social_media.scheduler import create_social_media_scheduler
import os

def integrate_social_media_scheduler(app):
    """
    Integrate social media scheduler with Flask app
    
    Args:
        app: Flask app instance
        
    Returns:
        SocialMediaScheduler: Scheduler instance if successful, None otherwise
    """
    try:
        # Get Supabase client from app config (assuming it's already set up)
        supabase_client = app.config.get('supabase')
        
        if not supabase_client:
            print("❌ Supabase client not found in app config")
            return None
        
        # Create social media scheduler
        social_scheduler = create_social_media_scheduler(app, supabase_client)
        
        if social_scheduler:
            # Start the scheduler
            social_scheduler.start()
            print("✅ Social media scheduler started successfully")
            
            # Store scheduler in app config for access from routes
            app.config['social_scheduler'] = social_scheduler
            
            return social_scheduler
        else:
            print("❌ Failed to create social media scheduler")
            return None
            
    except Exception as e:
        print(f"❌ Error integrating social media scheduler: {str(e)}")
        return None

def add_social_media_routes(app):
    """
    Add social media management routes to Flask app
    
    Args:
        app: Flask app instance
    """
    
    @app.route('/social-media/status')
    def social_media_status():
        """Get social media scheduler status"""
        try:
            scheduler = app.config.get('social_scheduler')
            if not scheduler:
                return {'error': 'Social media scheduler not available'}, 500
            
            status = scheduler.get_scheduler_status()
            return status
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/social-media/generate-content', methods=['POST'])
    def manual_generate_content():
        """Manually trigger content generation"""
        try:
            scheduler = app.config.get('social_scheduler')
            if not scheduler:
                return {'error': 'Social media scheduler not available'}, 500
            
            # Run content generation job
            scheduler.job_generate_content()
            return {'message': 'Content generation started'}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/social-media/post-content', methods=['POST'])
    def manual_post_content():
        """Manually trigger content posting"""
        try:
            scheduler = app.config.get('social_scheduler')
            if not scheduler:
                return {'error': 'Social media scheduler not available'}, 500
            
            # Run posting job
            scheduler.job_post_content()
            return {'message': 'Content posting started'}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/social-media/analytics', methods=['POST'])
    def manual_collect_analytics():
        """Manually trigger analytics collection"""
        try:
            scheduler = app.config.get('social_scheduler')
            if not scheduler:
                return {'error': 'Social media scheduler not available'}, 500
            
            # Run analytics collection job
            scheduler.job_collect_analytics()
            return {'message': 'Analytics collection started'}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Example usage in your main app.py
def example_app_setup():
    """Example of how to set up the Flask app with social media scheduler"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = 'your-secret-key'
    
    # Set up Supabase (replace with your actual credentials)
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        app.config['supabase'] = supabase_client
        
        # Integrate social media scheduler
        social_scheduler = integrate_social_media_scheduler(app)
        
        if social_scheduler:
            # Add management routes
            add_social_media_routes(app)
            print("✅ Social media integration complete")
        else:
            print("⚠️  Social media scheduler not available")
    else:
        print("❌ Supabase credentials not found")
    
    return app

if __name__ == "__main__":
    # Example usage
    app = example_app_setup()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)