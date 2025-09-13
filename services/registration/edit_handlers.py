"""Registration edit handlers"""
from typing import Dict
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class EditHandlers:
    """Handles editing during registration"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def process_edit_choice(self, session_id: str, choice: str) -> Dict:
        """Process edit choice during registration"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': "Session not found."
                }
            
            user_type = session.data['user_type']
            
            if user_type == 'trainer':
                return self._process_trainer_edit(session_id, choice)
            else:
                return self._process_client_edit(session_id, choice)
                
        except Exception as e:
            log_error(f"Error processing edit choice: {str(e)}")
            return {
                'success': False,
                'message': "Error processing edit request."
            }
    
    def _process_trainer_edit(self, session_id: str, choice: str) -> Dict:
        """Process trainer field edit"""
        edit_map = {
            '1': ('name', "What's your correct name?"),
            '2': ('email', "What's your correct email?"),
            '3': ('business_name', "What's your correct business name?"),
            '4': ('location', "What's your correct location?"),
            '5': ('pricing', "What's your correct rate per session?"),
            '6': ('specialties', "What are your specialties?")
        }
        
        if choice not in edit_map:
            return {
                'success': False,
                'message': "Please choose a number from 1-6"
            }
        
        step, message = edit_map[choice]
        
        # Update session to editing mode
        self.db.table('registration_sessions').update({
            'step': f'edit_{step}',
            'updated_at': datetime.now(self.sa_tz).isoformat()
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': message,
            'editing': step
        }
    
    def _process_client_edit(self, session_id: str, choice: str) -> Dict:
        """Process client field edit"""
        edit_map = {
            '1': ('name', "What's your correct name?"),
            '2': ('email', "What's your correct email?"),
            '3': ('emergency_contact', "Who should we contact in emergency? (Name and phone)"),
            '4': ('goals', "What are your fitness goals?"),
            '5': ('fitness_level', "What's your fitness level? (1. Beginner, 2. Intermediate, 3. Advanced)"),
            '6': ('medical_conditions', "Any medical conditions or injuries?")
        }
        
        if choice not in edit_map:
            return {
                'success': False,
                'message': "Please choose a number from 1-6"
            }
        
        step, message = edit_map[choice]
        
        # Update session to editing mode
        self.db.table('registration_sessions').update({
            'step': f'edit_{step}',
            'updated_at': datetime.now(self.sa_tz).isoformat()
        }).eq('id', session_id).execute()
        
        return {
            'success': True,
            'message': message,
            'editing': step
        }
    
    def process_edit_value(self, session_id: str, field: str, value: str) -> Dict:
        """Process edited value"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': "Session not found."
                }
            
            current_data = session.data.get('data', {})
            
            # Update the specific field
            if field == 'fitness_level':
                # Map response to fitness level
                level_map = {
                    '1': 'beginner',
                    '2': 'intermediate',
                    '3': 'advanced'
                }
                value = level_map.get(value, value)
            elif field == 'pricing':
                # Extract number
                import re
                numbers = re.findall(r'\d+', value)
                if numbers:
                    value = float(numbers[0])
                else:
                    return {
                        'success': False,
                        'message': "Please enter a valid price"
                    }
            elif field == 'specialties':
                # Parse as list
                value = [s.strip() for s in value.split(',')]
            
            current_data[field] = value
            
            # Update session back to confirm step
            self.db.table('registration_sessions').update({
                'data': current_data,
                'step': 'confirm',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            # Build confirmation message
            return self._build_confirmation_message(session.data['user_type'], current_data)
            
        except Exception as e:
            log_error(f"Error processing edit value: {str(e)}")
            return {
                'success': False,
                'message': "Error updating information."
            }
    
    def _build_confirmation_message(self, user_type: str, data: Dict) -> Dict:
        """Build confirmation message after edit"""
        if user_type == 'trainer':
            confirm_msg = (
                "Updated! Let me confirm your details:\n\n"
                f"📝 Name: {data.get('name', 'Not set')}\n"
                f"📧 Email: {data.get('email', 'Not set')}\n"
                f"🏢 Business: {data.get('business_name', 'Not set')}\n"
                f"📍 Location: {data.get('location', 'Not set')}\n"
                f"💰 Rate: R{data.get('pricing_per_session', 0)}/session\n"
            )
            
            if data.get('specialties'):
                specialties = data['specialties'] if isinstance(data['specialties'], list) else [data['specialties']]
                confirm_msg += f"🎯 Specialties: {', '.join(specialties)}\n"
        else:
            confirm_msg = (
                "Updated! Let me confirm your details:\n\n"
                f"📝 Name: {data.get('name', 'Not set')}\n"
            )
            
            if data.get('email'):
                confirm_msg += f"📧 Email: {data['email']}\n"
            
            confirm_msg += (
                f"🚨 Emergency: {data.get('emergency_contact', 'Not set')}\n"
                f"🎯 Goals: {data.get('fitness_goals', 'Not set')}\n"
                f"💪 Level: {data.get('fitness_level', 'Not set').title()}\n"
            )
            
            if data.get('medical_conditions'):
                confirm_msg += f"⚕️ Medical: {data['medical_conditions']}\n"
        
        confirm_msg += "\nIs everything correct now? (Yes/No)"
        
        return {
            'success': True,
            'message': confirm_msg,
            'next_step': 'confirm'
        }