<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5307 -->
<!-- Max Tokens: 16000 -->
<!-- CONTINUATION NEEDED -->
## ANALYSIS

Continuing Step 3 - Need to split the remaining large files:
- `routes/dashboard.py` (817 lines) - needs splitting
- `services/ai_intent_handler.py` (649 lines) - needs splitting  
- `payment_integration.py` (746 lines) - needs splitting
- `services/dashboard_sync.py` (640 lines) - needs splitting

Let's split these files into smaller, focused modules.

## CHANGES NEEDED

### SPLIT FILE: routes/dashboard.py

Split into three logical modules:

### NEW FILE: routes/dashboard_calendar.py
```python
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
```

### NEW FILE: routes/dashboard_gamification.py
```python
"""Dashboard gamification routes"""
from flask import Blueprint, jsonify, request, render_template
from datetime import datetime, timedelta, date
import pytz
from functools import wraps
from utils.logger import log_error

dashboard_gamification_bp = Blueprint('dashboard_gamification', __name__)

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

@dashboard_gamification_bp.route('/dashboard/challenges')
@token_required
def challenge_hub():
    """Render challenge hub page"""
    try:
        from app import supabase
        
        profile_key = f'{request.user_type}_id'
        profile = supabase.table('gamification_profiles').select('*').eq(
            profile_key, request.user['id']
        ).single().execute()
        
        if not profile.data:
            profile_data = {
                profile_key: request.user['id'],
                'points_total': 0,
                'is_public': True,
                'opted_in_global': True,
                'opted_in_trainer': True,
                'notification_style': 'daily_digest',
                'digest_time': '07:00',
                'quiet_start': '20:00',
                'quiet_end': '06:00'
            }
            profile = supabase.table('gamification_profiles').insert(
                profile_data
            ).execute()
            profile = {'data': profile.data[0] if profile.data else profile_data}
        
        return render_template('challenge_hub.html',
            user=request.user,
            user_type=request.user_type,
            profile=profile.data,
            token=request.token
        )
        
    except Exception as e:
        return f"Error loading challenge hub: {str(e)}", 500

@dashboard_gamification_bp.route('/api/dashboard/challenges/active', methods=['GET'])
@token_required
def get_active_challenges():
    """Get user's active challenges"""
    try:
        from app import supabase
        
        participants = supabase.table('challenge_participants').select(
            '*, challenges(*)'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).eq('status', 'active').execute()
        
        challenges = []
        for p in (participants.data or []):
            if p.get('challenges'):
                challenge = p['challenges']
                
                progress = supabase.table('challenge_progress').select('*').eq(
                    'participant_id', p['id']
                ).execute()
                
                total_progress = sum(
                    pr.get('value_achieved', 0) 
                    for pr in (progress.data or [])
                )
                
                target = challenge.get('target_value', 1)
                percentage = min(100, int((total_progress / target) * 100))
                
                challenges.append({
                    'id': challenge['id'],
                    'name': challenge['name'],
                    'description': challenge['description'],
                    'progress': total_progress,
                    'target': target,
                    'percentage': percentage,
                    'end_date': challenge['end_date'],
                    'points_reward': challenge['points_reward'],
                    'participant_id': p['id']
                })
        
        return jsonify(challenges)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_gamification_bp.route('/api/dashboard/challenges/pre-book', methods=['POST'])
@token_required
def pre_book_challenge():
    """Pre-book a challenge"""
    try:
        from app import supabase
        
        data = request.json
        challenge_id = data.get('challenge_id')
        
        if not challenge_id:
            return jsonify({'error': 'Challenge ID required'}), 400
        
        existing = supabase.table('challenge_pre_bookings').select('id').eq(
            'user_id', request.user['id']
        ).eq('user_type', request.user_type).eq(
            'challenge_id', challenge_id
        ).execute()
        
        if existing.data:
            return jsonify({'message': 'Already pre-booked'}), 200
        
        booking = supabase.table('challenge_pre_bookings').insert({
            'user_id': request.user['id'],
            'user_type': request.user_type,
            'challenge_id': challenge_id,
            'booked_at': datetime.now().isoformat()
        }).execute()
        
        return jsonify({
            'success': True,
            'message': 'Challenge pre-booked successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_gamification_bp.route('/api/dashboard/leaderboard/<type>', methods=['GET'])
@token_required
def get_leaderboard(type):
    """Get leaderboard data"""
    try:
        from app import supabase
        from collections import Counter
        
        valid_types = ['global', 'trainer', 'challenge']
        if type not in valid_types:
            return jsonify({'error': 'Invalid leaderboard type'}), 400
        
        if type == 'global':
            leaderboard = supabase.table('leaderboards').select('*').eq(
                'type', 'global'
            ).eq('is_active', True).single().execute()
        elif type == 'trainer' and request.user_type == 'client':
            client = supabase.table('clients').select('trainer_id').eq(
                'id', request.user['id']
            ).single().execute()
            
            if not client.data:
                return jsonify({'error': 'No trainer found'}), 404
                
            leaderboard = supabase.table('leaderboards').select('*').eq(
                'type', 'trainer_group'
            ).eq('scope', client.data['trainer_id']).eq(
                'is_active', True
            ).single().execute()
        else:
            challenge_id = request.args.get('challenge_id')
            if not challenge_id:
                return jsonify({'error': 'Challenge ID required'}), 400
                
            leaderboard = supabase.table('leaderboards').select('*').eq(
                'type', 'challenge'
            ).eq('scope', challenge_id).eq(
                'is_active', True
            ).single().execute()
        
        if not leaderboard.data:
            return jsonify({'error': 'Leaderboard not found'}), 404
        
        entries = supabase.table('leaderboard_entries').select('*').eq(
            'leaderboard_id', leaderboard.data['id']
        ).order('rank').execute()
        
        user_entry = None
        user_rank = None
        
        for entry in (entries.data or []):
            if (entry['user_id'] == request.user['id'] and 
                entry['user_type'] == request.user_type):
                user_entry = entry
                user_rank = entry['rank']
                break
        
        response = {
            'leaderboard': {
                'id': leaderboard.data['id'],
                'name': leaderboard.data['name'],
                'type': leaderboard.data['type']
            },
            'top_10': [],
            'user_context': None,
            'user_stats': None,
            'total_participants': len(entries.data) if entries.data else 0
        }
        
        for entry in (entries.data or [])[:10]:
            response['top_10'].append({
                'rank': entry['rank'],
                'nickname': entry.get('nickname', 'Anonymous'),
                'points': entry['points'],
                'trend': entry.get('trend', 'same'),
                'trend_value': abs(entry.get('previous_rank', entry['rank']) - entry['rank']),
                'is_user': (entry['user_id'] == request.user['id'] and 
                           entry['user_type'] == request.user_type)
            })
        
        if user_rank and user_rank > 10:
            context = []
            start_idx = max(0, user_rank - 3)
            end_idx = min(len(entries.data), user_rank + 2)
            
            for i in range(start_idx, end_idx):
                entry = entries.data[i]
                context.append({
                    'rank': entry['rank'],
                    'nickname': entry.get('nickname', 'Anonymous'),
                    'points': entry['points'],
                    'trend': entry.get('trend', 'same'),
                    'trend_value': abs(entry.get('previous_rank', entry['rank']) - entry['rank']),
                    'is_user': (entry['user_id'] == request.user['id'] and 
                               entry['user_type'] == request.user_type)
                })
            
            response['user_context'] = context
        
        if user_entry:
            points_to_next = 0
            if user_rank > 1:
                prev_entry = entries.data[user_rank - 2]
                points_to_next = prev_entry['points'] - user_entry['points']
            
            points_to_top10 = 0
            if user_rank > 10:
                top10_entry = entries.data[9]
                points_to_top10 = top10_entry['points'] - user_entry['points']
            
            percentile = round((1 - (user_rank / len(entries.data))) * 100)
            
            response['user_stats'] = {
                'rank': user_rank,
                'points': user_entry['points'],
                'trend': user_entry.get('trend', 'same'),
                'trend_value': abs(user_entry.get('previous_rank', user_rank) - user_rank),
                'points_to_next': points_to_next,
                'points_to_top10': points_to_top10,
                'percentile': percentile,
                'best_rank': user_entry.get('best_rank', user_rank)
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### EDIT: routes/dashboard.py

**Change 1:** Replace entire file with base dashboard routes only
Location: Lines 1-817
```python
# REMOVE (lines 1-817):
[entire current content]

