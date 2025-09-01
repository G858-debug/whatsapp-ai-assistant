from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta
import secrets
from functools import wraps
from services.analytics import AnalyticsService
from utils.logger import log_error, log_info

dashboard_bp = Blueprint('dashboard', __name__)

# Initialize service
dashboard_service = None

def init_dashboard_routes(supabase_client):
    """Initialize dashboard routes with Supabase client"""
    global dashboard_service
    dashboard_service = AnalyticsService(supabase_client)
    dashboard_service.db = supabase_client  # Store db reference for direct queries

def token_required(f):
    """Decorator to require valid dashboard token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Verify token
        result = dashboard_service.db.table('dashboard_tokens').select(
            '*, trainers(*)'
        ).eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check expiry
        expires_at = datetime.fromisoformat(result.data['expires_at'])
        if expires_at < datetime.utcnow():
            return jsonify({'error': 'Token expired'}), 401
        
        # Add trainer info to request
        request.trainer_id = result.data['trainer_id']
        request.trainer = result.data['trainers']
        
        return f(*args, **kwargs)
    return decorated

@dashboard_bp.route('/dashboard')
def dashboard():
    """Render dashboard page"""
    return render_template('dashboard.html')

@dashboard_bp.route('/dashboard/login', methods=['GET', 'POST'])
def login():
    """Handle dashboard login"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # Handle POST
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'error': 'Phone number required'}), 400
    
    # Verify trainer exists
    trainer = dashboard_service.db.table('trainers').select('*').eq(
        'phone_number', phone
    ).single().execute()
    
    if not trainer.data:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    # Store token
    dashboard_service.db.table('dashboard_tokens').insert({
        'trainer_id': trainer.data['id'],
        'token': token,
        'expires_at': expires_at.isoformat(),
        'created_at': datetime.utcnow().isoformat()
    }).execute()
    
    return jsonify({
        'token': token,
        'trainer': {
            'id': trainer.data['id'],
            'name': trainer.data['name'],
            'phone': trainer.data['phone_number']
        }
    })

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
@token_required
def get_stats():
    """Get dashboard statistics"""
    try:
        # Get date range
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        # Get bookings
        bookings = dashboard_service.db.table('bookings').select('*').eq(
            'trainer_id', request.trainer_id
        ).gte('session_date', start_date.date().isoformat()).execute()
        
        # Calculate stats
        total_sessions = len(bookings.data or [])
        completed = sum(1 for b in (bookings.data or []) if b['status'] == 'completed')
        revenue = sum(b.get('amount', 0) for b in (bookings.data or []) if b['status'] == 'completed')
        
        #
</details>
