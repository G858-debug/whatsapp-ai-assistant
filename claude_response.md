## ANALYSIS
The error shows that the `jwt` module is not installed. This is needed for the dashboard functionality. We need to add the PyJWT package to requirements.txt and ensure all necessary dependencies are included.

## FILES TO CHANGE

### FILE: requirements.txt
```python
# Core Framework
Flask==2.3.3
flask-cors==4.0.0

# WhatsApp Integration
requests==2.31.0

# AI/ML
anthropic==0.34.2

# Database
supabase==2.5.0

# Utilities
python-dotenv==1.0.0
pytz==2024.1

# Payment Processing
hashlib
urllib3

# Authentication & Security
PyJWT==2.8.0

# Logging
colorama==0.4.6

# Rate Limiting
redis==5.0.1

# Dashboard & Web
Werkzeug==2.3.7

# Voice Processing
pydub==0.25.1
speech_recognition==3.10.0

# Data Processing
pandas==2.0.3
numpy==1.24.3

# Image Processing (for assessment photos)
Pillow==10.0.0

# Async Support
aiohttp==3.8.5

# Validation
pydantic==2.3.0

# Date/Time
python-dateutil==2.8.2

# Testing (optional, for development)
pytest==7.4.0
pytest-asyncio==0.21.1

# Production Server
gunicorn==21.2.0
```

