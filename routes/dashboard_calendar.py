"""Dashboard calendar routes"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import pytz
from functools import wraps
from utils.logger import log_error

dashboard_calendar_bp = Blueprint('dashboard_calendar', __name__)

def token_required(f):
    """Verify dashboard access token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        from app import supabase
        
        result = supabase.table('dashboard_tokens').select(
            '*, trainers(*), clients(*)'
        ).eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 401
            
        if result.data.get('trainers'):
            request.user = result.data['trainers']
            request.user_type = 'trainer'
        else:
            request.user = result.data['clients']
            request.user_type = 'client'
            
        request.token = token
        return f(*args, **kwargs)
        
    return decorated

@dashboard_calendar_bp.route('/api/dashboard/calendar/day', methods=['GET'])
@token_required
def get_day_sessions():
    """Get all sessions for a specific day"""
    try:
        from app import supabase
        
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date parameter required'}), 400
            
        try:
            day_date = datetime.fromisoformat(date)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
        sessions = supabase.table('bookings').select(
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
        ).eq('trainer_id', request.user['id']).eq(
            'session_date', day_date.date().isoformat()
        ).order('start_time').execute()
        
        formatted_sessions = []
        for session in (sessions.data or []):
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

@dashboard_calendar_bp.route('/api/dashboard/calendar/day/session', methods=['POST'])
@token_required
def create_session():
    """Create a new session"""
    try:
        from app import supabase
        
        data = request.json
        required = ['client_id', 'date', 'start_time', 'end_time']
        
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
            
        client = supabase.table('clients').select('*').eq(
            'id', data['client_id']
        ).eq('trainer_id', request.user['id']).single().execute()
        
        if not client.data:
            return jsonify({'error': 'Invalid client'}), 400
            
        session = supabase.table('bookings').insert({
            'trainer_id': request.user['id'],
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

@dashboard_calendar_bp.route('/api/dashboard/calendar/day/session/<id>', methods=['PUT'])
@token_required
def update_session(id):
    """Update a session"""
    try:
        from app import supabase
        
        data = request.json
        
        session = supabase.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.user['id']).single().execute()
        
        if not session.data:
            return jsonify({'error': 'Session not found'}), 404
            
        allowed_updates = [
            'start_time', 'end_time', 'session_type',
            'notes', 'status'
        ]
        
        updates = {
            k: v for k, v in data.items() 
            if k in allowed_updates
        }
        
        if updates:
            updated = supabase.table('bookings').update(
                updates
            ).eq('id', id).execute()
            
            return jsonify(updated.data[0])
        
        return jsonify({'error': 'No valid updates provided'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_calendar_bp.route('/api/dashboard/calendar/day/session/<id>', methods=['DELETE'])
@token_required
def delete_session(id):
    """Delete a session"""
    try:
        from app import supabase
        
        session = supabase.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.user['id']).single().execute()
        
        if not session.data:
            return jsonify({'error': 'Session not found'}), 404
            
        supabase.table('bookings').delete().eq('id', id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500