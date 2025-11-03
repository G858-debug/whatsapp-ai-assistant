"""
Dashboard Routes
Web dashboard for relationship management
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services.dashboard import DashboardService, DashboardTokenManager
from utils.logger import log_info, log_error
import os

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Initialize services (will be set by app)
dashboard_service = None
token_manager = None

def init_dashboard_services(supabase_client):
    """Initialize dashboard services"""
    global dashboard_service, token_manager
    dashboard_service = DashboardService(supabase_client)
    token_manager = DashboardTokenManager(supabase_client)

@dashboard_bp.route('/<user_id>/<token>')
def dashboard_view(user_id, token):
    """Main dashboard view"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data:
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, token_data['role'])
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Check if this is a special purpose dashboard
        purpose = token_data.get('purpose', 'relationships')
        
        if purpose == 'browse_trainers' and token_data['role'] == 'client':
            # Special dashboard for browsing ALL trainers on the platform
            relationships = dashboard_service.get_all_trainers(user_id)
            stats = {
                'active_count': len([t for t in relationships if not t['is_connected']]),
                'pending_count': len([t for t in relationships if t['is_connected']]),
                'total_count': len(relationships)
            }
            relationship_type = 'available_trainers'
        else:
            # Regular dashboard showing user's relationships
            relationships = dashboard_service.get_relationships(user_id, token_data['role'])
            stats = dashboard_service.get_dashboard_stats(user_id, token_data['role'])
            relationship_type = 'clients' if token_data['role'] == 'trainer' else 'trainers'
        
        return render_template('dashboard/main.html',
                             user=user_info,
                             relationships=relationships,
                             stats=stats,
                             relationship_type=relationship_type,
                             role=token_data['role'],
                             purpose=purpose)
        
    except Exception as e:
        log_error(f"Dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the dashboard"), 500

@dashboard_bp.route('/api/<user_id>/<token>/relationships')
def api_get_relationships(user_id, token):
    """API endpoint to get relationships (for AJAX)"""
    try:
        # Validate token (but don't mark as used for API calls)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if token exists and is valid (but don't consume it)
        from datetime import datetime
        result = dashboard_service.db.table('dashboard_tokens').select('*').eq(
            'token_hash', token_hash
        ).eq('user_id', user_id).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 403
        
        token_data = result.data[0]
        
        # Get relationships
        status = request.args.get('status', 'active')
        relationships = dashboard_service.get_relationships(user_id, token_data['role'], status)
        
        return jsonify({'relationships': relationships})
        
    except Exception as e:
        log_error(f"API error: {str(e)}")
        return jsonify({'error': str(e)}), 500



@dashboard_bp.route('/api/<user_id>/<token>/export')
def api_export_csv(user_id, token):
    """API endpoint to export relationships as CSV"""
    try:
        # Validate token
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        from datetime import datetime
        result = dashboard_service.db.table('dashboard_tokens').select('*').eq(
            'token_hash', token_hash
        ).eq('user_id', user_id).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 403
        
        token_data = result.data[0]
        
        # Get relationships
        relationships = dashboard_service.get_relationships(user_id, token_data['role'])
        
        # Generate CSV
        import csv
        import io
        from flask import make_response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        if token_data['role'] == 'trainer':
            writer.writerow(['Name', 'Client ID', 'Phone', 'Email', 'Goals', 'Experience', 'Connected Date'])
        else:
            writer.writerow(['Name', 'Trainer ID', 'Phone', 'Email', 'Specialization', 'Experience', 'City', 'Connected Date'])
        
        # Write data
        for rel in relationships:
            if token_data['role'] == 'trainer':
                writer.writerow([
                    rel['name'], rel['id'], rel['phone'], rel['email'],
                    rel['additional_info'].get('goals', ''),
                    rel['additional_info'].get('experience', ''),
                    rel['connected_date']
                ])
            else:
                writer.writerow([
                    rel['name'], rel['id'], rel['phone'], rel['email'],
                    rel['additional_info'].get('specialization', ''),
                    rel['additional_info'].get('experience', ''),
                    rel['additional_info'].get('city', ''),
                    rel['connected_date']
                ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={token_data["role"]}_{user_id}_relationships.csv'
        
        return response
        
    except Exception as e:
        log_error(f"Export CSV error: {str(e)}")
        return jsonify({'error': str(e)}), 500