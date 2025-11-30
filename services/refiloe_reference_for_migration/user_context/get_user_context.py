"""
Get User Context
Get complete user context including trainer/client info with dual role support
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def get_user_context(self, phone: str, selected_role: str = None) -> Dict:
    """Get complete user context including trainer/client info with dual role support"""
    try:
        context = {}
        
        # Check both trainer and client tables
        trainer = self.db.table('trainers').select('*').eq(
            'whatsapp', phone
        ).execute()
        
        client = self.db.table('clients').select(
            '*, trainers(name, business_name, first_name, last_name)'
        ).eq('whatsapp', phone).execute()
        
        has_trainer = trainer.data and len(trainer.data) > 0
        has_client = client.data and len(client.data) > 0
        
        # Determine if user has dual roles
        context['has_dual_roles'] = has_trainer and has_client
        context['available_roles'] = []
        
        if has_trainer:
            context['available_roles'].append('trainer')
            context['trainer_data'] = trainer.data[0]
        
        if has_client:
            context['available_roles'].append('client')
            context['client_data'] = client.data[0]
        
        # Handle role selection for dual role users
        if context['has_dual_roles'] and not selected_role:
            # Check if user has a stored role preference
            role_pref = self.db.table('conversation_states').select('role_preference').eq(
                'phone', phone
            ).execute()
            
            if role_pref.data and role_pref.data[0].get('role_preference'):
                selected_role = role_pref.data[0]['role_preference']
            else:
                # No role selected - need role selection
                context['user_type'] = 'dual_role_selection_needed'
                context['user_data'] = None
                return context
        
        # Set active role (either selected or single available role)
        if selected_role:
            context['active_role'] = selected_role
        elif has_trainer and not has_client:
            context['active_role'] = 'trainer'
        elif has_client and not has_trainer:
            context['active_role'] = 'client'
        else:
            context['user_type'] = 'unknown'
            context['user_data'] = None
            return context
        
        # Build context based on active role
        if context['active_role'] == 'trainer' and has_trainer:
            trainer_data = trainer.data[0]
            context['user_type'] = 'trainer'
            
            # Extract first name for friendly conversation
            first_name = trainer_data.get('first_name')
            if not first_name:
                full_name = trainer_data.get('name', 'Trainer')
                first_name = full_name.split()[0] if full_name else 'Trainer'
            
            context['user_data'] = {
                **trainer_data,
                'name': first_name,
                'full_name': trainer_data.get('name'),
                'first_name': first_name,
                'last_name': trainer_data.get('last_name', '')
            }
            
            # Get active clients count
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_data['id']
            ).eq('status', 'active').execute()
            
            context['active_clients'] = len(clients.data) if clients.data else 0
            
        elif context['active_role'] == 'client' and has_client:
            client_data = client.data[0]
            context['user_type'] = 'client'
            
            # Extract first name for client
            first_name = client_data.get('first_name')
            if not first_name:
                full_name = client_data.get('name', 'there')
                first_name = full_name.split()[0] if full_name else 'there'
            
            context['user_data'] = {
                **client_data,
                'name': first_name,
                'full_name': client_data.get('name'),
                'first_name': first_name,
                'last_name': client_data.get('last_name', '')
            }
            
            if client_data.get('trainers'):
                trainer_first_name = client_data['trainers'].get('first_name')
                if trainer_first_name:
                    context['trainer_name'] = trainer_first_name
                else:
                    context['trainer_name'] = (
                        client_data['trainers'].get('business_name') or 
                        client_data['trainers'].get('name', '').split()[0] if client_data['trainers'].get('name') else 'your trainer'
                    )
        
        return context
        
    except Exception as e:
        log_error(f"Error getting user context: {str(e)}")
        return {'user_type': 'unknown', 'user_data': None}
