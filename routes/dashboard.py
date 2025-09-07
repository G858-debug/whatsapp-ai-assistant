from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from datetime import datetime, timedelta
import pytz
from functools import wraps
import secrets

dashboard_bp = Blueprint('dashboard', __name__)

def token_required(f):
    """Verify dashboard access token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            # Check for token in session for web views
            token = request.args.get('token')
            
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        # Import here to avoid circular imports
        from app import supabase
        
        # Verify token and get trainer/client info
        result = supabase.table('dashboard_tokens').select(
            '*, trainers(*), clients(*)'
        ).eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 401
            
        # Determine if trainer or client
        if result.data.get('trainers'):
            request.user = result.data['trainers']
            request.user_type = 'trainer'
        else:
            request.user = result.data['clients']
            request.user_type = 'client'
            
        request.token = token
        return f(*args, **kwargs)
        
    return decorated

# ============= EXISTING CALENDAR ROUTES =============

@dashboard_bp.route('/api/dashboard/calendar/day', methods=['GET'])
@token_required
def get_day_sessions():
    """Get all sessions for a specific day"""
    try:
        from app import supabase
        
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date parameter required'}), 400
            
        # Parse date
        try:
            day_date = datetime.fromisoformat(date)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
        # Get sessions for this day
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
        
        # Format response
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

@dashboard_bp.route('/api/dashboard/calendar/day/session', methods=['POST'])
@token_required
def create_session():
    """Create a new session"""
    try:
        from app import supabase
        
        data = request.json
        required = ['client_id', 'date', 'start_time', 'end_time']
        
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Validate client belongs to trainer
        client = supabase.table('clients').select('*').eq(
            'id', data['client_id']
        ).eq('trainer_id', request.user['id']).single().execute()
        
        if not client.data:
            return jsonify({'error': 'Invalid client'}), 400
            
        # Create session
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

@dashboard_bp.route('/api/dashboard/calendar/day/session/<id>', methods=['PUT'])
@token_required
def update_session(id):
    """Update a session"""
    try:
        from app import supabase
        
        data = request.json
        
        # Verify session belongs to trainer
        session = supabase.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.user['id']).single().execute()
        
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
            updated = supabase.table('bookings').update(
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
        from app import supabase
        
        # Verify session belongs to trainer
        session = supabase.table('bookings').select('*').eq(
            'id', id
        ).eq('trainer_id', request.user['id']).single().execute()
        
        if not session.data:
            return jsonify({'error': 'Session not found'}), 404
            
        # Delete session
        supabase.table('bookings').delete().eq('id', id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= NEW GAMIFICATION ROUTES =============

@dashboard_bp.route('/dashboard/challenges')
@token_required
def challenge_hub():
    """Render challenge hub page"""
    try:
        from app import supabase
        
        # Get user's gamification profile
        profile_key = f'{request.user_type}_id'
        profile = supabase.table('gamification_profiles').select('*').eq(
            profile_key, request.user['id']
        ).single().execute()
        
        # If no profile, create default
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

@dashboard_bp.route('/dashboard/preferences')
@token_required
def preferences():
    """Render preferences page"""
    try:
        from app import supabase
        
        # Get user's gamification profile
        profile_key = f'{request.user_type}_id'
        profile = supabase.table('gamification_profiles').select('*').eq(
            profile_key, request.user['id']
        ).single().execute()
        
        if not profile.data:
            # Create default profile
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
        
        return render_template('preferences.html',
            user=request.user,
            user_type=request.user_type,
            profile=profile.data,
            token=request.token
        )
        
    except Exception as e:
        return f"Error loading preferences: {str(e)}", 500

@dashboard_bp.route('/api/dashboard/preferences', methods=['GET'])
@token_required
def get_preferences():
    """Get user preferences as JSON"""
    try:
        from app import supabase
        
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
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/preferences', methods=['PUT'])
@token_required
def update_preferences():
    """Update user preferences"""
    try:
        from app import supabase
        
        data = request.json
        profile_key = f'{request.user_type}_id'
        
        # Check if profile exists
        existing = supabase.table('gamification_profiles').select('id').eq(
            profile_key, request.user['id']
        ).single().execute()
        
        # Allowed fields to update
        allowed_fields = [
            'nickname', 'notification_style', 'digest_time',
            'quiet_start', 'quiet_end', 'opted_in_global',
            'opted_in_trainer', 'is_public'
        ]
        
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if existing.data:
            # Update existing profile
            result = supabase.table('gamification_profiles').update(
                updates
            ).eq(profile_key, request.user['id']).execute()
        else:
            # Create new profile
            updates[profile_key] = request.user['id']
            updates['points_total'] = 0
            result = supabase.table('gamification_profiles').insert(
                updates
            ).execute()
        
        return jsonify(result.data[0] if result.data else {'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/challenges/active', methods=['GET'])
@token_required
def get_active_challenges():
    """Get user's active challenges"""
    try:
        from app import supabase
        
        # Get challenges user is participating in
        participants = supabase.table('challenge_participants').select(
            '*, challenges(*)'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).eq('status', 'active').execute()
        
        challenges = []
        for p in (participants.data or []):
            if p.get('challenges'):
                challenge = p['challenges']
                
                # Get user's progress
                progress = supabase.table('challenge_progress').select('*').eq(
                    'participant_id', p['id']
                ).execute()
                
                total_progress = sum(
                    pr.get('value_achieved', 0) 
                    for pr in (progress.data or [])
                )
                
                # Calculate percentage
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

