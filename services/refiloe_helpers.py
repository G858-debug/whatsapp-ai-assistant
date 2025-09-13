"""Helper functions for Refiloe service - Registration flow orchestration"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.registration import (
    TrainerRegistrationHandler,
    ClientRegistrationHandler,
    RegistrationStateManager,
    EditHandlers
)

class RefiloeHelpers:
    """Orchestrates registration flow and handles confirmation/edit logic"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize handlers
        self.trainer_handler = TrainerRegistrationHandler(supabase_client, config)
        self.client_handler = ClientRegistrationHandler(supabase_client, config)
        self.state_manager = RegistrationStateManager(supabase_client, config)
        self.edit_handler = EditHandlers(supabase_client, config)
    
    def _continue_registration(self, session_id: str, message: str, session_data: Dict) -> Dict:
        """Continue registration process based on current step"""
        try:
            step = session_data.get('step', '')
            user_type = session_data.get('user_type', '')
            
            # Handle confirmation step specially
            if step == 'confirmation' or step == 'confirm':
                return self._handle_confirmation_step(session_id, message, session_data)
            
            # Handle edit mode
            if step.startswith('edit_'):
                return self._handle_edit_mode(session_id, message, session_data)
            
            # Handle edit selection (when user chooses what to edit)
            if step == 'edit' or step == 'edit_selection':
                return self._handle_edit_selection(session_id, message, session_data)
            
            # Regular step processing
            if user_type == 'trainer':
                return self.trainer_handler.process_trainer_step(session_id, step, message)
            elif user_type == 'client':
                return self.client_handler.process_client_step(session_id, step, message)
            else:
                return {
                    'success': False,
                    'message': 'Invalid registration type.'
                }
                
        except Exception as e:
            log_error(f"Error continuing registration: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing registration. Please try again.'
            }
    
    def _handle_confirmation_step(self, session_id: str, message: str, session_data: Dict) -> Dict:
        """Handle the confirmation step with support for yes/no/edit variations"""
        try:
            message_lower = message.lower().strip()
            user_type = session_data.get('user_type', '')
            
            # Check for YES variations
            yes_variations = ['yes', 'y', 'yeah', 'yep', 'correct', 'confirm', 'ok', 'okay', 'sure', '✅', '👍']
            if any(word in message_lower for word in yes_variations):
                # Proceed with registration completion
                if user_type == 'trainer':
                    return self.trainer_handler._confirm_trainer_registration(session_id, 'yes')
                else:
                    return self.client_handler._confirm_client_registration(session_id, 'yes')
            
            # Check for NO variations
            no_variations = ['no', 'n', 'nope', 'incorrect', 'wrong', 'change', '❌', '👎']
            if any(word in message_lower for word in no_variations):
                return self._show_edit_options(session_id, session_data)
            
            # Check for EDIT variations
            edit_variations = ['edit', 'modify', 'change', 'update', 'fix', 'correct']
            if any(word in message_lower for word in edit_variations):
                return self._show_edit_options(session_id, session_data)
            
            # If unclear, provide guidance
            return {
                'success': True,
                'message': (
                    "Please confirm your details:\n\n"
                    "Reply *YES* to complete registration\n"
                    "Reply *EDIT* to change something\n"
                    "Reply *NO* to cancel"
                ),
                'next_step': 'confirmation'
            }
            
        except Exception as e:
            log_error(f"Error handling confirmation: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing confirmation.'
            }
    
    def _show_edit_options(self, session_id: str, session_data: Dict) -> Dict:
        """Show editable fields with current values"""
        try:
            user_type = session_data.get('user_type', '')
            data = session_data.get('data', {})
            
            # Build message showing current details
            message = "📝 *Current Details:*\n\n"
            
            if user_type == 'trainer':
                message += f"1️⃣ *Name:* {data.get('name', 'Not set')}\n"
                message += f"2️⃣ *Email:* {data.get('email', 'Not set')}\n"
                message += f"3️⃣ *Business:* {data.get('business_name', 'Not set')}\n"
                message += f"4️⃣ *Location:* {data.get('location', 'Not set')}\n"
                message += f"5️⃣ *Rate:* R{data.get('pricing_per_session', 0)}/session\n"
                
                specialties = data.get('specialties', [])
                if isinstance(specialties, list):
                    message += f"6️⃣ *Specialties:* {', '.join(specialties)}\n"
                else:
                    message += f"6️⃣ *Specialties:* {specialties}\n"
            else:
                message += f"1️⃣ *Name:* {data.get('name', 'Not set')}\n"
                message += f"2️⃣ *Email:* {data.get('email', 'Not set')}\n"
                message += f"3️⃣ *Emergency Contact:* {data.get('emergency_contact', 'Not set')}\n"
                message += f"4️⃣ *Goals:* {data.get('fitness_goals', 'Not set')}\n"
                message += f"5️⃣ *Fitness Level:* {data.get('fitness_level', 'Not set').title()}\n"
                message += f"6️⃣ *Medical Info:* {data.get('medical_conditions', 'None')}\n"
            
            message += (
                "\n*What would you like to change?*\n"
                "Reply with the number (1-6) of the field you want to edit.\n\n"
                "Or reply *DONE* if everything looks good now."
            )
            
            # Update session to edit selection mode
            self.db.table('registration_sessions').update({
                'step': 'edit_selection',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': message,
                'next_step': 'edit_selection'
            }
            
        except Exception as e:
            log_error(f"Error showing edit options: {str(e)}")
            return {
                'success': False,
                'message': 'Error displaying edit options.'
            }
    
    def _handle_edit_selection(self, session_id: str, message: str, session_data: Dict) -> Dict:
        """Handle selection of field to edit"""
        try:
            message_lower = message.lower().strip()
            
            # Check if user is done editing
            if message_lower in ['done', 'finished', 'complete', 'ok', 'confirm']:
                # Show confirmation again with updated details
                return self._show_confirmation(session_id, session_data)
            
            # Process edit choice
            return self.edit_handler.process_edit_choice(session_id, message)
            
        except Exception as e:
            log_error(f"Error handling edit selection: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing edit selection.'
            }
    
    def _handle_edit_mode(self, session_id: str, message: str, session_data: Dict) -> Dict:
        """Handle editing a specific field"""
        try:
            step = session_data.get('step', '')
            # Extract field name from step (e.g., 'edit_name' -> 'name')
            field_name = step.replace('edit_', '')
            
            # Process the edited value
            result = self.edit_handler.process_edit_value(session_id, field_name, message)
            
            if result.get('success'):
                # After successful edit, show edit options again
                return self._show_edit_options(session_id, session_data)
            
            return result
            
        except Exception as e:
            log_error(f"Error in edit mode: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing edit.'
            }
    
    def _show_confirmation(self, session_id: str, session_data: Dict) -> Dict:
        """Show confirmation message with all details"""
        try:
            user_type = session_data.get('user_type', '')
            data = session_data.get('data', {})
            
            if user_type == 'trainer':
                confirm_msg = (
                    "✨ *Let's confirm your details:*\n\n"
                    f"📝 *Name:* {data.get('name', 'Not set')}\n"
                    f"📧 *Email:* {data.get('email', 'Not set')}\n"
                    f"🏢 *Business:* {data.get('business_name', 'Not set')}\n"
                    f"📍 *Location:* {data.get('location', 'Not set')}\n"
                    f"💰 *Rate:* R{data.get('pricing_per_session', 0)}/session\n"
                )
                
                specialties = data.get('specialties', [])
                if isinstance(specialties, list):
                    confirm_msg += f"🎯 *Specialties:* {', '.join(specialties)}\n"
                else:
                    confirm_msg += f"🎯 *Specialties:* {specialties}\n"
            else:
                confirm_msg = (
                    "✨ *Let's confirm your details:*\n\n"
                    f"📝 *Name:* {data.get('name', 'Not set')}\n"
                )
                
                if data.get('email'):
                    confirm_msg += f"📧 *Email:* {data['email']}\n"
                
                confirm_msg += (
                    f"🚨 *Emergency:* {data.get('emergency_contact', 'Not set')}\n"
                    f"🎯 *Goals:* {data.get('fitness_goals', 'Not set')}\n"
                    f"💪 *Level:* {data.get('fitness_level', 'Not set').title()}\n"
                )
                
                if data.get('medical_conditions'):
                    confirm_msg += f"⚕️ *Medical:* {data['medical_conditions']}\n"
            
            confirm_msg += (
                "\n*Is everything correct?*\n"
                "Reply *YES* to complete registration ✅\n"
                "Reply *EDIT* to make changes ✏️"
            )
            
            # Update session back to confirmation step
            self.db.table('registration_sessions').update({
                'step': 'confirmation',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': confirm_msg,
                'next_step': 'confirmation'
            }
            
        except Exception as e:
            log_error(f"Error showing confirmation: {str(e)}")
            return {
                'success': False,
                'message': 'Error displaying confirmation.'
            }
    
    def _restart_registration(self, session_id: str, field_to_edit: Optional[str] = None) -> Dict:
        """Enhanced restart that allows editing specific fields"""
        try:
            # Get session data
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session not found.'
                }
            
            if field_to_edit:
                # Jump directly to editing that field
                user_type = session.data.get('user_type', '')
                
                # Map field names to steps
                field_to_step = {
                    'name': 'edit_name',
                    'email': 'edit_email',
                    'business': 'edit_business_name',
                    'location': 'edit_location',
                    'price': 'edit_pricing',
                    'specialties': 'edit_specialties',
                    'emergency': 'edit_emergency_contact',
                    'goals': 'edit_goals',
                    'fitness': 'edit_fitness_level',
                    'medical': 'edit_medical_conditions'
                }
                
                if field_to_edit in field_to_step:
                    # Update session to edit mode for specific field
                    self.db.table('registration_sessions').update({
                        'step': field_to_step[field_to_edit],
                        'updated_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('id', session_id).execute()
                    
                    # Get appropriate prompt
                    prompts = {
                        'name': "What's your correct name?",
                        'email': "What's your correct email?",
                        'business': "What's your business name?",
                        'location': "What's your location?",
                        'price': "What's your rate per session? (just the number)",
                        'specialties': "What are your specialties? (comma-separated)",
                        'emergency': "Who should we contact in emergency? (Name and phone)",
                        'goals': "What are your fitness goals?",
                        'fitness': "What's your fitness level?\n1. Beginner\n2. Intermediate\n3. Advanced",
                        'medical': "Any medical conditions or injuries? (or type 'none')"
                    }
                    
                    return {
                        'success': True,
                        'message': prompts.get(field_to_edit, "Please enter the new value:"),
                        'editing': field_to_edit
                    }
            
            # If no specific field, show edit options
            return self._show_edit_options(session_id, session.data)
            
        except Exception as e:
            log_error(f"Error restarting registration: {str(e)}")
            return {
                'success': False,
                'message': 'Error restarting registration.'
            }
