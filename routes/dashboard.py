from flask import Blueprint, render_template, jsonify, request
from functools import wraps
from datetime import datetime, timedelta
import jwt
from services.assessment import EnhancedAssessmentService
from utils.logger import log_error

dashboard = Blueprint('dashboard', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.get_by_id(data['user_id'])
        except:
            return jsonify({'message': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@dashboard.route('/trainer/dashboard')
@token_required
def trainer_dashboard(current_user):
    """Trainer dashboard view"""
    try:
        # Get trainer stats
        stats = {
            'total_clients': get_total_clients(current_user.id),
            'active_sessions': get_active_sessions(current_user.id),
            'completion_rate': get_completion_rate(current_user.id),
            'revenue_mtd': get_revenue_mtd(current_user.id)
        }

        # Get upcoming sessions
        upcoming = get_upcoming_sessions(current_user.id)

        # Get recent assessments
        assessments = get_recent_assessments(current_user.id)

        return render_template(
            'trainer/dashboard.html',
            stats=stats,
            upcoming=upcoming,
            assessments=assessments
        )

    except Exception as e:
        log_error(f"Dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@dashboard.route('/trainer/clients')
@token_required
def trainer_clients(current_user):
    """Client management view"""
    try:
        clients = get_trainer_clients(current_user.id)
        return render_template('trainer/clients.html', clients=clients)
    except Exception as e:
        log_error(f"Client list error: {str(e)}")
        return jsonify({'error': 'Failed to load clients'}), 500

@dashboard.route('/trainer/analytics')
@token_required
def trainer_analytics(current_user):
    """Analytics and reporting view"""
    try:
        # Get date range
        start_date = request.args.get('start', default=datetime.now() - timedelta(days=30))
        end_date = request.args.get('end', default=datetime.now())

        analytics = {
            'session_stats': get_session_stats(current_user.id, start_date, end_date),
            'revenue_stats': get_revenue_stats(current_user.id, start_date, end_date),
            'client_progress': get_client_progress(current_user.id, start_date, end_date)
        }

        return render_template('trainer/analytics.html', analytics=analytics)
    except Exception as e:
        log_error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to load analytics'}), 500