@dashboard_bp.route('/api/dashboard/challenges/upcoming', methods=['GET'])
@token_required
def get_upcoming_challenges():
    """Get upcoming challenges available to join"""
    try:
        from app import supabase
        from datetime import date
        
        today = date.today()
        week_from_now = today + timedelta(days=7)
        
        # Get challenges starting in next 7 days
        challenges = supabase.table('challenges').select('*').gte(
            'start_date', today.isoformat()
        ).lte('start_date', week_from_now.isoformat()).eq(
            'is_active', True
        ).execute()
        
        # Check which ones user has pre-booked
        pre_bookings = supabase.table('challenge_pre_bookings').select(
            'challenge_id'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).execute()
        
        pre_booked_ids = [b['challenge_id'] for b in (pre_bookings.data or [])]
        
        # Get participant counts
        formatted = []
        for challenge in (challenges.data or []):
            # Count participants
            count = supabase.table('challenge_participants').select(
                'id', count='exact'
            ).eq('challenge_id', challenge['id']).execute()
            
            formatted.append({
                'id': challenge['id'],
                'name': challenge['name'],
                'description': challenge['description'],
                'start_date': challenge['start_date'],
                'end_date': challenge['end_date'],
                'duration_days': (
                    datetime.fromisoformat(challenge['end_date']) - 
                    datetime.fromisoformat(challenge['start_date'])
                ).days,
                'target_value': challenge['target_value'],
                'points_reward': challenge['points_reward'],
                'participant_count': count.count if count else 0,
                'is_pre_booked': challenge['id'] in pre_booked_ids,
                'challenge_type': challenge.get('challenge_rules', {}).get('challenge_type', 'custom')
            })
        
        return jsonify(formatted)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/challenges/pre-book', methods=['POST'])
@token_required
def pre_book_challenge():
    """Pre-book a challenge"""
    try:
        from app import supabase
        
        data = request.json
        challenge_id = data.get('challenge_id')
        
        if not challenge_id:
            return jsonify({'error': 'Challenge ID required'}), 400
        
        # Check if already pre-booked
        existing = supabase.table('challenge_pre_bookings').select('id').eq(
            'user_id', request.user['id']
        ).eq('user_type', request.user_type).eq(
            'challenge_id', challenge_id
        ).execute()
        
        if existing.data:
            return jsonify({'message': 'Already pre-booked'}), 200
        
        # Create pre-booking
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

