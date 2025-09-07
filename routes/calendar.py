"""Calendar and client view routes"""
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
import pytz
import secrets
from io import BytesIO
from jinja2 import Template
from utils.logger import log_error

calendar_bp = Blueprint('calendar', __name__)

def generate_calendar_token(client_id: str) -> str:
    """Generate a secure token for calendar access"""
    import hashlib
    token_data = f"{client_id}:{datetime.now().isoformat()}:{secrets.token_hex(16)}"
    return hashlib.sha256(token_data.encode()).hexdigest()

def verify_calendar_token(token: str, client_id: str) -> bool:
    """Verify calendar access token"""
    from app import supabase
    try:
        result = supabase.table('calendar_access_tokens').select('*').eq(
            'token', token
        ).eq('client_id', client_id).eq('is_valid', True).execute()
        
        if result.data:
            created_at = datetime.fromisoformat(result.data[0]['created_at'])
            if (datetime.now(pytz.UTC) - created_at).total_seconds() < 86400:
                return True
        return False
    except:
        return False

@calendar_bp.route('/api/client/calendar/<client_id>')
def client_calendar_view(client_id):
    """Client calendar view endpoint"""
    from app import supabase, Config
    
    try:
        token = request.args.get('token')
        if not token or not verify_calendar_token(token, client_id):
            return "Access denied. Please request a new calendar link.", 403
        
        client = supabase.table('clients').select('*, trainers(*)').eq(
            'id', client_id
        ).single().execute()
        
        if not client.data:
            return "Client not found", 404
        
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
        end_date = today + timedelta(days=30)
        
        sessions = supabase.table('bookings').select('*').eq(
            'client_id', client_id
        ).gte('session_date', today.isoformat()).lte(
            'session_date', end_date.isoformat()
        ).order('session_date').order('session_time').execute()
        
        past_sessions = supabase.table('bookings').select('*').eq(
            'client_id', client_id
        ).lt('session_date', today.isoformat()).order(
            'session_date', desc=True
        ).limit(10).execute()
        
        next_session = None
        for session in (sessions.data or []):
            if session['status'] in ['confirmed', 'rescheduled']:
                next_session = session
                break
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>My Training Calendar - {{ client_name }}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }
                .header h1 {
                    font-size: 24px;
                    margin-bottom: 10px;
                }
                .header p {
                    opacity: 0.9;
                    font-size: 14px;
                }
                .next-session {
                    background: #f0f9ff;
                    border-left: 4px solid #3b82f6;
                    margin: 20px;
                    padding: 15px;
                    border-radius: 10px;
                }
                .next-session h2 {
                    color: #1e40af;
                    font-size: 16px;
                    margin-bottom: 10px;
                }
                .session-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    margin: 10px 20px;
                    padding: 15px;
                    border-radius: 10px;
                    position: relative;
                }
                .session-card.completed {
                    opacity: 0.6;
                    background: #f9fafb;
                }
                .session-date {
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 5px;
                }
                .session-time {
                    color: #6b7280;
                    font-size: 14px;
                }
                .session-status {
                    position: absolute;
                    top: 15px;
                    right: 15px;
                    padding: 4px 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    font-weight: 500;
                }
                .status-confirmed {
                    background: #d1fae5;
                    color: #065f46;
                }
                .status-completed {
                    background: #e0e7ff;
                    color: #3730a3;
                }
                .status-cancelled {
                    background: #fee2e2;
                    color: #991b1b;
                }
                .section-title {
                    font-size: 18px;
                    font-weight: 600;
                    margin: 30px 20px 15px;
                    color: #1f2937;
                }
                .action-buttons {
                    padding: 20px;
                    display: flex;
                    gap: 10px;
                }
                .btn {
                    flex: 1;
                    padding: 12px;
                    border: none;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 500;
                    text-align: center;
                    text-decoration: none;
                    cursor: pointer;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .btn-secondary {
                    background: #f3f4f6;
                    color: #374151;
                }
                .empty-state {
                    text-align: center;
                    padding: 40px 20px;
                    color: #6b7280;
                }
                .stats {
                    display: flex;
                    justify-content: space-around;
                    padding: 20px;
                    background: #f9fafb;
                }
                .stat {
                    text-align: center;
                }
                .stat-value {
                    font-size: 24px;
                    font-weight: 700;
                    color: #1f2937;
                }
                .stat-label {
                    font-size: 12px;
                    color: #6b7280;
                    margin-top: 5px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 My Training Calendar</h1>
                    <p>{{ client_name }} • {{ trainer_name }}</p>
                </div>
                
                {% if next_session %}
                <div class="next-session">
                    <h2>🎯 Next Session</h2>
                    <div class="session-date">{{ next_session.formatted_date }}</div>
                    <div class="session-time">{{ next_session.session_time }}</div>
                </div>
                {% endif %}
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{{ upcoming_count }}</div>
                        <div class="stat-label">Upcoming</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ completed_count }}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{{ total_count }}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
                
                <h2 class="section-title">📍 Upcoming Sessions</h2>
                {% if upcoming_sessions %}
                    {% for session in upcoming_sessions %}
                    <div class="session-card">
                        <div class="session-date">{{ session.formatted_date }}</div>
                        <div class="session-time">🕐 {{ session.session_time }}</div>
                        <span class="session-status status-{{ session.status }}">{{ session.status|upper }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <p>No upcoming sessions scheduled</p>
                    </div>
                {% endif %}
                
                <h2 class="section-title">✅ Recent Sessions</h2>
                {% if past_sessions %}
                    {% for session in past_sessions %}
                    <div class="session-card completed">
                        <div class="session-date">{{ session.formatted_date }}</div>
                        <div class="session-time">{{ session.session_time }}</div>
                        <span class="session-status status-{{ session.status }}">{{ session.status|upper }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <p>No past sessions</p>
                    </div>
                {% endif %}
                
                <div class="action-buttons">
                    <a href="/api/client/trainer-availability/{{ trainer_id }}?client_id={{ client_id }}&token={{ token }}" class="btn btn-primary">
                        Check Availability
                    </a>
                    <a href="/api/client/calendar/{{ client_id }}/ics?token={{ token }}" class="btn btn-secondary">
                        📥 Download Calendar
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        def format_date(date_str):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%A, %d %B')
        
        upcoming_sessions = []
        for session in (sessions.data or []):
            session['formatted_date'] = format_date(session['session_date'])
            upcoming_sessions.append(session)
        
        past_sessions_formatted = []
        for session in (past_sessions.data or []):
            session['formatted_date'] = format_date(session['session_date'])
            past_sessions_formatted.append(session)
        
        if next_session:
            next_session['formatted_date'] = format_date(next_session['session_date'])
        
        completed_count = len([s for s in past_sessions.data if s['status'] == 'completed'])
        upcoming_count = len([s for s in sessions.data if s['status'] in ['confirmed', 'rescheduled']])
        
        template = Template(html_template)
        return template.render(
            client_name=client.data['name'],
            client_id=client_id,
            trainer_name=client.data['trainers']['name'],
            trainer_id=client.data['trainer_id'],
            next_session=next_session,
            upcoming_sessions=upcoming_sessions,
            past_sessions=past_sessions_formatted,
            upcoming_count=upcoming_count,
            completed_count=completed_count,
            total_count=upcoming_count + completed_count,
            token=token
        )
        
    except Exception as e:
        log_error(f"Error in client calendar view: {str(e)}")
        return "Error loading calendar", 500

@calendar_bp.route('/api/client/calendar/<client_id>/ics')
def download_calendar_ics(client_id):
    """Download calendar in ICS format"""
    from app import supabase, calendar_service, Config
    
    try:
        token = request.args.get('token')
        if not token or not verify_calendar_token(token, client_id):
            return "Access denied", 403
        
        client = supabase.table('clients').select('*, trainers(*)').eq(
            'id', client_id
        ).single().execute()
        
        if not client.data:
            return "Client not found", 404
        
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()
        sessions = supabase.table('bookings').select('*').eq(
            'client_id', client_id
        ).gte('session_date', today.isoformat()).order('session_date').execute()
        
        ics_content = calendar_service.generate_ics_file({
            'client': client.data,
            'sessions': sessions.data or [],
            'trainer': client.data['trainers']
        })
        
        output = BytesIO()
        output.write(ics_content.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/calendar',
            as_attachment=True,
            download_name=f'training_calendar_{client.data["name"].replace(" ", "_")}.ics'
        )
        
    except Exception as e:
        log_error(f"Error generating ICS file: {str(e)}")
        return "Error generating calendar file", 500