# ADD:
"""Main dashboard routes"""
from flask import Blueprint, jsonify, request
from routes.dashboard_calendar import dashboard_calendar_bp
from routes.dashboard_gamification import dashboard_gamification_bp

# Create main dashboard blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Register sub-blueprints
dashboard_bp.register_blueprint(dashboard_calendar_bp)
dashboard_bp.register_blueprint(dashboard_gamification_bp)

@dashboard_bp.route('/api/dashboard/preferences', methods=['GET', 'PUT'])
def handle_preferences():
    """Handle user preferences"""
    from routes.dashboard_gamification import token_required
    
    @token_required
    def _handle():
        from app import supabase
        
        if request.method == 'GET':
            profile_key = f'{request.user_type}_id'
            profile = supabase.table('gamification_profiles').select('*').eq(
                profile_key, request.user['id']
            ).single().execute()
            
            if profile.data:
                return jsonify(profile.data)
            else:
                return jsonify({
                    'notification_style': 'daily_digest',
                    'digest_time': '07:00',
                    'quiet_start': '20:00',
                    'quiet_end': '06:00',
                    'opted_in_global': True,
                    'opted_in_trainer': True,
                    'is_public': True
                })
        
        elif request.method == 'PUT':
            data = request.json
            profile_key = f'{request.user_type}_id'
            
            existing = supabase.table('gamification_profiles').select('id').eq(
                profile_key, request.user['id']
            ).single().execute()
            
            allowed_fields = [
                'nickname', 'notification_style', 'digest_time',
                'quiet_start', 'quiet_end', 'opted_in_global',
                'opted_in_trainer', 'is_public'
            ]
            
            updates = {k: v for k, v in data.items() if k in allowed_fields}
            
            if existing.data:
                result = supabase.table('gamification_profiles').update(
                    updates
                ).eq(profile_key, request.user['id']).execute()
            else:
                updates[profile_key] = request.user['id']
                updates['points_total'] = 0
                result = supabase.table('gamification_profiles').insert(
                    updates
                ).execute()
            
            return jsonify(result.data[0] if result.data else {'success': True})
    
    return _handle()

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_user_stats():
    """Get user's gamification stats"""
    from routes.dashboard_gamification import token_required
    
    @token_required  
    def _get_stats():
        from app import supabase
        
        profile_key = f'{request.user_type}_id'
        
        profile = supabase.table('gamification_profiles').select('*').eq(
            profile_key, request.user['id']
        ).single().execute()
        
        if not profile.data:
            return jsonify({
                'points_total': 0,
                'badges': [],
                'challenges_won': 0,
                'current_streak': 0
            })
        
        badges = supabase.table('user_badges').select(
            '*, badges(*)'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).order('earned_at', desc=True).execute()
        
        wins = supabase.table('challenge_participants').select(
            'id', count='exact'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).eq('final_position', 1).execute()
        
        return jsonify({
            'points_total': profile.data.get('points_total', 0),
            'badges': [
                {
                    'name': b['badges']['name'],
                    'description': b['badges']['description'],
                    'icon': b['badges']['icon_emoji'],
                    'earned_at': b['earned_at']
                }
                for b in (badges.data or [])
                if b.get('badges')
            ],
            'challenges_won': wins.count if wins else 0,
            'current_streak': 0
        })
    
    return _get_stats()