@dashboard_bp.route('/api/dashboard/challenges/leave', methods=['POST'])
@token_required
def leave_challenge():
    """Leave an active challenge"""
    try:
        from app import supabase
        
        data = request.json
        participant_id = data.get('participant_id')
        
        if not participant_id:
            return jsonify({'error': 'Participant ID required'}), 400
        
        # Verify this participant belongs to user
        participant = supabase.table('challenge_participants').select('*').eq(
            'id', participant_id
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).single().execute()
        
        if not participant.data:
            return jsonify({'error': 'Invalid participant'}), 404
        
        # Update status to left
        supabase.table('challenge_participants').update({
            'status': 'left',
            'left_at': datetime.now().isoformat()
        }).eq('id', participant_id).execute()
        
        return jsonify({'success': True, 'message': 'Left challenge'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/leaderboard/<type>', methods=['GET'])
@token_required
def get_leaderboard(type):
    """Get leaderboard data"""
    try:
        from app import supabase
        
        # Validate type
        valid_types = ['global', 'trainer', 'challenge']
        if type not in valid_types:
            return jsonify({'error': 'Invalid leaderboard type'}), 400
        
        # Get appropriate leaderboard
        if type == 'global':
            leaderboard = supabase.table('leaderboards').select('*').eq(
                'type', 'global'
            ).eq('is_active', True).single().execute()
        elif type == 'trainer' and request.user_type == 'client':
            # Get client's trainer
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
            # For challenge, need challenge_id parameter
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
        
        # Get entries
        entries = supabase.table('leaderboard_entries').select('*').eq(
            'leaderboard_id', leaderboard.data['id']
        ).order('rank').execute()
        
        # Find user's position
        user_entry = None
        user_rank = None
        
        for entry in (entries.data or []):
            if (entry['user_id'] == request.user['id'] and 
                entry['user_type'] == request.user_type):
                user_entry = entry
                user_rank = entry['rank']
                break
        
        # Format response
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
        
        # Add top 10
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
        
        # Add user context if not in top 10
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
        
        # Add user stats
        if user_entry:
            # Calculate points to next rank
            points_to_next = 0
            if user_rank > 1:
                prev_entry = entries.data[user_rank - 2]
                points_to_next = prev_entry['points'] - user_entry['points']
            
            # Calculate points to top 10
            points_to_top10 = 0
            if user_rank > 10:
                top10_entry = entries.data[9]
                points_to_top10 = top10_entry['points'] - user_entry['points']
            
            # Calculate percentile
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

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
@token_required  
def get_user_stats():
    """Get user's gamification stats"""
    try:
        from app import supabase
        
        profile_key = f'{request.user_type}_id'
        
        # Get profile
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
        
        # Get badges
        badges = supabase.table('user_badges').select(
            '*, badges(*)'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).order('earned_at', desc=True).execute()
        
        # Get challenge wins
        wins = supabase.table('challenge_participants').select(
            'id', count='exact'
        ).eq('user_id', request.user['id']).eq(
            'user_type', request.user_type
        ).eq('final_position', 1).execute()
        
        # Format response
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
            'current_streak': 0  # Calculate based on activity
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= TRAINER-SPECIFIC ROUTES =============

@dashboard_bp.route('/api/dashboard/challenges/create', methods=['POST'])
@token_required
def create_challenge():
    """Create a new challenge (trainers only)"""
    try:
        if request.user_type != 'trainer':
            return jsonify({'error': 'Only trainers can create challenges'}), 403
        
        from app import supabase
        from services.gamification import ChallengeManager
        
        data = request.json
        required = ['name', 'challenge_type', 'duration_days']
        
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Initialize challenge manager
        from config import Config
        from services.whatsapp import WhatsAppService
        
        whatsapp = WhatsAppService(Config, supabase, None)
        manager = ChallengeManager(Config, supabase, whatsapp)
        
        # Create challenge
        result = manager.create_challenge(
            trainer_id=request.user['id'],
            name=data['name'],
            challenge_type=data['challenge_type'],
            duration_days=data['duration_days'],
            target_value=data.get('target_value'),
            description=data.get('description'),
            max_participants=data.get('max_participants')
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/challenges/invite', methods=['POST'])
@token_required
def invite_to_challenge():
    """Invite clients to challenge (trainers only)"""
    try:
        if request.user_type != 'trainer':
            return jsonify({'error': 'Only trainers can invite to challenges'}), 403
        
        from app import supabase
        from services.gamification import ChallengeManager
        from config import Config
        from services.whatsapp import WhatsAppService
        
        data = request.json
        challenge_id = data.get('challenge_id')
        client_ids = data.get('client_ids', [])
        
        if not challenge_id:
            return jsonify({'error': 'Challenge ID required'}), 400
        
        # Initialize services
        whatsapp = WhatsAppService(Config, supabase, None)
        manager = ChallengeManager(Config, supabase, whatsapp)
        
        # Send invitations
        result = manager.invite_clients_to_challenge(
            trainer_id=request.user['id'],
            challenge_id=challenge_id,
            client_ids=client_ids if client_ids else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
