from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import pytz
from functools import wraps

dashboard_bp = Blueprint('dashboard', __name__)

def token_required(f):
    """Verify dashboard access token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        # Verify token and get trainer info
        result = dashboard_service.db.table('dashboard_tokens').select(
            '*, trainers(*)'
        ).eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 401
            
        request.trainer = result.data['trainers']
        return f(*args, **kwargs)
        
    return decorated

@dashboard_bp.route('/api/dashboard/calendar/day', methods=['GET'])
@token_required
def get_day_sessions():
    """Get all sessions for a specific day"""
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date parameter required'}), 400
            
        # Parse date
        try:
            day_date = datetime.fromisoformat(date)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
        # Get sessions for this day
        sessions = dashboard_service.db.table('bookings').select(
            """
            *,
            clients (
                id,
                name,
                whatsapp,
                package_type,
                sessions_remaining
            )
            """
        ).eq('trainer_id', request.trainer['id']).eq(
            'session_date', day_date.date().isoformat()
        ).order('start_time').execute()
        
        # Format response
        formatted_sessions = []
        for session in sessions.data:
            formatted_sessions.append({
                'id': session['id'],
                'start_time': session['start_time'],
                'end_time': session['end_time'],
                'client': {
                    'id': session['clients']['id'],
                    'name': session['clients']['name'],
                    'phone': session['clients']['whatsapp'],
                    'package': session['clients']['package_type'],
                    'sessions_remaining': session['clients']['sessions_remaining']
                },
                'status': session['status'],
                'session_type': session['session_type'],
                'notes': session['notes']
            })
            
        return jsonify({
            'date': day_date.date().isoformat(),
            'sessions': formatted_sessions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/calendar/day/session', methods=['POST'])
@token_required
def create_session():
    """Create a new session"""
    try:
        data = request.json
        required = ['client_id', 'date', 'start_time', 'end_time']
        
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Validate client belongs to trainer
        client = dashboard_service.db.table('clients').select('*').eq(
            'id', data['client_id']
        ).eq('trainer_id', request.trainer['id']).single().execute()
        
        if not client.data:
            return jsonify({'error': 'Invalid client'}), 400
            
        # Create session
        session = dashboard_service.db.table('bookings').insert({
            'trainer_id': request.trainer['id'],
            'client_id': data['client_id'],
            'session_date': data['date'],
            'start_time': data['start_time'],
            'end_time': data['end_time'],
            'session_type': data.get('session_type', 'standard'),
            'notes': data.get('notes', ''),
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return jsonify(session.data[0])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/calendar/day/session/<id>', methods=['PUT'])
@token_required
def update_session(id):
    """Update a session"""
    try:
        data = request.json
        
        # Verify session belongs to trainer
        session = dashboard_service.db.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.trainer['id']).single().execute()
        
        if not session.data:
            return jsonify({'error': 'Session not found'}), 404
            
        # Update allowed fields
        allowed_updates = [
            'start_time', 'end_time', 'session_type',
            'notes', 'status'
        ]
        
        updates = {
            k: v for k, v in data.items() 
            if k in allowed_updates
        }
        
        if updates:
            updated = dashboard_service.db.table('bookings').update(
                updates
            ).eq('id', id).execute()
            
            return jsonify(updated.data[0])
        
        return jsonify({'error': 'No valid updates provided'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/calendar/day/session/<id>', methods=['DELETE'])
@token_required
def delete_session(id):
    """Delete a session"""
    try:
        # Verify session belongs to trainer
        session = dashboard_service.db.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.trainer['id']).single().execute()
        
        if not session.data:
            return jsonify({'error': 'Session not found'}), 404
            
        # Delete session
        dashboard_service.db.table('bookings').delete().eq('id', id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500