```

### NEW FILE: services/ai_intent_core.py
```python
"""Core AI intent detection functionality"""
import json
import anthropic
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning

class AIIntentCore:
    """Core AI intent detection"""
    
    def __init__(self, config):
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        if config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"
            log_info("AI Intent Handler initialized with Claude")
        else:
            self.client = None
            log_warning("No Anthropic API key - falling back to keyword matching")
    
    def understand_message(self, message: str, sender_type: str,
                          sender_data: Dict, conversation_history: List[str] = None) -> Dict:
        """Main entry point - understands any message using AI"""
        
        if not self.client:
            log_info(f"Using fallback intent detection for: {message[:50]}")
            return self._fallback_intent_detection(message, sender_type)
        
        try:
            context = self._build_context(sender_type, sender_data)
            prompt = self._create_intent_prompt(message, sender_type, context, conversation_history)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            intent_data = self._parse_ai_response(response.content[0].text)
            validated_intent = self._validate_intent(intent_data, sender_data, sender_type)
            
            log_info(f"AI Intent detected: {validated_intent.get('primary_intent')} "
                    f"with confidence {validated_intent.get('confidence')}")
            
            return validated_intent
            
        except Exception as e:
            log_error(f"AI intent understanding failed: {str(e)}", exc_info=True)
            return self._fallback_intent_detection(message, sender_type)
    
    def _build_context(self, sender_type: str, sender_data: Dict) -> Dict:
        """Build context based on sender type"""
        if sender_type == 'trainer':
            return {
                'name': sender_data.get('name', 'Trainer'),
                'id': sender_data.get('id'),
                'whatsapp': sender_data.get('whatsapp'),
                'business_name': sender_data.get('business_name'),
                'active_clients': sender_data.get('active_clients', 0)
            }
        else:
            return {
                'name': sender_data.get('name', 'Client'),
                'id': sender_data.get('id'),
                'whatsapp': sender_data.get('whatsapp'),
                'trainer_name': sender_data.get('trainer_name', 'your trainer'),
                'sessions_remaining': sender_data.get('sessions_remaining', 0)
            }
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse the AI's JSON response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI response: {e}")
            return {
                'primary_intent': 'unclear',
                'confidence': 0.3,
                'extracted_data': {},
                'sentiment': 'neutral',
                'suggested_response_type': 'conversational'
            }
    
    def _validate_intent(self, intent_data: Dict, sender_data: Dict, sender_type: str) -> Dict:
        """Validate and enrich the AI's intent understanding"""
        intent_data.setdefault('primary_intent', 'general_question')
        intent_data.setdefault('confidence', 0.5)
        intent_data.setdefault('extracted_data', {})
        intent_data.setdefault('requires_confirmation', False)
        intent_data.setdefault('suggested_response_type', 'conversational')
        intent_data.setdefault('conversation_tone', 'friendly')
        return intent_data
    
    def _fallback_intent_detection(self, message: str, sender_type: str) -> Dict:
        """Basic keyword-based intent detection when AI is unavailable"""
        message_lower = message.lower()
        
        casual_keywords = {
            'status_check': ['are you there', 'you there', 'still there'],
            'greeting': ['hi', 'hello', 'hey', 'howzit', 'sawubona'],
            'thanks': ['thanks', 'thank you', 'appreciate'],
            'farewell': ['bye', 'goodbye', 'see you'],
            'casual_chat': ['how are you', 'what\'s up'],
        }
        
        for intent, keywords in casual_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return {
                        'primary_intent': intent,
                        'secondary_intents': [],
                        'confidence': 0.8,
                        'extracted_data': {},
                        'sentiment': 'friendly',
                        'requires_confirmation': False,
                        'suggested_response_type': 'conversational',
                        'conversation_tone': 'casual',
                        'is_follow_up': False
                    }
        
        return {
            'primary_intent': 'general_question',
            'secondary_intents': [],
            'confidence': 0.3,
            'extracted_data': {},
            'sentiment': 'neutral',
            'requires_confirmation': False,
            'suggested_response_type': 'task',
            'conversation_tone': 'friendly',
            'is_follow_up': False
        }

    def _create_intent_prompt(self, message: str, sender_type: str, 
                             context: Dict, history: List[str]) -> str:
        """Create prompt for Claude"""
        return f"""Analyze this WhatsApp message to Refiloe, an AI assistant for personal trainers.

SENDER: {sender_type} ({context.get('name', 'Unknown')})
MESSAGE: "{message}"

Return ONLY valid JSON with primary_intent, confidence, extracted_data, sentiment, and suggested_response_type."""
```

### EDIT: services/ai_intent_handler.py

**Change 1:** Import core functionality and reduce to handler logic only
Location: Lines 1-649
```python
# REMOVE (lines 1-649):
[entire current content]

