from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class GamificationService:
    """Handles challenges, points and gamification features"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
    def get_challenge_library(self) -> List[Dict]:
        """Return pre-defined challenge templates"""
        return {
            'daily': [
                {
                    'name': 'Water Wednesday',
                    'description': 'Drink 2L of water today',
                    'duration_days': 1,
                    'target_value': 2.0,
                    'unit': 'liters',
                    'points_reward': 50,
                    'challenge_type': 'water_intake'
                },
                {
                    'name': 'Move It Monday',
                    'description': 'Complete 10,000 steps',
                    'duration_days': 1,
                    'target_value': 10000,
                    'unit': 'steps',
                    'points_reward': 50,
                    'challenge_type': 'steps'
                },
                {
                    'name': 'Early Bird',
                    'description': 'Complete morning workout before 8am',
                    'duration_days': 1,
                    'target_value': 1,
                    'unit': 'workout',
                    'points_reward': 75,
                    'challenge_type': 'workout'
                }
            ],
            'short': [
                {
                    'name': 'Hydration Hero',
                    'description': 'Hit daily water goals for 3 days',
                    'duration_days': 3,
                    'target_value': 6.0,
                    'unit': 'liters',
                    'points_reward': 150,
                    'challenge_type': 'water_intake'
                },
                {
                    'name': 'Step Up',
                    'description': 'Complete 30,000 steps in 3 days',
                    'duration_days': 3,
                    'target_value': 30000,
                    'unit': 'steps',
                    'points_reward': 150,
                    'challenge_type': 'steps'
                }
            ],
            'weekly': [
                {
                    'name': '7K for 7 Days',
                    'description': 'Walk 7000 steps daily for a week',
                    'duration_days': 7,
                    'target_value': 49000,
                    'unit': 'steps',
                    'points_reward': 350,
                    'challenge_type': 'steps'
                },
                {
                    'name': 'Sleep Sanctuary',
                    'description': 'Get 7+ hours sleep for 7 nights',
                    'duration_days': 7,
                    'target_value': 49,
                    'unit': 'hours',
                    'points_reward': 350,
                    'challenge_type': 'sleep'
                }
            ],
            'extended': [
                {
                    'name': 'Consistency King',
                    'description': 'Complete all workouts for 14 days',
                    'duration_days': 14,
                    'target_value': 14,
                    'unit': 'workouts',
                    'points_reward': 750,
                    'challenge_type': 'workout'
                },
                {
                    'name': 'Habit Former',
                    'description': 'Track all habits for 21 days',
                    'duration_days': 21,
                    'target_value': 21,
                    'unit': 'days',
                    'points_reward': 1000,
                    'challenge_type': 'habits'
                }
            ]
        }
    
    def schedule_upcoming_challenges(self) -> None:
        """Schedule challenges throughout the month"""
        try:
            library = self.get_challenge_library()
            start_date = datetime.now(self.sa_tz).date()
            end_date = start_date + timedelta(days=30)
            
            # Get currently scheduled challenges
            scheduled = self.db.table('upcoming_challenges').select('*').gte(
                'start_date', start_date.isoformat()
            ).execute()
            
            scheduled_count = {
                'daily': 0,
                'short': 0,
                'weekly': 0,
                'extended': 0
            }
            
            if scheduled.data:
                for challenge in scheduled.data:
                    category = challenge['challenge_category']
                    scheduled_count[category] = scheduled_count.get(category, 0) + 1
            
            # Schedule new challenges based on gaps
            for category, challenges in library.items():
                if scheduled_count[category] < 5:  # Max 5 per category
                    needed = 5 - scheduled_count[category]
                    for i in range(needed):
                        challenge = challenges[i % len(challenges)]
                        start_date = self._get_next_start_date(category)
                        
                        self.db.table('upcoming_challenges').insert({
                            'challenge_template_id': challenge['id'],
                            'challenge_category': category,
                            'start_date': start_date.isoformat(),
                            'end_date': (start_date + timedelta(
                                days=challenge['duration_days']
                            )).isoformat(),
                            'visible_from': (start_date - timedelta(days=7)).isoformat(),
                            'challenge_data': challenge
                        }).execute()
                        
            log_info("Challenges scheduled successfully")
            
        except Exception as e:
            log_error(f"Error scheduling challenges: {str(e)}")
    
    def pre_book_challenge(self, client_id: str, challenge_id: str) -> Dict:
        """Pre-book an upcoming challenge"""
        try:
            # Verify challenge exists and is upcoming
            challenge = self.db.table('upcoming_challenges').select('*').eq(
                'id', challenge_id
            ).single().execute()
            
            if not challenge.data:
                return {
                    'success': False,
                    'error': 'Challenge not found'
                }
            
            # Check if already pre-booked
            existing = self.db.table('challenge_pre_bookings').select('*').eq(
                'challenge_id', challenge_id
            ).eq('client_id', client_id).execute()
            
            if existing.data:
                return {
                    'success': False,
                    'error': 'Already pre-booked'
                }
            
            # Create pre-booking
            result = self.db.table('challenge_pre_bookings').insert({
                'challenge_id': challenge_id,
                'client_id': client_id,
                'booked_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            if result.data:
                return {
                    'success': True,
                    'message': f"""🎯 Challenge Pre-booked!

You'll be automatically enrolled when it starts.
Starting: {challenge.data['start_date']}

