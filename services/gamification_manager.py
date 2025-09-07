"""Gamification manager for points, badges, and achievements"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class GamificationManager:
    """Manages points, badges, and achievements"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Point values
        self.POINTS = {
            'workout_sent': 25,
            'workout_completed': 50,
            'assessment_completed': 100,
            'assessment_improved': 50,
            'habit_logged': 10,
            'habit_streak_3': 30,
            'habit_streak_7': 70,
            'habit_streak_14': 150,
            'habit_streak_30': 300,
            'challenge_completed': 100,
            'challenge_won': 200
        }
        
        # Badge definitions
        self.BADGES = {
            'improver': {
                'name': 'Improver',
                'description': 'Achieved 10% improvement in assessments',
                'icon': '📈',
                'criteria': 'assessment_improvement',
                'threshold': 10
            },
            'consistency_king': {
                'name': 'Consistency King',
                'description': 'Logged habits for 30 days straight',
                'icon': '👑',
                'criteria': 'habit_streak',
                'threshold': 30
            },
            'workout_warrior': {
                'name': 'Workout Warrior',
                'description': 'Completed 20 workouts',
                'icon': '💪',
                'criteria': 'workouts_completed',
                'threshold': 20
            },
            'habit_hero': {
                'name': 'Habit Hero',
                'description': 'Logged 100 habits',
                'icon': '🦸',
                'criteria': 'habits_logged',
                'threshold': 100
            }
        }
    
    def award_points(self, user_id: str, user_type: str, action: str, 
                     value: int = None, metadata: Dict = None) -> Dict:
        """Award points for an action"""
        try:
            # Get point value
            points = value if value else self.POINTS.get(action, 0)
            
            if points == 0:
                return {'success': False, 'error': 'Invalid action'}
            
            # Get or create gamification profile
            profile = self._get_or_create_profile(user_id, user_type)
            
            if not profile:
                return {'success': False, 'error': 'Failed to get profile'}
            
            # Update points
            new_total = profile.get('points_total', 0) + points
            
            # Update profile
            profile_key = f'{user_type}_id'
            self.db.table('gamification_profiles').update({
                'points_total': new_total,
                'points_this_week': profile.get('points_this_week', 0) + points,
                'points_this_month': profile.get('points_this_month', 0) + points,
                'last_points_earned': datetime.now(self.sa_tz).isoformat()
            }).eq(profile_key, user_id).execute()
            
            # Log points
            self.db.table('point_logs').insert({
                'user_id': user_id,
                'user_type': user_type,
                'action': action,
                'points': points,
                'metadata': metadata or {},
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Update leaderboards
            self._update_leaderboards(user_id, user_type, new_total)
            
            # Check for challenge updates
            if action.startswith('workout_') or action.startswith('habit_'):
                self._update_challenge_progress(user_id, user_type, action, metadata)
            
            log_info(f"Awarded {points} points to {user_type} {user_id} for {action}")
            
            return {
                'success': True,
                'points_awarded': points,
                'new_total': new_total,
                'message': f"+{points} points! Total: {new_total}"
            }
            
        except Exception as e:
            log_error(f"Error awarding points: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_and_award_badges(self, user_id: str, user_type: str, 
                              trigger_type: str, value: any = None) -> List[Dict]:
        """Check if user has earned any badges"""
        earned_badges = []
        
        try:
            for badge_id, badge_def in self.BADGES.items():
                if badge_def['criteria'] == trigger_type:
                    # Check if already earned
                    existing = self.db.table('user_badges').select('id').eq(
                        'user_id', user_id
                    ).eq('user_type', user_type).eq(
                        'badge_id', badge_id
                    ).execute()
                    
                    if not existing.data:
                        # Check if criteria met
                        if self._check_badge_criteria(user_id, user_type, badge_def, value):
                            # Award badge
                            self.db.table('user_badges').insert({
                                'user_id': user_id,
                                'user_type': user_type,
                                'badge_id': badge_id,
                                'earned_at': datetime.now(self.sa_tz).isoformat()
                            }).execute()
                            
                            earned_badges.append({
                                'name': badge_def['name'],
                                'description': badge_def['description'],
                                'icon': badge_def['icon']
                            })
                            
                            log_info(f"Badge earned: {badge_def['name']} by {user_type} {user_id}")
            
            return earned_badges
            
        except Exception as e:
            log_error(f"Error checking badges: {str(e)}")
            return []
    
    def compare_assessments(self, client_id: str, old_assessment: Dict, 
                          new_assessment: Dict) -> Tuple[Dict, List[str]]:
        """Compare assessments and calculate improvements"""
        improvements = []
        points_earned = 0
        
        try:
            # Compare measurements
            old_measurements = old_assessment.get('responses', {}).get('measurements', {})
            new_measurements = new_assessment.get('responses', {}).get('measurements', {})
            
            # Check weight improvement
            if 'weight' in old_measurements and 'weight' in new_measurements:
                old_weight = float(old_measurements['weight'])
                new_weight = float(new_measurements['weight'])
                weight_change = ((old_weight - new_weight) / old_weight) * 100
                
                if weight_change >= 5:
                    improvements.append(f"Weight loss: {weight_change:.1f}%")
                    points_earned += 25
            
            # Check fitness test improvements
            old_tests = old_assessment.get('responses', {}).get('fitness_tests', {})
            new_tests = new_assessment.get('responses', {}).get('fitness_tests', {})
            
            # Check pushups
            if 'pushups' in old_tests and 'pushups' in new_tests:
                old_pushups = int(old_tests['pushups'])
                new_pushups = int(new_tests['pushups'])
                pushup_improvement = ((new_pushups - old_pushups) / old_pushups) * 100 if old_pushups > 0 else 0
                
                if pushup_improvement >= 10:
                    improvements.append(f"Push-ups: +{pushup_improvement:.0f}%")
                    points_earned += 25
            
            # Check plank
            if 'plank' in old_tests and 'plank' in new_tests:
                old_plank = int(old_tests['plank'])
                new_plank = int(new_tests['plank'])
                plank_improvement = ((new_plank - old_plank) / old_plank) * 100 if old_plank > 0 else 0
                
                if plank_improvement >= 10:
                    improvements.append(f"Plank hold: +{plank_improvement:.0f}%")
                    points_earned += 25
            
            # Overall improvement check for badge
            overall_improvement = len(improvements) >= 2  # At least 2 areas improved
            
            result = {
                'improvements': improvements,
                'points_earned': points_earned,
                'overall_improvement': overall_improvement
            }
            
            # Award points if improvements found
            if points_earned > 0:
                self.award_points(client_id, 'client', 'assessment_improved', 
                                points_earned, {'improvements': improvements})
            
            # Check for Improver badge
            if overall_improvement:
                badges = self.check_and_award_badges(client_id, 'client', 
                                                    'assessment_improvement', 10)
                return result, badges
            
            return result, []
            
        except Exception as e:
            log_error(f"Error comparing assessments: {str(e)}")
            return {'improvements': [], 'points_earned': 0}, []
    
    def _get_or_create_profile(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get or create gamification profile"""
        try:
            profile_key = f'{user_type}_id'
            
            # Try to get existing profile
            result = self.db.table('gamification_profiles').select('*').eq(
                profile_key, user_id
            ).single().execute()
            
            if result.data:
                return result.data
            
            # Create new profile
            new_profile = {
                profile_key: user_id,
                'points_total': 0,
                'points_this_week': 0,
                'points_this_month': 0,
                'is_public': True,
                'opted_in_global': True,
                'opted_in_trainer': True,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('gamification_profiles').insert(
                new_profile
            ).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            log_error(f"Error getting/creating profile: {str(e)}")
            return None
    
    def _check_badge_criteria(self, user_id: str, user_type: str, 
                            badge_def: Dict, value: any) -> bool:
        """Check if badge criteria is met"""
        try:
            criteria = badge_def['criteria']
            threshold = badge_def['threshold']
            
            if criteria == 'assessment_improvement':
                return value >= threshold if value else False
                
            elif criteria == 'habit_streak':
                # Check current streak
                from services.habits import HabitTrackingService
                habit_service = HabitTrackingService(self.db)
                streak = habit_service.get_current_streak(user_id)
                return streak >= threshold
                
            elif criteria == 'workouts_completed':
                # Count completed workouts
                count = self.db.table('bookings').select(
                    'id', count='exact'
                ).eq('client_id', user_id).eq(
                    'status', 'completed'
                ).execute()
                return count.count >= threshold if count else False
                
            elif criteria == 'habits_logged':
                # Count habit logs
                count = self.db.table('habit_tracking').select(
                    'id', count='exact'
                ).eq('client_id', user_id).execute()
                return count.count >= threshold if count else False
            
            return False
            
        except Exception as e:
            log_error(f"Error checking badge criteria: {str(e)}")
            return False
    
    def _update_leaderboards(self, user_id: str, user_type: str, points: int):
        """Update leaderboard entries"""
        try:
            # Update global leaderboard
            global_lb = self.db.table('leaderboards').select('id').eq(
                'type', 'global'
            ).eq('is_active', True).single().execute()
            
            if global_lb.data:
                # Check if entry exists
                entry = self.db.table('leaderboard_entries').select('*').eq(
                    'leaderboard_id', global_lb.data['id']
                ).eq('user_id', user_id).eq(
                    'user_type', user_type
                ).single().execute()
                
                if entry.data:
                    # Update existing
                    self.db.table('leaderboard_entries').update({
                        'points': points,
                        'updated_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('id', entry.data['id']).execute()
                else:
                    # Create new entry
                    self.db.table('leaderboard_entries').insert({
                        'leaderboard_id': global_lb.data['id'],
                        'user_id': user_id,
                        'user_type': user_type,
                        'points': points,
                        'rank': 999  # Will be recalculated
                    }).execute()
            
        except Exception as e:
            log_error(f"Error updating leaderboards: {str(e)}")
    
    def _update_challenge_progress(self, user_id: str, user_type: str, 
                                  action: str, metadata: Dict = None):
        """Update challenge progress based on action"""
        try:
            # Get active challenge participations
            participants = self.db.table('challenge_participants').select(
                '*, challenges(*)'
            ).eq('user_id', user_id).eq(
                'user_type', user_type
            ).eq('status', 'active').execute()
            
            if not participants.data:
                return
            
            for participant in participants.data:
                challenge = participant.get('challenges', {})
                challenge_type = challenge.get('challenge_rules', {}).get('challenge_type')
                
                # Check if action matches challenge type
                update_value = 0
                
                if challenge_type == 'workout' and action == 'workout_completed':
                    update_value = 1
                elif challenge_type == 'habits' and action == 'habit_logged':
                    update_value = 1
                elif challenge_type == 'water_intake' and metadata:
                    if metadata.get('habit_type') == 'water_intake':
                        update_value = float(metadata.get('value', 0))
                elif challenge_type == 'steps' and metadata:
                    if metadata.get('habit_type') == 'steps':
                        update_value = int(metadata.get('value', 0))
                
                if update_value > 0:
                    # Update progress
                    self.db.table('challenge_progress').insert({
                        'participant_id': participant['id'],
                        'date': datetime.now(self.sa_tz).date().isoformat(),
                        'value_achieved': update_value,
                        'created_at': datetime.now(self.sa_tz).isoformat()
                    }).execute()
                    
                    log_info(f"Updated challenge progress for {user_id}: +{update_value}")
                    
        except Exception as e:
            log_error(f"Error updating challenge progress: {str(e)}")