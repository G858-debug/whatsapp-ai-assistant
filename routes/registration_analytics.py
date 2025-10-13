#!/usr/bin/env python3
"""
Registration Analytics API Routes
Provides endpoints for registration analytics and reporting
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.logger import log_info, log_error
from services.registration.registration_analytics import RegistrationAnalytics

# Create blueprint
registration_analytics_bp = Blueprint('registration_analytics', __name__)

def setup_registration_analytics_routes(app, supabase):
    """Setup registration analytics routes"""
    
    # Initialize analytics service
    analytics_service = RegistrationAnalytics(supabase)
    
    @registration_analytics_bp.route('/analytics/overview', methods=['GET'])
    def get_analytics_overview():
        """Get registration analytics overview"""
        try:
            days = request.args.get('days', 30, type=int)
            
            # Validate days parameter
            if days < 1 or days > 365:
                return jsonify({
                    'status': 'error',
                    'message': 'Days parameter must be between 1 and 365'
                }), 400
            
            analytics = analytics_service.get_comprehensive_analytics(days)
            
            return jsonify({
                'status': 'success',
                'data': analytics
            }), 200
            
        except Exception as e:
            log_error(f"Error getting analytics overview: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve analytics data'
            }), 500
    
    @registration_analytics_bp.route('/analytics/real-time', methods=['GET'])
    def get_real_time_metrics():
        """Get real-time registration metrics"""
        try:
            metrics = analytics_service.get_real_time_metrics()
            
            return jsonify({
                'status': 'success',
                'data': metrics,
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            log_error(f"Error getting real-time metrics: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve real-time metrics'
            }), 500
    
    @registration_analytics_bp.route('/analytics/report', methods=['GET'])
    def get_analytics_report():
        """Get formatted analytics report"""
        try:
            days = request.args.get('days', 7, type=int)
            format_type = request.args.get('format', 'summary')
            
            # Validate parameters
            if days < 1 or days > 365:
                return jsonify({
                    'status': 'error',
                    'message': 'Days parameter must be between 1 and 365'
                }), 400
            
            if format_type not in ['summary', 'detailed']:
                return jsonify({
                    'status': 'error',
                    'message': 'Format must be either "summary" or "detailed"'
                }), 400
            
            report = analytics_service.generate_analytics_report(days, format_type)
            
            return jsonify({
                'status': 'success',
                'data': {
                    'report': report,
                    'format': format_type,
                    'period_days': days,
                    'generated_at': datetime.now().isoformat()
                }
            }), 200
            
        except Exception as e:
            log_error(f"Error generating analytics report: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate analytics report'
            }), 500
    
    @registration_analytics_bp.route('/analytics/funnel', methods=['GET'])
    def get_funnel_analysis():
        """Get detailed funnel analysis"""
        try:
            days = request.args.get('days', 30, type=int)
            
            analytics = analytics_service.get_comprehensive_analytics(days)
            funnel_data = analytics.get('funnel_analysis', {})
            
            return jsonify({
                'status': 'success',
                'data': {
                    'funnel_analysis': funnel_data,
                    'period_days': days,
                    'generated_at': datetime.now().isoformat()
                }
            }), 200
            
        except Exception as e:
            log_error(f"Error getting funnel analysis: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve funnel analysis'
            }), 500
    
    @registration_analytics_bp.route('/analytics/errors', methods=['GET'])
    def get_error_analysis():
        """Get detailed error analysis"""
        try:
            days = request.args.get('days', 30, type=int)
            
            analytics = analytics_service.get_comprehensive_analytics(days)
            error_data = analytics.get('error_analysis', {})
            
            return jsonify({
                'status': 'success',
                'data': {
                    'error_analysis': error_data,
                    'period_days': days,
                    'generated_at': datetime.now().isoformat()
                }
            }), 200
            
        except Exception as e:
            log_error(f"Error getting error analysis: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve error analysis'
            }), 500
    
    @registration_analytics_bp.route('/analytics/recommendations', methods=['GET'])
    def get_optimization_recommendations():
        """Get optimization recommendations"""
        try:
            days = request.args.get('days', 30, type=int)
            
            analytics = analytics_service.get_comprehensive_analytics(days)
            recommendations = analytics.get('recommendations', [])
            
            return jsonify({
                'status': 'success',
                'data': {
                    'recommendations': recommendations,
                    'total_recommendations': len(recommendations),
                    'period_days': days,
                    'generated_at': datetime.now().isoformat()
                }
            }), 200
            
        except Exception as e:
            log_error(f"Error getting recommendations: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve recommendations'
            }), 500
    
    @registration_analytics_bp.route('/analytics/health', methods=['GET'])
    def get_system_health():
        """Get registration system health status"""
        try:
            real_time_metrics = analytics_service.get_real_time_metrics()
            
            # Get 7-day analytics for trend analysis
            analytics = analytics_service.get_comprehensive_analytics(7)
            overview = analytics.get('overview', {})
            
            health_status = {
                'overall_status': real_time_metrics.get('current_status', 'unknown'),
                'completion_rate_7d': overview.get('completion_rate', 0),
                'error_rate_7d': overview.get('error_rate', 0),
                'last_24h_metrics': real_time_metrics.get('last_24_hours', {}),
                'alerts': real_time_metrics.get('alerts', []),
                'recommendations_count': len(analytics.get('recommendations', [])),
                'system_uptime': 'operational',  # Could be enhanced with actual uptime monitoring
                'last_updated': datetime.now().isoformat()
            }
            
            return jsonify({
                'status': 'success',
                'data': health_status
            }), 200
            
        except Exception as e:
            log_error(f"Error getting system health: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve system health'
            }), 500
    
    @registration_analytics_bp.route('/dashboard', methods=['GET'])
    def analytics_dashboard():
        """Serve the analytics dashboard"""
        try:
            from flask import render_template
            return render_template('registration_analytics.html')
        except Exception as e:
            log_error(f"Error serving analytics dashboard: {str(e)}")
            return f"Error loading dashboard: {str(e)}", 500
    
    # Register blueprint
    app.register_blueprint(registration_analytics_bp, url_prefix='/api/registration')
    
    log_info("Registration analytics routes registered successfully")
