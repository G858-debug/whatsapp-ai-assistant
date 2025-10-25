"""
Registration Flow Handler - Phase 1
Handles new user registration for trainers and clients
"""
from typing import Dict
from utils.logger import log_info, log_error


class RegistrationFlowHandler:
    """Handles the registration conversation flow"""
    
    def __init__(self, db, whatsapp, auth_service, reg_service, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.auth = auth_service
        self.reg = reg_service
        self.task = task_service
    
    def handle_new_user(self, phone: str, message: str) -> Dict:
        """Handle first message from new user"""
        try:
            # Check if this is a button response
            msg_lower = message.lower().strip()
            
            if msg_lower in ['register_trainer', 'register as trainer', 'trainer', '💪 register as trainer']:
                return self.start_registration(phone, 'trainer')
            
            elif msg_lower in ['register_client', 'register as client', 'client', '🏃 register as client']:
                return self.start_registration(phone, 'client')
            
            # First time user - send welcome message with registration options
            welcome_msg = (
                "👋 *Welcome to Refiloe!*\n\n"
                "I'm your AI fitness assistant. I can help you:\n\n"
                "🏋️ *As a Trainer:*\n"
                "• Manage clients\n"
                "• Track their progress\n"
                "• Assign fitness habits\n\n"
                "🏃 *As a Client:*\n"
                "• Find trainers\n"
                "• Track your fitness journey\n"
                "• Log your habits\n\n"
                "How would you like to register?"
            )
            
            # Send message with buttons
            buttons = [
                {'id': 'register_trainer', 'title': 'Register as Trainer'},
                {'id': 'register_client', 'title': 'Register as Client'}
            ]
            
            self.whatsapp.send_button_message(phone, welcome_msg, buttons)
            
            return {
                'success': True,
                'response': welcome_msg,
                'handler': 'new_user_welcome'
            }
            
        except Exception as e:
            log_error(f"Error handling new user: {str(e)}")
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error.\n\n"
                "Please try sending me a message again to start registration."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'new_user_error'
            }

    
    def start_registration(self, phone: str, role: str) -> Dict:
        """Start registration process for selected role"""
        try:
            log_info(f"Starting {role} registration for {phone}")
            
            # Get registration fields for this role
            fields = self.reg.get_registration_fields(role)
            
            if not fields:
                return {
                    'success': False,
                    'response': "Sorry, registration is not available right now. Please try again later.",
                    'handler': 'registration_error'
                }
            
            # Create registration task
            task_id = self.task.create_task(
                user_id=phone,  # Use phone as temp ID until we have user_id
                role=role,
                task_type='registration',
                task_data={
                    'current_field_index': 0,
                    'collected_data': {},
                    'role': role
                }
            )
            
            if not task_id:
                return {
                    'success': False,
                    'response': "Sorry, I couldn't start registration. Please try again.",
                    'handler': 'registration_task_error'
                }
            
            # Get first field and send prompt
            first_field = fields[0]
            
            # Send informative message
            intro_msg = (
                f"✅ Great! Let's get you registered as a *{role.title()}*.\n\n"
                f"I'll ask you {len(fields)} questions to set up your profile.\n\n"
                f"💡 *Tip:* You can type */stop* at any time to cancel.\n\n"
                f"Let's start! 👇"
            )
            
            self.whatsapp.send_message(phone, intro_msg)
            
            # Send first field prompt
            self.whatsapp.send_message(phone, first_field['prompt'])
            
            return {
                'success': True,
                'response': first_field['prompt'],
                'handler': 'registration_started'
            }
            
        except Exception as e:
            log_error(f"Error starting registration: {str(e)}")
            
            # Send error message
            error_msg = (
                "❌ *Registration Error*\n\n"
                "Sorry, I encountered an error starting registration.\n\n"
                "Please try again by sending me a message."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'registration_start_error'
            }
    
    def continue_registration(self, phone: str, message: str, role: str, task: Dict) -> Dict:
        """Continue registration by collecting next field"""
        try:
            task_data = task.get('task_data', {})
            current_index = task_data.get('current_field_index', 0)
            collected_data = task_data.get('collected_data', {})
            reg_role = task_data.get('role', role)
            
            # Get all fields
            fields = self.reg.get_registration_fields(reg_role)
            
            # For client self-registration, skip phone_number field (we already have it)
            # Filter out phone_number field for client self-registration
            if reg_role == 'client':
                fields = [f for f in fields if f['name'] != 'phone_number']
            
            if current_index >= len(fields):
                # All fields collected - complete registration
                return self._complete_registration(phone, reg_role, collected_data, task)
            
            # Get current field
            current_field = fields[current_index]
            
            # Validate the input
            is_valid, error_msg = self.reg.validate_field_value(current_field, message)
            
            if not is_valid:
                # Send error and ask again
                error_response = f"❌ {error_msg}\n\n{current_field['prompt']}"
                self.whatsapp.send_message(phone, error_response)
                
                return {
                    'success': True,
                    'response': error_response,
                    'handler': 'registration_validation_error'
                }
            
            # Parse and store the value
            parsed_value = self.reg.parse_field_value(current_field, message)
            collected_data[current_field['name']] = parsed_value
            
            # Move to next field
            current_index += 1
            
            # Update task
            self.task.update_task(
                task_id=task['id'],
                role=reg_role,
                task_data={
                    'current_field_index': current_index,
                    'collected_data': collected_data,
                    'role': reg_role
                }
            )
            
            # Check if we have more fields
            if current_index < len(fields):
                # Send next field prompt
                next_field = fields[current_index]
                
                # Show progress
                progress_msg = f"✅ Got it! ({current_index}/{len(fields)})\n\n"
                full_msg = progress_msg + next_field['prompt']
                
                self.whatsapp.send_message(phone, full_msg)
                
                return {
                    'success': True,
                    'response': full_msg,
                    'handler': 'registration_next_field'
                }
            else:
                # All fields collected - complete registration
                return self._complete_registration(phone, reg_role, collected_data, task)
                
        except Exception as e:
            log_error(f"Error continuing registration: {str(e)}")
            
            # Stop the task
            self.task.stop_task(task['id'], role)
            
            # Send error message
            error_msg = (
                "❌ *Registration Error*\n\n"
                "Sorry, I encountered an error during registration.\n\n"
                "The registration has been cancelled. Please start again by sending me a message."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'registration_continue_error'
            }
    
    def _complete_registration(self, phone: str, role: str, data: Dict, task: Dict) -> Dict:
        """Complete registration and save to database"""
        try:
            log_info(f"Completing {role} registration for {phone}")
            
            # Save registration based on role
            if role == 'trainer':
                success, message, user_id = self.reg.save_trainer_registration(phone, data)
            else:
                success, message, user_id = self.reg.save_client_registration(phone, data)
            
            if success:
                # Complete the task
                self.task.complete_task(task['id'], role)
                
                # Send success message
                self.whatsapp.send_message(phone, message)
                
                # Send welcome message with available commands
                welcome_msg = self._get_welcome_message(role, user_id)
                self.whatsapp.send_message(phone, welcome_msg)
                
                return {
                    'success': True,
                    'response': message,
                    'handler': 'registration_complete'
                }
            else:
                # Registration failed
                error_msg = (
                    f"❌ Registration failed: {message}\n\n"
                    "Please try again or contact support."
                )
                self.whatsapp.send_message(phone, error_msg)
                
                # Stop the task
                self.task.stop_task(task['id'], role)
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'registration_save_error'
                }
                
        except Exception as e:
            log_error(f"Error completing registration: {str(e)}")
            
            # Stop the task
            self.task.stop_task(task['id'], role)
            
            # Send error message
            error_msg = (
                "❌ *Registration Error*\n\n"
                "Sorry, I encountered an error saving your registration.\n\n"
                "The registration has been cancelled. Please start again by sending me a message."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'registration_complete_error'
            }
    
    def _get_welcome_message(self, role: str, user_id: str) -> str:
        """Get welcome message with available commands"""
        if role == 'trainer':
            return (
                "🎉 *Welcome to Refiloe!*\n\n"
                "You're all set up as a trainer. Here's what you can do:\n\n"
                "📋 *Profile Management:*\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n\n"
                "👥 *Client Management:* (Coming in Phase 2)\n"
                "• /invite-trainee - Invite a client\n"
                "• /view-trainees - See your clients\n\n"
                "💪 *Other Commands:*\n"
                "• /help - Show all commands\n"
                "• /logout - Logout\n\n"
                "What would you like to do first?"
            )
        else:
            return (
                "🎉 *Welcome to Refiloe!*\n\n"
                "You're all set up as a client. Here's what you can do:\n\n"
                "📋 *Profile Management:*\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n\n"
                "🔍 *Find Trainers:* (Coming in Phase 2)\n"
                "• /search-trainer - Search for trainers\n"
                "• /view-trainers - See your trainers\n\n"
                "💪 *Other Commands:*\n"
                "• /help - Show all commands\n"
                "• /logout - Logout\n\n"
                "What would you like to do first?"
            )
