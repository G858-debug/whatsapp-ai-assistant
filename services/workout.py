"""Workout management service"""
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class WorkoutService:
    """Handle workout creation and management"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_workout(self, trainer_id: str, workout_data: Dict) -> Dict:
        """Create a new workout"""
        try:
            workout = {
                'trainer_id': trainer_id,
                'name': workout_data.get('name', 'Workout'),
                'description': workout_data.get('description'),
                'exercises': workout_data.get('exercises', []),
                'duration_minutes': workout_data.get('duration', 60),
                'difficulty': workout_data.get('difficulty', 'intermediate'),
                'category': workout_data.get('category', 'general'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workouts').insert(workout).execute()
            
            if result.data:
                log_info(f"Workout created: {workout['name']}")
                return {'success': True, 'workout_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to create workout'}
            
        except Exception as e:
            log_error(f"Error creating workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def assign_workout(self, trainer_id: str, client_id: str, 
                      workout_id: str, scheduled_date: str = None) -> Dict:
        """Assign workout to client"""
        try:
            # Verify workout belongs to trainer
            workout = self.db.table('workouts').select('id').eq(
                'id', workout_id
            ).eq('trainer_id', trainer_id).single().execute()
            
            if not workout.data:
                return {'success': False, 'error': 'Workout not found'}
            
            assignment = {
                'workout_id': workout_id,
                'client_id': client_id,
                'trainer_id': trainer_id,
                'scheduled_date': scheduled_date or datetime.now(self.sa_tz).date().isoformat(),
                'status': 'assigned',
                'assigned_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workout_assignments').insert(
                assignment
            ).execute()
            
            if result.data:
                log_info(f"Workout assigned to client {client_id}")
                return {'success': True, 'assignment_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to assign workout'}
            
        except Exception as e:
            log_error(f"Error assigning workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_workouts(self, client_id: str, status: str = None) -> List[Dict]:
        """Get workouts assigned to client"""
        try:
            query = self.db.table('workout_assignments').select(
                '*, workouts(*)'
            ).eq('client_id', client_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('scheduled_date', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting client workouts: {str(e)}")
            return []
    
    def mark_workout_completed(self, assignment_id: str, 
                              feedback: Dict = None) -> Dict:
        """Mark workout as completed"""
        try:
            update_data = {
                'status': 'completed',
                'completed_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if feedback:
                update_data['feedback'] = feedback
            
            result = self.db.table('workout_assignments').update(
                update_data
            ).eq('id', assignment_id).execute()
            
            if result.data:
                log_info(f"Workout {assignment_id} marked as completed")
                return {'success': True}
            
            return {'success': False, 'error': 'Assignment not found'}
            
        except Exception as e:
            log_error(f"Error marking workout completed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_workout_library(self, trainer_id: str, 
                          category: str = None) -> List[Dict]:
        """Get trainer's workout library"""
        try:
            query = self.db.table('workouts').select('*').eq(
                'trainer_id', trainer_id
            )
            
            if category:
                query = query.eq('category', category)
            
            result = query.order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting workout library: {str(e)}")
            return []
    
    def format_workout_for_whatsapp(self, workout: Dict) -> str:
        """Format workout for WhatsApp message"""
        try:
            message = f"🏋️ *{workout['name']}*\n\n"
            
            if workout.get('description'):
                message += f"_{workout['description']}_\n\n"
            
            message += f"⏱ Duration: {workout.get('duration_minutes', 60)} minutes\n"
            message += f"💪 Difficulty: {workout.get('difficulty', 'intermediate').title()}\n\n"
            
            if workout.get('exercises'):
                message += "*Exercises:*\n"
                for i, exercise in enumerate(workout['exercises'], 1):
                    message += f"{i}. {exercise.get('name', 'Exercise')}"
                    
                    if exercise.get('sets') and exercise.get('reps'):
                        message += f" - {exercise['sets']} sets x {exercise['reps']} reps"
                    elif exercise.get('duration'):
                        message += f" - {exercise['duration']}"
                    
                    message += "\n"
            
            return message
            
        except Exception as e:
            log_error(f"Error formatting workout: {str(e)}")
            return "Workout details unavailable"