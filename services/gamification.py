from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional
from utils.logger import log_error, log_info

class BadgeChecker:
    """Handles badge evaluation and awarding"""
    
    def __init__(self, config, supabase_client, whatsapp_service):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
    def check_badges(self, user_id: str, user_type: str = 'client') -> List[Dict]:
        """Check if user has earned any new badges"""
        try:
            # Get all available badges
            badges = self.db.table('badges').select('*').execute()
            
            # Get user's existing badges
            user_badges = self.db.table('user_badges').select('badge_id').eq(
                'user_id', user_id
            ).eq('user_type', user_type).execute()
            
            earned_badge_ids = [b['badge_id'] for b in (user_badges.data or [])]
            newly_earned = []
            
            for badge in (badges.data or []):
                # Skip if already earned
                if badge['id'] in earned_badge_ids:
                    continue
                
                # Check if badge criteria is met
                if self._check_badge_criteria(user_id, user_type, badge):
                    # Award the badge
                    self._award_badge(user_id, user_type, badge)
                    newly_earned.append(badge)
            
            return newly_earned
            
        except Exception as e:
            log_error(f"Error checking badges: {str(e)}")
            return []
    
    def _check_badge_criteria(self, user_id: str, user_type: str, badge: Dict) -> bool:
        """Check if user meets badge criteria"""
        try:
            criteria_type = badge['criteria_type']
            criteria_value = badge['criteria_value']
            
            if criteria_type == 'first_workout':
                # Check if user has completed at least one workout
                result = self.db.table('workout_history').select('id').eq(
                    f'{user_type}_id', user_id
                ).eq('completed', True).limit(1).execute()
                return bool(result.data)
                
            elif criteria_type == 'workout_streak':
                # Check workout streak
                streak = self._get_current_streak(user_id, user_type)
                return streak >= criteria_value
                
            elif criteria_type == 'challenge_wins':
                # Check challenge wins
                result = self.db.table('challenge_history').select('id').eq(
                    f'{user_type}_id', user_id
                ).eq('status', 'won').execute()
                return len(result.data or []) >= criteria_value
                
            elif criteria_type == 'points_milestone':
                # Check total points
                result = self.db.table('user_points').select('total_points').eq(
                    f'{user_type}_id', user_id
                ).single().execute()
                if result.data:
                    return result.data['total_points'] >= criteria_value
            
            return False
            
        except Exception as e:
            log_error(f"Error checking badge criteria: {str(e)}")
            return False
    
    def _award_badge(self, user_id: str, user_type: str, badge: Dict):
        """Award badge to user"""
        try:
            # Add badge to user's collection
            self.db.table('user_badges').insert({
                'user_id': user_id,
                'user_type': user_type,
                'badge_id': badge['id'],
                'earned_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Award points if specified
            if badge.get('points_value'):
                self._add_points(user_id, user_type, badge['points_value'])
            
            # Get user's contact info
            if user_type == 'client':
                user = self.db.table('clients').select('name, whatsapp').eq(
                    'id', user_id
                ).single().execute()
            else:
                user = self.db.table('trainers').select('name, whatsapp').eq(
                    'id', user_id
                ).single().execute()
            
            if user.data:
                # Send WhatsApp notification
                message = f"""🏆 *Achievement Unlocked!*

Congratulations {user.data['name']}!
You've earned the {badge['icon_emoji']} *{badge['name']}* badge!

_{badge['description']}_

+{badge['points_value']} points added to your profile! 🌟"""
                
                self.whatsapp.send_message(user.data['whatsapp'], message)
            
        except Exception as e:
            log_error(f"Error awarding badge: {str(e)}")
    
    def _add_points(self, user_id: str, user_type: str, points: int):
        """Add points to user's total"""
        try:
            # Get current points
            result = self.db.table('user_points').select('total_points').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if result.data:
                # Update existing
                new_total = result.data['total_points'] + points
                self.db.table('user_points').update({
                    'total_points': new_total,
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq(f'{user_type}_id', user_id).execute()
            else:
                # Create new entry
                self.db.table('user_points').insert({
                    f'{user_type}_id': user_id,
                    'total_points': points,
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
            
        except Exception as e:
            log_error(f"Error adding points: {str(e)}")
    
    def _get_current_streak(self, user_id: str, user_type: str) -> int:
        """Calculate current workout streak"""
        try:
            # Get workouts ordered by date
            result = self.db.table('workout_history').select('*').eq(
                f'{user_type}_id', user_id
            ).order('completed_at', desc=True).execute()
            
            if not result.data:
                return 0
            
            streak = 0
            last_date = None
            
            for workout in result.data:
                workout_date = datetime.fromisoformat(workout['completed_at']).date()
                
                if last_date is None:
                    last_date = workout_date
                    streak = 1
                    continue
                
                # Check if this workout is consecutive
                date_diff = (last_date - workout_date).days
                
                if date_diff == 1:
                    streak += 1
                    last_date = workout_date
                else:
                    break
            
            return streak
            
        except Exception as e:
            log_error(f"Error calculating streak: {str(e)}")
            return 0