# ADD:
"""AI Intent Handler - routes intents to appropriate handlers"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pytz
from services.ai_intent_core import AIIntentCore
from utils.logger import log_info, log_error

class AIIntentHandler:
    """Handle all message understanding through AI first"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.core = AIIntentCore(config)
    
    def understand_message(self, message: str, sender_type: str,
                          sender_data: Dict, conversation_history: List[str] = None) -> Dict:
        """Delegate to core for understanding"""
        return self.core.understand_message(message, sender_type, sender_data, conversation_history)
    
    def generate_smart_response(self, intent_data: Dict, sender_type: str, 
                               sender_data: Dict) -> str:
        """Generate a contextual response when no specific handler exists"""
        import random
        
        intent = intent_data.get('primary_intent')
        name = sender_data.get('name', 'there')
        
        casual_responses = {
            'status_check': [
                f"Yes {name}, I'm here! 😊 Just chilling in the cloud, ready when you need me.",
                f"I'm always here for you, {name}! 24/7, rain or shine ☀️",
                f"Yep, still here {name}! Not going anywhere 😄",
                f"Present and accounted for! What's on your mind, {name}?"
            ],
            'casual_chat': [
                f"I'm doing great, {name}! Just here helping trainers and clients stay fit. How are things with you?",
                f"All good on my end! How's your day going, {name}?",
                f"Can't complain - living the AI dream! 😄 How are you doing?",
                f"I'm well, thanks for asking! How's the fitness world treating you?"
            ],
            'thanks': [
                f"You're welcome, {name}! Always happy to help 😊",
                f"My pleasure! That's what I'm here for 💪",
                f"Anytime, {name}! 🙌",
                f"No worries at all! Glad I could help."
            ],
            'farewell': [
                f"Chat soon, {name}! Have an awesome day! 👋",
                f"Later, {name}! Stay strong! 💪",
                f"Bye {name}! Catch you later 😊",
                f"See you soon! Don't be a stranger!"
            ]
        }
        
        if intent in casual_responses:
            return random.choice(casual_responses[intent])
        
        if intent == 'greeting':
            greetings = [
                f"Hey {name}! 👋",
                f"Hi {name}! Good to hear from you 😊",
                f"Hello {name}! How's it going?",
                f"Hey there {name}! 🙌"
            ]
            return random.choice(greetings)
        elif intent == 'unclear':
            return f"I didn't quite catch that, {name}. Could you rephrase that for me?"
        else:
            return f"Let me help you with that, {name}. What specifically would you like to know?"
    
    def process_habit_responses(self, responses: List) -> List[Dict]:
        """Process various habit response formats into structured data"""
        processed = []
        
        for response in responses:
            response_lower = str(response).lower()
            
            if response_lower in ['yes', '✅', 'done', 'complete', '👍']:
                processed.append({'completed': True, 'value': None})
            elif response_lower in ['no', '❌', 'skip', 'missed', '👎']:
                processed.append({'completed': False, 'value': None})
            elif response_lower.replace('.', '').isdigit():
                processed.append({'completed': True, 'value': float(response_lower)})
            elif '/' in response_lower:
                parts = response_lower.split('/')
                if len(parts) == 2 and parts[0].isdigit():
                    processed.append({'completed': True, 'value': float(parts[0])})
            else:
                import re
                numbers = re.findall(r'\d+', response_lower)
                if numbers:
                    processed.append({'completed': True, 'value': float(numbers[0])})
                else:
                    processed.append({'completed': False, 'value': None})
        
        return processed
    
    def fuzzy_match_client(self, search_name: str, trainer_id: str) -> Optional[Dict]:
        """Find best matching client name"""
        clients = self.db.table('clients').select('id, name').eq(
            'trainer_id', trainer_id
        ).execute()
        
        if not clients.data:
            return None
        
        search_lower = search_name.lower()
        
        for client in clients.data:
            client_lower = client['name'].lower()
            if search_lower == client_lower:
                return client
            if search_lower in client_lower or client_lower in search_lower:
                return client
            if search_lower.split()[0] == client_lower.split()[0]:
                return client
        
        return None
    
    def parse_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse various datetime formats to SA timezone"""
        from dateutil import parser
        import re
        
        try:
            time_lower = time_str.lower()
            now = datetime.now(self.sa_tz)
            
            if 'tomorrow' in time_lower:
                base_date = now + timedelta(days=1)
            elif 'today' in time_lower:
                base_date = now
            elif 'monday' in time_lower:
                days_ahead = 0 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                base_date = now + timedelta(days=days_ahead)
            else:
                parsed = parser.parse(time_str, fuzzy=True)
                return self.sa_tz.localize(parsed) if parsed.tzinfo is None else parsed
            
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                meridiem = time_match.group(3)
                
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
        except Exception as e:
            log_error(f"Error parsing datetime '{time_str}': {str(e)}")
            return None
```

## SUMMARY

✅ **Completed splitting large files:**
- Split `routes/dashboard.py` (817 lines) into:
  - `routes/dashboard_calendar.py` - Calendar-specific routes
  - `routes/dashboard_gamification.py` - Gamification routes  
  - `routes/dashboard.py` - Main blueprint registration (reduced to ~150 lines)

- Split `services/ai_intent_handler.py` (649 lines) into:
  - `services/ai_intent_core.py` - Core AI detection logic
  - `services/ai_intent_handler.py` - Handler logic (reduced to ~180 lines)

**CONTINUE_NEEDED** - Still need to split:
- `payment_integration.py` (746 lines)
- `services/dashboard_sync.py` (640 lines)