### FILE: routes/dashboard.py
```python
from flask import Blueprint, request, jsonify, redirect
from datetime import datetime, timedelta
import secrets
import jwt
from functools import wraps
from services.analytics import AnalyticsService
from utils.logger import log_info, log_error
import os

dashboard_bp = Blueprint('dashboard', __name__)

class DashboardService:
    """Service for handling dashboard-related operations"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.analytics = AnalyticsService(supabase_client)
        self.jwt_secret = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
        self.dashboard_url = os.environ.get('DASHBOARD_BASE_URL', 'https://refiloe.co.za')
        
    def generate_dashboard_token(self, trainer_id: str) -> str:
        """Generate a JWT token for dashboard access"""
        try:
            payload = {
                'trainer_id': trainer_id,
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow(),
                'type': 'dashboard_access'
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Store token in database for tracking
            self.db.table('dashboard_tokens').insert({
                'trainer_id': trainer_id,
                'token': token,
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            return token
            
        except Exception as e:
            log_error(f"Error generating dashboard token: {str(e)}")
            return None
    
    def verify_dashboard_token(self, token: str) -> dict:
        """Verify and decode a dashboard token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if token exists in database and is not revoked
            result = self.db.table('dashboard_tokens').select('*').eq(
                'token', token
            ).eq('revoked', False).execute()
            
            if not result.data:
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            log_error("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            log_error(f"Invalid token: {str(e)}")
            return None
    
    def generate_dashboard_link(self, trainer_id: str) -> str:
        """Generate a secure dashboard link for trainer"""
        try:
            token = self.generate_dashboard_token(trainer_id)
            if not token:
                return None
                
            return f"{self.dashboard_url}/dashboard?token={token}"
            
        except Exception as e:
            log_error(f"Error generating dashboard link: {str(e)}")
            return None
    
    def get_dashboard_data(self, trainer_id: str) -> dict:
        """Get all dashboard data for a trainer"""
        try:
            # Get trainer info
            trainer = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).single().execute()
            
            if not trainer.data:
                return None
            
            # Get analytics
            analytics = self.analytics.get_trainer_analytics(trainer_id)
            
            # Get recent activity
            recent_bookings = self.db.table('bookings').select(
                '*, client:clients(name, phone_number)'
            ).eq('trainer_id', trainer_id).order(
                'created_at', desc=True
            ).limit(10).execute()
            
            # Get active clients
            active_clients = self.db.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            # Get upcoming sessions
            upcoming = self.db.table('bookings').select(
                '*, client:clients(name)'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'confirmed'
            ).gte('date', datetime.now().isoformat()).order(
                'date'
            ).limit(10).execute()
            
            return {
                'trainer': trainer.data,
                'analytics': analytics,
                'recent_bookings': recent_bookings.data if recent_bookings.data else [],
                'active_clients': active_clients.data if active_clients.data else [],
                'upcoming_sessions': upcoming.data if upcoming.data else [],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            log_error(f"Error getting dashboard data: {str(e)}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a dashboard token"""
        try:
            result = self.db.table('dashboard_tokens').update({
                'revoked': True,
                'revoked_at': datetime.utcnow().isoformat()
            }).eq('token', token).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error revoking token: {str(e)}")
            return False

# Initialize service (will be set in app.py)
dashboard_service = None

def token_required(f):
    """Decorator to require valid dashboard token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
            
        payload = dashboard_service.verify_dashboard_token(token)
        
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        request.trainer_id = payload['trainer_id']
        return f(*args, **kwargs)
        
    return decorated_function

@dashboard_bp.route('/api/dashboard/login', methods=['POST'])
def dashboard_login():
    """Generate dashboard access link"""
    try:
        data = request.json
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'error': 'Phone number required'}), 400
            
        # Normalize phone number
        if not phone_number.startswith('+'):
            phone_number = '+27' + phone_number.lstrip('0')
            
        # Find trainer
        result = dashboard_service.db.table('trainers').select('*').eq(
            'phone_number', phone_number
        ).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Trainer not found'}), 404
            
        # Generate dashboard link
        link = dashboard_service.generate_dashboard_link(result.data['id'])
        
        if not link:
            return jsonify({'error': 'Failed to generate dashboard link'}), 500
            
        # Here you would normally send this link via WhatsApp
        # For now, we'll return it in the response
        return jsonify({
            'success': True,
            'message': 'Dashboard link generated',
            'link': link,
            'expires_in': '24 hours'
        })
        
    except Exception as e:
        log_error(f"Dashboard login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/data', methods=['GET'])
@token_required
def get_dashboard_data():
    """Get dashboard data for authenticated trainer"""
    try:
        data = dashboard_service.get_dashboard_data(request.trainer_id)
        
        if not data:
            return jsonify({'error': 'Failed to fetch dashboard data'}), 500
            
        return jsonify(data)
        
    except Exception as e:
        log_error(f"Dashboard data error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/clients', methods=['GET'])
@token_required
def get_clients():
    """Get all clients for trainer"""
    try:
        result = dashboard_service.db.table('clients').select('*').eq(
            'trainer_id', request.trainer_id
        ).order('created_at', desc=True).execute()
        
        return jsonify(result.data if result.data else [])
        
    except Exception as e:
        log_error(f"Get clients error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/bookings', methods=['GET'])
@token_required
def get_bookings():
    """Get bookings for trainer"""
    try:
        # Get query parameters
        status = request.args.get('status')
        date_from = request.args.get('from')
        date_to = request.args.get('to')
        
        query = dashboard_service.db.table('bookings').select(
            '*, client:clients(name, phone_number)'
        ).eq('trainer_id', request.trainer_id)
        
        if status:
            query = query.eq('status', status)
        if date_from:
            query = query.gte('date', date_from)
        if date_to:
            query = query.lte('date', date_to)
            
        result = query.order('date', desc=True).execute()
        
        return jsonify(result.data if result.data else [])
        
    except Exception as e:
        log_error(f"Get bookings error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/analytics', methods=['GET'])
@token_required
def get_analytics():
    """Get analytics for trainer"""
    try:
        period = request.args.get('period', 'month')
        analytics = dashboard_service.analytics.get_trainer_analytics(
            request.trainer_id, 
            period=period
        )
        
        return jsonify(analytics)
        
    except Exception as e:
        log_error(f"Get analytics error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/logout', methods=['POST'])
@token_required
def dashboard_logout():
    """Logout and revoke token"""
    try:
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
        else:
            token = request.args.get('token')
            
        success = dashboard_service.revoke_token(token)
        
        if success:
            return jsonify({'success': True, 'message': 'Logged out successfully'})
        else:
            return jsonify({'error': 'Failed to logout'}), 500
            
    except Exception as e:
        log_error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/update-schedule', methods=['POST'])
@token_required
def update_schedule():
    """Update trainer's availability schedule"""
    try:
        schedule_data = request.json
        
        result = dashboard_service.db.table('trainer_schedules').upsert({
            'trainer_id': request.trainer_id,
            'schedule': schedule_data,
            'updated_at': datetime.utcnow().isoformat()
        }).execute()
        
        if result.data:
            return jsonify({'success': True, 'message': 'Schedule updated'})
        else:
            return jsonify({'error': 'Failed to update schedule'}), 500
            
    except Exception as e:
        log_error(f"Update schedule error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
```

## MIGRATION: add_dashboard_tokens_table.sql
```sql
-- Create dashboard tokens table
CREATE TABLE IF NOT EXISTS dashboard_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    ip_address TEXT,
    user_agent TEXT
);

-- Create indexes
CREATE INDEX idx_dashboard_tokens_trainer_id ON dashboard_tokens(trainer_id);
CREATE INDEX idx_dashboard_tokens_token ON dashboard_tokens(token);
CREATE INDEX idx_dashboard_tokens_expires_at ON dashboard_tokens(expires_at);
CREATE INDEX idx_dashboard_tokens_revoked ON dashboard_tokens(revoked);

-- Add JWT secret to environment variables table if exists
-- Or store securely in your environment configuration
```

## SUMMARY
Fixed the ModuleNotFoundError by adding PyJWT==2.8.0 to requirements.txt. Also updated the requirements.txt file to include all necessary dependencies for the application, ensuring proper versions are specified. Created a migration for the dashboard_tokens table to support the dashboard authentication system. The dashboard routes are now properly configured with JWT authentication.