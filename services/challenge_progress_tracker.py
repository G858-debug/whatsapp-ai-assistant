"""Centralized challenge progress tracking service"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class ChallengeProgressTracker:
    """Auto-tracks progress for challenges based on activities"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Activity to challenge type mapping
        self.ACTIVITY_MAPPING = {
            'habit': {
                'water_intake': ['hydration', 'water_challenge', 'daily_water'],
                'steps': ['step_challenge', 'walking', 'daily_steps', 'movement'],
                'sleep_hours': ['sleep_challenge', 'rest', 'recovery'],
                'workout_completed': ['consistency', 'workout_warrior', 'daily_workout'],
                'vegetables': ['nutrition', 'veggie_challenge', 'healthy_eating'],
                'all_habits': ['consistency_challenge', 'habit_master', 'daily_tracking']
            },
            'workout': {
                'completed': ['workout_warrior', 'consistency', 'fitness_challenge', 'training'],
                'strength': ['strength_challenge', 'muscle_building'],
                'cardio': ['cardio_challenge', 'endurance']
            },
            'assessment': {
                'improvement': ['improvement_challenge', 'progress_challenge', 'transformation'],
                'weight_loss': ['weight_loss_challenge', 'body_composition'],
                'strength_gain': ['strength_improvement', 'muscle_gain']
            }
        }
        
        # Points for different activities
        self.ACTIVITY_POINTS = {
            'habit_logged': 10,
            'workout_completed': 25,
            'assessment_improved': 50,
            'challenge_milestone': 100
        }
    
    def auto_track_progress(self, user_id: str, user_type: str, 
                           activity_type: str, activity_data: Dict) -> int:
        """
        Automatically track progress for relevant challenges
        
        Returns: Points earned from challenge progress
        """
        try:
            # Get user's active challenges
            active_challenges = self._get_active_challenges(user_id, user_type)
            if not active_challenges:
                return 0
            
            total_points = 0
            updates_batch = []
            
            for challenge in active_challenges:
                # Check if activity matches challenge
                progress_value = self._calculate_progress_value(
                    challenge, activity_type, activity_data
                )
                
                if progress_value > 0:
                    # Prepare batch update
                    updates_batch.append({
                        'participant_id': challenge['participant_id'],
                        'challenge_id': challenge['challenge_id'],
                        'value': progress_value,
                        'activity_type': activity_type,
                        'activity_data': activity_data
                    })
                    
                    # Calculate points (but don't send notification)
                    points = self._calculate_points(challenge, progress_value)
                    total_points += points
            
            # Batch update progress
            if updates_batch:
                self._batch_update_progress(updates_batch)
                
                # Update dashboard in real-time
                self._trigger_dashboard_update(user_id, user_type, updates_batch)
                
                # Queue for daily digest
                self._queue_for_digest(user_id, user_type, total_points, updates_batch)
            
            return total_points
            
        except Exception as e:
            log_error(f"Error in auto_track_progress: {str(e)}")
            return 0
    
    def _get_active_challenges(self, user_id: str, user_type: str) -> List[Dict]:
        """Get user's active challenge participations"""
        try:
            result = self.db.table('challenge_participants').select(
                """
                id as participant_id,
                challenge_id,
                challenges (
                    id,
                    name,
                    challenge_rules,
                    target_value,
                    points_reward,
                    end_date
                )
                """
            ).eq('user_id', user_id).eq(
                'user_type', user_type
            ).eq('status', 'active').execute()
            
            if not result.data:
                return []
            
            # Flatten the structure
            challenges = []
            for participant in result.data:
                if participant.get('challenges'):
                    challenge_data = participant['challenges']
                    challenges.append({
                        'participant_id': participant['participant_id'],
                        'challenge_id': participant['challenge_id'],
                        'name': challenge_data['name'],
                        'rules': challenge_data.get('challenge_rules', {}),
                        'target_value': challenge_data.get('target_value', 0),
                        'points_reward': challenge_data.get('points_reward', 0),
                        'end_date': challenge_data.get('end_date')
                    })
            
            return challenges
            
        except Exception as e:
            log_error(f"Error getting active challenges: {str(e)}")
            return []
    
    def _calculate_progress_value(self, challenge: Dict, 
                                 activity_type: str, activity_data: Dict) -> float:
        """Calculate progress value based on activity and challenge type"""
        try:
            challenge_type = challenge['rules'].get('challenge_type', '')
            
            # Handle habit activities
            if activity_type == 'habit':
                habit_type = activity_data.get('habit_type')
                habit_value = activity_data.get('value', 0)
                
                # Check if habit matches challenge
                if habit_type in self.ACTIVITY_MAPPING['habit']:
                    matching_challenges = self.ACTIVITY_MAPPING['habit'][habit_type]
                    if any(ct in challenge_type.lower() for ct in matching_challenges):
                        # Return the actual value for cumulative challenges
                        if habit_type in ['water_intake', 'steps', 'sleep_hours']:
                            return float(habit_value) if habit_value else 0
                        # Return 1 for completion-based challenges
                        else:
                            return 1.0
                
                # Check for "all habits" challenges
                if 'consistency' in challenge_type.lower() or 'all' in challenge_type.lower():
                    return 1.0  # Each habit counts as 1
            
            # Handle workout activities
            elif activity_type == 'workout':
                workout_type = activity_data.get('workout_type', 'general')
                
                if 'workout' in challenge_type.lower() or 'consistency' in challenge_type.lower():
                    return 1.0
                
                # Specific workout type matching
                if workout_type in self.ACTIVITY_MAPPING['workout']:
                    matching_challenges = self.ACTIVITY_MAPPING['workout'][workout_type]
                    if any(ct in challenge_type.lower() for ct in matching_challenges):
                        return 1.0
            
            # Handle assessment improvements
            elif activity_type == 'assessment':
                improvement_type = activity_data.get('improvement_type', 'general')
                improvement_percentage = activity_data.get('improvement_percentage', 0)
                
                if 'improvement' in challenge_type.lower():
                    # Use percentage as progress value for improvement challenges
                    return improvement_percentage / 100.0  # Normalize to 0-1
            
            return 0
            
        except Exception as e:
            log_error(f"Error calculating progress value: {str(e)}")
            return 0
    
    def _calculate_points(self, challenge: Dict, progress_value: float) -> int:
        """Calculate points earned from progress"""
        try:
            # Base points for any progress
            base_points = 10
            
            # Additional points based on progress toward target
            if challenge.get('target_value'):
                # Get current total progress
                current_progress = self._get_current_progress(
                    challenge['participant_id']
                )
                new_total = current_progress + progress_value
                
                # Check for milestone achievements
                milestones = [0.25, 0.5, 0.75, 1.0]  # 25%, 50%, 75%, 100%
                target = challenge['target_value']
                
                for milestone in milestones:
                    milestone_value = target * milestone
                    if current_progress < milestone_value <= new_total:
                        # Milestone reached!
                        base_points += self.ACTIVITY_POINTS['challenge_milestone']
                        
                        # Check for completion
                        if milestone == 1.0:
                            base_points += challenge.get('points_reward', 0)
            
            return base_points
            
        except Exception as e:
            log_error(f"Error calculating points: {str(e)}")
            return 10  # Default points
    
    def _get_current_progress(self, participant_id: str) -> float:
        """Get current cumulative progress for a participant"""
        try:
            result = self.db.table('challenge_progress').select(
                'value_achieved'
            ).eq('participant_id', participant_id).execute()
            
            if result.data:
                return sum(p['value_achieved'] for p in result.data)
            return 0
            
        except Exception as e:
            log_error(f"Error getting current progress: {str(e)}")
            return 0
    
    def _batch_update_progress(self, updates: List[Dict]):
        """Batch update challenge progress"""
        try:
            # Process each update
            for update in updates:
                # Check if already logged today (prevent duplicates)
                today = datetime.now(self.sa_tz).date().isoformat()
                
                existing = self.db.table('challenge_progress').select('id').eq(
                    'participant_id', update['participant_id']
                ).eq('date', today).eq(
                    'activity_type', update.get('activity_type', 'unknown')
                ).execute()
                
                if not existing.data:
                    # Insert new progress entry
                    self.db.table('challenge_progress').insert({
                        'participant_id': update['participant_id'],
                        'date': today,
                        'value_achieved': update['value'],
                        'activity_type': update.get('activity_type'),
                        'metadata': update.get('activity_data', {}),
                        'created_at': datetime.now(self.sa_tz).isoformat()
                    }).execute()
                else:
                    # Update existing entry (add to value)
                    self.db.table('challenge_progress').update({
                        'value_achieved': self.db.rpc('increment', {
                            'x': existing.data[0]['id'],
                            'row_id': update['value']
                        })
                    }).eq('id', existing.data[0]['id']).execute()
            
            log_info(f"Batch updated {len(updates)} challenge progress entries")
            
        except Exception as e:
            log_error(f"Error in batch update: {str(e)}")
    
    def _trigger_dashboard_update(self, user_id: str, user_type: str, updates: List[Dict]):
        """Trigger real-time dashboard update"""
        try:
            # Update last_activity timestamp for real-time sync
            self.db.table('dashboard_updates').insert({
                'user_id': user_id,
                'user_type': user_type,
                'update_type': 'challenge_progress',
                'update_data': {
                    'updates_count': len(updates),
                    'challenges_affected': [u['challenge_id'] for u in updates]
                },
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            # Update gamification profile with new activity
            profile_key = f'{user_type}_id'
            self.db.table('gamification_profiles').update({
                'last_activity': datetime.now(self.sa_tz).isoformat()
            }).eq(profile_key, user_id).execute()
            
        except Exception as e:
            log_error(f"Error triggering dashboard update: {str(e)}")
    
    def _queue_for_digest(self, user_id: str, user_type: str, 
                         points: int, updates: List[Dict]):
        """Queue achievements for daily digest"""
        try:
            # Create digest entry
            digest_content = {
                'points_earned': points,
                'challenges_progressed': len(updates),
                'timestamp': datetime.now(self.sa_tz).isoformat()
            }
            
            # Add to notification queue for next digest
            self.db.table('notification_queue').insert({
                'user_id': user_id,
                'user_type': user_type,
                'notification_type': 'challenge_progress',
                'content': f"Challenge progress: +{points} points",
                'data': digest_content,
                'scheduled_for': self._get_next_digest_time(user_id, user_type),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error queuing for digest: {str(e)}")
    
    def _get_next_digest_time(self, user_id: str, user_type: str) -> str:
        """Get next digest time for user"""
        try:
            # Get user preferences
            profile_key = f'{user_type}_id'
            prefs = self.db.table('gamification_profiles').select(
                'digest_time'
            ).eq(profile_key, user_id).single().execute()
            
            digest_time = '07:00'  # Default
            if prefs.data and prefs.data.get('digest_time'):
                digest_time = prefs.data['digest_time']
            
            # Calculate next digest datetime
            now = datetime.now(self.sa_tz)
            hour, minute = map(int, digest_time.split(':'))
            next_digest = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if next_digest <= now:
                next_digest += timedelta(days=1)
            
            return next_digest.isoformat()
            
        except Exception as e:
            log_error(f"Error getting digest time: {str(e)}")
            # Return tomorrow 7am as fallback
            tomorrow = datetime.now(self.sa_tz) + timedelta(days=1)
            return tomorrow.replace(hour=7, minute=0, second=0, microsecond=0).isoformat()
    
    def check_challenge_completion(self, participant_id: str) -> Optional[Dict]:
        """Check if challenge is completed and trigger celebration"""
        try:
            # Get participant and challenge info
            participant = self.db.table('challenge_participants').select(
                """
                *,
                challenges (
                    target_value,
                    points_reward,
                    name
                )
                """
            ).eq('id', participant_id).single().execute()
            
            if not participant.data:
                return None
            
            # Get total progress
            progress = self.db.table('challenge_progress').select(
                'value_achieved'
            ).eq('participant_id', participant_id).execute()
            
            total_progress = sum(p['value_achieved'] for p in (progress.data or []))
            target = participant.data['challenges']['target_value']
            
            if total_progress >= target and participant.data['status'] == 'active':
                # Mark as completed
                self.db.table('challenge_participants').update({
                    'status': 'completed',
                    'completed_at': datetime.now(self.sa_tz).isoformat(),
                    'final_value': total_progress
                }).eq('id', participant_id).execute()
                
                # Return completion data for celebration
                return {
                    'challenge_name': participant.data['challenges']['name'],
                    'points_earned': participant.data['challenges']['points_reward'],
                    'final_value': total_progress,
                    'target_value': target
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error checking challenge completion: {str(e)}")
            return None