Get ready to crush it! 💪"""
                }
            
            return {
                'success': False,
                'error': 'Failed to pre-book'
            }
            
        except Exception as e:
            log_error(f"Error pre-booking challenge: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_next_start_date(self, category: str) -> datetime:
        """Get next available start date for challenge category"""
        today = datetime.now(self.sa_tz).date()
        
        if category == 'daily':
            # Next Wednesday for Water Wednesday etc
            days_ahead = (2 - today.weekday()) % 7
            return today + timedelta(days=days_ahead)
        elif category == 'short':
            # Start on Monday or Thursday
            days_to_mon = (0 - today.weekday()) % 7
            days_to_thu = (3 - today.weekday()) % 7
            return today + timedelta(days=min(days_to_mon, days_to_thu))
        elif category == 'weekly':
            # Start on Mondays
            days_ahead = (0 - today.weekday()) % 7
            return today + timedelta(days=days_ahead)
        else:  # extended
            # Start on 1st or 15th of month
            if today.day < 15:
                return today.replace(day=15)
            else:
                next_month = today.replace(day=28) + timedelta(days=4)
                return next_month.replace(day=1)

class NotificationManager:
    """Handles notification preferences and batching"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def set_user_preferences(self, client_id: str, pref_type: str, 
                           pref_time: str = '07:00', enabled: bool = True) -> Dict:
        """Set notification preferences"""
        try:
            valid_types = ['daily_digest', 'milestone_only', 'weekly', 'quiet']
            
            if pref_type not in valid_types:
                return {
                    'success': False,
                    'error': f'Invalid preference type. Must be one of: {", ".join(valid_types)}'
                }
            
            result = self.db.table('notification_preferences').upsert({
                'client_id': client_id,
                'type': pref_type,
                'time': pref_time,
                'enabled': enabled,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            if result.data:
                return {'success': True}
            
            return {'success': False, 'error': 'Failed to update preferences'}
            
        except Exception as e:
            log_error(f"Error setting notification preferences: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_daily_digest(self, client_id: str) -> Optional[str]:
        """Get daily digest message"""
        try:
            updates = []
            
            # Get active challenges
            challenges = self.db.table('challenge_participants').select(
                '*, challenges(*)'
            ).eq('client_id', client_id).eq('status', 'active').execute()
            
            if challenges.data:
                updates.append("🎯 *Active Challenges*")
                for c in challenges.data:
                    updates.append(f"• {c['challenges']['name']}")
            
            # Get points earned yesterday
            yesterday = datetime.now(self.sa_tz).date() - timedelta(days=1)
            points = self.db.table('point_logs').select('points').eq(
                'client_id', client_id
            ).eq('created_at', yesterday.isoformat()).execute()
            
            if points.data:
                total = sum(p['points'] for p in points.data)
                updates.append(f"\n💫 Points earned yesterday: {total}")
            
            if updates:
                return "\n".join(updates)
            return None
            
        except Exception as e:
            log_error(f"Error getting daily digest: {str(e)}")
            return None
    
    def should_notify(self, client_id: str, notification_type: str) -> bool:
        """Check if notification should be sent based on preferences"""
        try:
            # Get preferences
            prefs = self.db.table('notification_preferences').select('*').eq(
                'client_id', client_id
            ).single().execute()
            
            if not prefs.data or not prefs.data['enabled']:
                return False
            
            pref_type = prefs.data['type']
            current_hour = datetime.now(self.sa_tz).hour
            
            # Don't send after 8pm
            if current_hour >= 20:
                return False
            
            if pref_type == 'quiet':
                return False
            elif pref_type == 'milestone_only':
                return notification_type == 'milestone'
            elif pref_type == 'weekly':
                return notification_type in ['weekly_summary', 'milestone']
            else:  # daily_digest
                return True
                
        except Exception as e:
            log_error(f"Error checking notification preferences: {str(e)}")
            return False

    def create_daily_digest(self, client_id: str) -> Optional[str]:
        """Create consolidated daily digest message"""
        try:
            # Get preferences
            prefs = self.db.table('notification_preferences').select('*').eq(
                'client_id', client_id
            ).single().execute()
            
            if not prefs.data or not prefs.data['enabled']:
                return None
                
            # Get client info
            client = self.db.table('clients').select('name').eq(
                'id', client_id
            ).single().execute()
            
            digest = [f"👋 Good morning {client.data['name']}!"]
            
            # Add challenge updates
            challenge_text = self.get_daily_digest(client_id)
            if challenge_text:
                digest.append(challenge_text)
            
            # Add streak info
            streak = self._get_current_streak(client_id)
            if streak > 0:
                digest.append(f"\n🔥 Current streak: {streak} days")
            
            # Add dashboard link
            digest.append("\n📱 View details: [dashboard_link]")
            
            return "\n".join(digest) if len(digest) > 1 else None
            
        except Exception as e:
            log_error(f"Error creating daily digest: {str(e)}")
            return None
    
    def _get_current_streak(self, client_id: str) -> int:
        """Get current streak days"""
        try:
            today = datetime.now(self.sa_tz).date()
            streak = 0
            
            for i in range(30):  # Check last 30 days max
                check_date = today - timedelta(days=i)
                
                result = self.db.table('daily_logs').select('*').eq(
                    'client_id', client_id
                ).eq('log_date', check_date.isoformat()).execute()
                
                if result.data:
                    streak += 1
                else:
                    break
            
            return streak
            
        except Exception as e:
            log_error(f"Error getting streak: {str(e)}")
            return 0