"""
Dashboard Service
Handles dashboard data retrieval and management
"""
from typing import List, Dict, Optional
from utils.logger import log_info, log_error
from services.relationships import RelationshipService


class DashboardService:
    """Provides dashboard functionality for relationship management"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.relationship_service = RelationshipService(supabase_client)
    
    def _format_array_field(self, field_value):
        """Helper to format array fields, handling empty arrays and strings properly"""
        if isinstance(field_value, list) and field_value:
            # Filter out empty strings and None values
            filtered_items = [str(item) for item in field_value if item and str(item).strip()]
            return ', '.join(filtered_items) if filtered_items else ''
        elif isinstance(field_value, str) and field_value:
            # Handle string representations of arrays and empty cases
            if field_value in ['[]', '[""]', 'null', 'None', '""', "''", 'undefined']:
                return ''
            return field_value
        else:
            return ''
    
    def get_user_info(self, user_id: str, role: str) -> Optional[Dict]:
        """Get user information for dashboard"""
        try:
            table = 'trainers' if role == 'trainer' else 'clients'
            id_field = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(id_field, user_id).execute()
            
            if result.data:
                user_data = result.data[0]
                # Clean up data for dashboard
                return {
                    'id': user_data.get(id_field),
                    'name': user_data.get('name', 'N/A'),
                    'phone': user_data.get('whatsapp', 'N/A'),
                    'email': user_data.get('email', 'N/A'),
                    'role': role
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error getting user info: {str(e)}")
            return None
    
    def get_relationships(self, user_id: str, role: str, status: str = 'active') -> List[Dict]:
        """Get relationships for dashboard display"""
        try:
            if role == 'trainer':
                relationships = self.relationship_service.get_trainer_clients(user_id, status)
                # Format for dashboard
                formatted = []
                for client in relationships:
                    rel = client.get('relationship', {})
                    
                    # Format JSON arrays to comma-separated text
                    training_times_text = self._format_array_field(client.get('preferred_training_times', []))
                    
                    formatted.append({
                        'id': client.get('client_id', 'N/A'),
                        'name': client.get('name', 'N/A'),
                        'status': client.get('status', 'N/A'),
                        'additional_info': {
                            'experience_level': client.get('experience_level', ''),
                            'health_conditions': self._format_array_field(client.get('health_conditions', '')),
                            'fitness_goals': self._format_array_field(client.get('fitness_goals', '')),
                            'availability': self._format_array_field(client.get('availability', '')),
                            'preferred_training_times': training_times_text
                        },
                        'connected_date': rel.get('created_at', '')[:10] if rel.get('created_at') else 'N/A',
                        'connection_status': rel.get('connection_status', status)
                    })
                return formatted
            
            else:  # client
                relationships = self.relationship_service.get_client_trainers(user_id, status)
                # Format for dashboard
                formatted = []
                for trainer in relationships:
                    rel = trainer.get('relationship', {})
                    
                    # Format JSON arrays to comma-separated text
                    services_text = self._format_array_field(trainer.get('services_offered', []))
                    pricing_flex_text = self._format_array_field(trainer.get('pricing_flexibility', []))
                    available_days_text = self._format_array_field(trainer.get('available_days', []))
                    
                    formatted.append({
                        'id': trainer.get('trainer_id', 'N/A'),
                        'name': trainer.get('name', 'N/A'),
                        'first_name': trainer.get('first_name', ''),
                        'last_name': trainer.get('last_name', ''),
                        'business_name': trainer.get('business_name', ''),
                        'status': trainer.get('status', 'N/A'),
                        'additional_info': {
                            'pricing_per_session': f"R{trainer.get('pricing_per_session', 0)}" if trainer.get('pricing_per_session') else '',
                            'city': trainer.get('city', ''),
                            'location': trainer.get('location', ''),
                            'experience_years': trainer.get('experience_years', ''),
                            'years_experience': trainer.get('years_experience', ''),
                            'available_days': available_days_text,
                            'preferred_time_slots': self._format_array_field(trainer.get('preferred_time_slots', '')),
                            'specialization': self._format_array_field(trainer.get('specialization', '')),
                            'services_offered': services_text,
                            'pricing_flexibility': pricing_flex_text,
                            'additional_notes': trainer.get('additional_notes', '')
                        },
                        'connected_date': rel.get('created_at', '')[:10] if rel.get('created_at') else 'N/A',
                        'connection_status': rel.get('connection_status', status)
                    })
                return formatted
            
        except Exception as e:
            log_error(f"Error getting relationships: {str(e)}")
            return []
    

    
    def get_dashboard_stats(self, user_id: str, role: str) -> Dict:
        """Get dashboard statistics"""
        try:
            active_relationships = self.get_relationships(user_id, role, 'active')
            pending_relationships = self.get_relationships(user_id, role, 'pending')
            
            return {
                'active_count': len(active_relationships),
                'pending_count': len(pending_relationships),
                'total_count': len(active_relationships) + len(pending_relationships)
            }
            
        except Exception as e:
            log_error(f"Error getting dashboard stats: {str(e)}")
            return {'active_count': 0, 'pending_count': 0, 'total_count': 0}