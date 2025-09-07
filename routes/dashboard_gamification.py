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