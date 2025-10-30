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
                    formatted.append({
                        'id': client.get('client_id', 'N/A'),
                        'name': client.get('name', 'N/A'),
                        'phone': client.get('whatsapp', 'N/A'),
                        'email': client.get('email', 'N/A'),
                        'additional_info': {
                            'goals': client.get('fitness_goals', ''),
                            'experience': client.get('experience_level', '')
                        },
                        'connected_date': rel.get('created_at', '')[:10] if rel.get('created_at') else 'N/A',
                        'status': rel.get('connection_status', status)
                    })
                return formatted
            
            else:  # client
                relationships = self.relationship_service.get_client_trainers(user_id, status)
                # Format for dashboard
                formatted = []
                for trainer in relationships:
                    rel = trainer.get('relationship', {})
                    formatted.append({
                        'id': trainer.get('trainer_id', 'N/A'),
                        'name': trainer.get('name', 'N/A'),
                        'phone': trainer.get('whatsapp', 'N/A'),
                        'email': trainer.get('email', 'N/A'),
                        'additional_info': {
                            'specialization': trainer.get('specialization', ''),
                            'experience': trainer.get('experience_years', ''),
                            'city': trainer.get('city', '')
                        },
                        'connected_date': rel.get('created_at', '')[:10] if rel.get('created_at') else 'N/A',
                        'status': rel.get('connection_status', status)
                    })
                return formatted
            
        except Exception as e:
            log_error(f"Error getting relationships: {str(e)}")
            return []
    
    def remove_relationship(self, user_id: str, role: str, target_id: str) -> Dict:
        """Remove a relationship"""
        try:
            if role == 'trainer':
                success, message = self.relationship_service.remove_trainer_client(user_id, target_id)
            else:
                success, message = self.relationship_service.remove_client_trainer(user_id, target_id)
            
            return {'success': success, 'message': message}
            
        except Exception as e:
            log_error(f"Error removing relationship: {str(e)}")
            return {'success': False, 'message': str(e)}
    
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