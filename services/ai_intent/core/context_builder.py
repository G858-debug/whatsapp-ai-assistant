"""
Context Builder
Builds context information for AI intent detection
"""
from typing import Dict, List
import pytz
from utils.logger import log_error


class ContextBuilder:
    """Builds context for AI intent detection"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def build_context(self, phone: str, role: str, user_id: str,
                     recent_tasks: List[Dict], chat_history: List[Dict]) -> Dict:
        """Build comprehensive context for AI"""
        try:
            # Get user data
            user_data = self._get_user_data(role, user_id)
            
            # Build base context
            context = {
                'role': role,
                'user_id': user_id,
                'phone': phone,
                'recent_tasks': [t.get('task_type') for t in recent_tasks[:3]],
                'chat_history': [h.get('message', '')[:100] for h in chat_history[-5:]],
            }
            
            # Add user information
            if user_data:
                context['name'] = user_data.get('first_name') or user_data.get('name', '').split()[0] or 'there'
                
                # Add role-specific context
                if role == 'trainer':
                    context.update(self._build_trainer_context(user_data))
                else:
                    context.update(self._build_client_context(user_data))
            
            return context
            
        except Exception as e:
            log_error(f"Error building context: {str(e)}")
            return {'role': role, 'user_id': user_id, 'phone': phone}
    
    def _get_user_data(self, role: str, user_id: str) -> Dict:
        """Get user data from database"""
        try:
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            if result.data:
                return result.data[0]
            return {}
            
        except Exception as e:
            log_error(f"Error getting user data: {str(e)}")
            return {}
    
    def _build_trainer_context(self, user_data: Dict) -> Dict:
        """Build trainer-specific context"""
        return {
            'business_name': user_data.get('business_name'),
            'specialization': user_data.get('specialization'),
            'experience_years': user_data.get('experience_years'),
            'certifications': user_data.get('certifications')
        }
    
    def _build_client_context(self, user_data: Dict) -> Dict:
        """Build client-specific context"""
        return {
            'fitness_goals': user_data.get('fitness_goals'),
            'experience_level': user_data.get('experience_level'),
            'health_conditions': user_data.get('health_conditions'),
            'preferred_workout_time': user_data.get('preferred_workout_time')
        }