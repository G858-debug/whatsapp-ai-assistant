"""Workout service for managing training programs"""
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class WorkoutService:
    """Service for managing workouts and training programs"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_workout(self, trainer_id: str, client_id: str, 
                      workout_data: Dict) -> Dict:
        """Create a new workout"""
        try:
            workout = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'name': workout_data.get('name', 'Custom Workout'),
                'description': workout_data.get('description', ''),
                'exercises': workout_data.get('exercises', []),
                'duration_minutes': workout_data.get('duration', 60),
                'difficulty': workout_data.get('difficulty', 'intermediate'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workouts').insert(workout).execute()
            
            if result.data:
                log_info(f"Workout created for client {client_id}")
                return {
                    'success': True,
                    'workout_id': result.data[0]['id']
                }
            
            return {'success': False, 'error': 'Failed to create workout'}
            
        except Exception as e:
            log_error(f"Error creating workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_workouts(self, client_id: str) -> List[Dict]:
        """Get all workouts for a client"""
        try:
            result = self.db.table('workouts').select('*').eq(
                'client_id', client_id
            ).order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting workouts: {str(e)}")
            return []