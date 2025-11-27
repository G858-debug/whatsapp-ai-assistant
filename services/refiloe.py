"""Refiloe AI service - Main conversation handler"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class RefiloeService:
    """Main Refiloe AI conversation service"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Conversation states
        self.STATES = {
            'IDLE': 'idle',
            'AWAITING_RESPONSE': 'awaiting_response',
            'REGISTRATION': 'registration',
            'BOOKING': 'booking',
            'ASSESSMENT': 'assessment',
            'HABIT_TRACKING': 'habit_tracking'
        }
    
    def get_conversation_state(self, phone: str) -> Dict:
        """Get current conversation state for user"""
        try:
            result = self.db.table('conversation_states').select('*').eq(
                'phone_number', phone
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Create new state
            return self.create_conversation_state(phone)
            
        except Exception as e:
            log_error(f"Error getting conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def create_conversation_state(self, phone: str) -> Dict:
        """Create new conversation state"""
        try:
            state_data = {
                'phone_number': phone,
                'state': self.STATES['IDLE'],
                'context': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('conversation_states').insert(
                state_data
            ).execute()
            
            return result.data[0] if result.data else state_data
            
        except Exception as e:
            log_error(f"Error creating conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def update_conversation_state(self, phone: str, state: str, 
                                 context: Dict = None) -> bool:
        """Update or create conversation state"""
        try:
            # First try to get existing state
            existing = self.db.table('conversation_states').select('id').eq(
                'phone_number', phone
            ).execute()
            
            update_data = {
                'phone_number': phone,  # Include phone for insert
                'state': state,
                'context': context or {},
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if existing.data:
                # Update existing row
                result = self.db.table('conversation_states').update(
                    update_data
                ).eq('phone_number', phone).execute()
                log_info(f"Updated conversation state for {phone}: {state}")
            else:
                # Insert new row
                update_data['created_at'] = datetime.now(self.sa_tz).isoformat()
                result = self.db.table('conversation_states').insert(
                    update_data
                ).execute()
                log_info(f"Created new conversation state for {phone}: {state}")
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating conversation state: {str(e)}")
            return False
    
    def get_conversation_history(self, phone: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            result = self.db.table('message_history').select('*').eq(
                'phone_number', phone
            ).order('created_at', desc=True).limit(limit).execute()
            
            # Reverse to get chronological order
            return list(reversed(result.data)) if result.data else []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def save_message(self, phone: str, message: str, sender: str, 
                    intent: str = None) -> bool:
        """Save message to history"""
        try:
            message_data = {
                'phone_number': phone,
                'message': message,
                'sender': sender,  # 'user' or 'bot'
                'intent': intent,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('message_history').insert(
                message_data
            ).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error saving message: {str(e)}")
            return False
    
    def clear_conversation_state(self, phone: str) -> bool:
        """Clear conversation state (reset to idle)"""
        try:
            return self.update_conversation_state(phone, self.STATES['IDLE'], {})
            
        except Exception as e:
            log_error(f"Error clearing conversation state: {str(e)}")
            return False
    
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

    def handle_role_selection(self, phone: str, selected_role: str) -> Dict:
        """Handle role selection for dual role users"""
        try:
            # Store role preference
            self.db.table('conversation_states').upsert({
                'phone': phone,
                'role_preference': selected_role,
                'updated_at': datetime.now().isoformat()
            }, on_conflict='phone').execute()
            
            # Get context with selected role
            context = self.get_user_context(phone, selected_role)
            
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if selected_role == 'trainer':
                message = f"Great! You're now using Refiloe as a trainer. 💪\n\nWhat can I help you with today?"
            else:
                message = f"Perfect! You're now using Refiloe as a client. 🏃‍♀️\n\nWhat can I help you with today?"
            
            # Add role switch button for easy switching
            buttons = [{
                'id': 'switch_role',
                'title': f'Switch to {("Client" if selected_role == "trainer" else "Trainer")}'
            }]
            
            whatsapp_service.send_button_message(phone, message, buttons)
            
            return {'success': True, 'role_selected': selected_role}
            
        except Exception as e:
            log_error(f"Error handling role selection: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_role_selection_message(self, phone: str, context: Dict) -> Dict:
        """Send role selection buttons for dual role users"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get user's name from either role
            name = "there"
            if context.get('trainer_data'):
                trainer_name = context['trainer_data'].get('first_name') or context['trainer_data'].get('name', '').split()[0]
                if trainer_name:
                    name = trainer_name
            elif context.get('client_data'):
                client_name = context['client_data'].get('first_name') or context['client_data'].get('name', '').split()[0]
                if client_name:
                    name = client_name
            
            message = f"Hi {name}! 👋\n\nI see you're both a trainer and a client. Which role would you like to use today?"
            
            buttons = [
                {'id': 'role_trainer', 'title': '💪 Trainer'},
                {'id': 'role_client', 'title': '🏃‍♀️ Client'}
            ]
            
            return whatsapp_service.send_button_message(phone, message, buttons)
            
        except Exception as e:
            log_error(f"Error sending role selection message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_role_switch(self, phone: str) -> Dict:
        """Handle role switching for dual role users"""
        try:
            # Get current context to check available roles
            context = self.get_user_context(phone)
            
            if not context.get('has_dual_roles'):
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                whatsapp_service.send_message(phone, "You only have one role available. No switching needed! 😊")
                return {'success': True, 'message': 'Single role user'}
            
            # Get current role preference
            current_role = context.get('active_role', 'trainer')
            new_role = 'client' if current_role == 'trainer' else 'trainer'
            
            # Switch the role
            return self.handle_role_selection(phone, new_role)
            
        except Exception as e:
            log_error(f"Error handling role switch: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_slash_command(self, phone: str, command: str) -> Dict:
        """Handle slash commands for trainers and clients"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get user context to determine available commands
            context = self.get_user_context(phone)
            user_type = context.get('user_type', 'unknown')
            user_data = context.get('user_data')
            
            # Handle dual role selection needed
            if user_type == 'dual_role_selection_needed':
                response = "Please select your role first using the buttons above, then you can use commands."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Route to specific command handlers
            if command == '/help':
                return self._handle_help_command(phone, user_type, user_data)
            elif command == '/profile':
                return self._handle_profile_command(phone, user_type, user_data)
            elif command == '/edit_profile':
                return self._handle_edit_profile_command(phone, user_type, user_data)
            elif command == '/registration':
                return self._handle_registration_command(phone, user_type)
            elif command == '/clients' and user_type == 'trainer':
                return self._handle_clients_command(phone, user_data)
            elif command == '/add_client' and user_type == 'trainer':
                return self._handle_add_client_command(phone, user_data)
            elif command == '/pending_requests' and user_type == 'trainer':
                return self._handle_pending_requests_command(phone, user_data)
            elif command.startswith('/approve_client') and user_type == 'trainer':
                return self._handle_approve_client_command(phone, command, user_data)
            elif command.startswith('/decline_client') and user_type == 'trainer':
                return self._handle_decline_client_command(phone, command, user_data)
            elif command == '/trainer' and user_type == 'client':
                return self._handle_trainer_info_command(phone, user_data)
            elif command == '/invitations' and user_type == 'client':
                return self._handle_client_invitations_command(phone, user_data)
            elif command.startswith('/accept_invitation') and user_type == 'client':
                return self._handle_accept_invitation_command(phone, command, user_data)
            elif command.startswith('/decline_invitation') and user_type == 'client':
                return self._handle_decline_invitation_command(phone, command, user_data)
            elif command == '/find_trainer' and user_type == 'client':
                return self._handle_find_trainer_command(phone, user_data)
            elif command.startswith('/request_trainer') and user_type == 'client':
                return self._handle_request_trainer_command(phone, command, user_data)
            elif command.startswith('/add_trainer') and user_type == 'client':
                return self._handle_add_trainer_command(phone, command, user_data)
            elif command == '/habits':
                return self._handle_habits_command(phone, user_type, user_data)
            elif command == '/log_habit':
                return self._handle_log_habit_command(phone, user_type, user_data)
            elif command == '/habit_streak':
                return self._handle_habit_streak_command(phone, user_type, user_data)
            elif command == '/habit_goals':
                return self._handle_habit_goals_command(phone, user_type, user_data)
            elif command == '/habit_progress' and user_type == 'client':
                return self._handle_habit_progress_command(phone, user_data)
            elif command == '/setup_habits' and user_type == 'trainer':
                return self._handle_setup_habits_command(phone, user_data)
            elif command == '/habit_challenges':
                return self._handle_habit_challenges_command(phone, user_type, user_data)
            elif command == '/habit_analytics' and user_type == 'trainer':
                return self._handle_habit_analytics_command(phone, user_type, user_data)
            elif command == '/send_reminders' and user_type == 'trainer':
                return self._handle_send_reminders_command(phone, user_type, user_data)
            elif command == '/create_challenge' and user_type == 'trainer':
                return self._handle_create_challenge_command(phone, user_data)
            elif command == '/test_flows':
                return self._test_habit_flows(phone, user_type, user_data)
            elif command == '/reset_me':
                return self._handle_reset_command(phone)
            else:
                # Unknown command
                available_commands = self._get_available_commands(user_type)
                response = (
                    f"❓ Unknown command: `{command}`\n\n"
                    f"Available commands:\n{available_commands}\n\n"
                    f"Type `/help` for detailed information."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
                
        except Exception as e:
            log_error(f"Error handling slash command {command}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_available_commands(self, user_type: str) -> str:
        """Get list of available commands for user type"""
        if user_type == 'trainer':
            return (
                "• `/help` - Show all commands\n"
                "• `/profile` - View your profile\n"
                "• `/edit_profile` - Edit your profile\n"
                "• `/clients` - Manage your clients\n"
                "• `/add_client` - Add a new client\n"
                "• `/pending_requests` - View client requests\n"
                "• `/approve_client [name]` - Approve client\n"
                "• `/decline_client [name]` - Decline client\n"
                "• `/habits` - Client habit management\n"
                "• `/setup_habits` - Setup client habits\n"
                "• `/habit_challenges` - Manage habit challenges\n"
                "• `/create_challenge` - Create new challenge\n"
                "• `/habit_analytics` - View habit analytics\n"
                "• `/send_reminders` - Send habit reminders"
            )
        elif user_type == 'client':
            return (
                "• `/help` - Show all commands\n"
                "• `/profile` - View your profile\n"
                "• `/edit_profile` - Edit your profile\n"
                "• `/trainer` - View trainer info\n"
                "• `/invitations` - View trainer invitations\n"
                "• `/accept_invitation [token]` - Accept invitation\n"
                "• `/decline_invitation [token]` - Decline invitation\n"
                "• `/find_trainer` - Search for trainers\n"
                "• `/request_trainer [email/phone]` - Request specific trainer\n"
                "• `/add_trainer [email/phone]` - Add trainer directly\n"
                "• `/habits` - View your habit progress\n"
                "• `/log_habit` - Log today's habits\n"
                "• `/habit_progress` - Detailed progress view\n"
                "• `/habit_streak` - Check your streaks\n"
                "• `/habit_goals` - Manage habit goals\n"
                "• `/habit_challenges` - View available challenges"
            )
        else:
            return (
                "• `/help` - Show all commands\n"
                "• `/registration` - Start registration"
            )

    def handle_message(self, phone: str, text: str) -> Dict:
        """Handle incoming WhatsApp message - main entry point"""
        try:
            # Check for reset command FIRST
            if text.strip().lower() == '/reset_me':
                return self._handle_reset_command(phone)
            
            # Check for role selection commands
            if text.strip().lower() in ['role_trainer', 'role_client']:
                selected_role = 'trainer' if text.strip().lower() == 'role_trainer' else 'client'
                return self.handle_role_selection(phone, selected_role)
            
            # Check for role switch command
            if text.strip().lower() == 'switch_role':
                return self._handle_role_switch(phone)
            
            # Check for slash commands
            if text.strip().startswith('/'):
                return self._handle_slash_command(phone, text.strip().lower())
            
            # Check for test commands (optional - for easier testing)
            if text.strip().lower().startswith('/test_'):
                return self._handle_test_command(phone, text.strip().lower())
            
            # Import services we need
            from app import app
            ai_handler = app.config['services']['ai_handler']
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get user context using existing method
            context = self.get_user_context(phone)
            
            # Handle dual role selection needed
            if context['user_type'] == 'dual_role_selection_needed':
                return self.send_role_selection_message(phone, context)
            
            # Determine sender type and data from context
            if context['user_type'] == 'trainer':
                sender_type = 'trainer'
                sender_data = context['user_data']
            elif context['user_type'] == 'client':
                sender_type = 'client'
                sender_data = context['user_data']
            else:
                sender_type = 'unknown'
                sender_data = {'name': 'there', 'whatsapp': phone}
            
            # Get conversation history using existing method
            history = self.get_conversation_history(phone)
            history_text = [h['message'] for h in history] if history else []
            
            # Save incoming message using existing method
            self.save_message(phone, text, 'user')
            
            # Get conversation state early
            conv_state = self.get_conversation_state(phone)
            
            # CHECK IF USER IS ALREADY IN REGISTRATION FLOW - BEFORE BUTTON CHECKS
            if conv_state.get('state') == 'REGISTRATION':
                log_info(f"User {phone} is in registration flow, context: {conv_state.get('context', {})}")
                
                registration_type = conv_state.get('context', {}).get('type')
                
                if registration_type == 'trainer':
                    try:
                        from services.registration.trainer_registration import TrainerRegistrationHandler
                        from services.registration.registration_state import RegistrationStateManager
                        
                        # Initialize handlers
                        reg_handler = TrainerRegistrationHandler(self.db, whatsapp_service)
                        state_manager = RegistrationStateManager(self.db)
                        
                        # Get comprehensive registration summary
                        reg_summary = state_manager.get_registration_summary(phone)
                        
                        if reg_summary.get('exists'):
                            # Check if registration is expired
                            if reg_summary.get('is_expired'):
                                log_info(f"Registration expired for {phone}, starting fresh")
                                # Clean up expired state and start fresh
                                state_manager.cleanup_expired_registrations()
                                welcome_message = reg_handler.start_registration(phone)
                                whatsapp_service.send_message(phone, welcome_message)
                                
                                # Update conversation state
                                self.update_conversation_state(phone, 'REGISTRATION', {
                                    'type': 'trainer',
                                    'current_step': 0
                                })
                                
                                return {'success': True, 'response': welcome_message}
                            
                            # Check if can resume
                            if not reg_summary.get('can_resume'):
                                log_info(f"Registration cannot be resumed for {phone}, starting fresh")
                                welcome_message = reg_handler.start_registration(phone)
                                whatsapp_service.send_message(phone, welcome_message)
                                
                                # Update conversation state
                                self.update_conversation_state(phone, 'REGISTRATION', {
                                    'type': 'trainer',
                                    'current_step': 0
                                })
                                
                                return {'success': True, 'response': welcome_message}
                            
                            current_step = reg_summary.get('current_step', 0)
                            data = reg_summary.get('data', {})
                            progress_pct = reg_summary.get('progress_percentage', 0)
                            
                            log_info(f"Resuming registration for {phone}: step {current_step}, {progress_pct}% complete")
                            
                            # Process the registration step using correct method
                            reg_result = reg_handler.handle_registration_response(
                                phone, text, current_step, data
                            )
                            
                            if reg_result.get('success'):
                                # Send response message
                                if reg_result.get('message'):
                                    whatsapp_service.send_message(phone, reg_result['message'])
                                
                                # Check if registration is complete
                                if not reg_result.get('continue', True):
                                    # Registration completed
                                    self.update_conversation_state(phone, 'IDLE')
                                    log_info(f"Trainer registration completed for {phone}")
                                else:
                                    # Update conversation state with new step
                                    new_step = reg_result.get('next_step', current_step + 1)
                                    new_context = conv_state.get('context', {})
                                    new_context['current_step'] = new_step
                                    self.update_conversation_state(phone, 'REGISTRATION', new_context)
                                    log_info(f"Updated registration step for {phone} to {new_step}")
                                
                                return {'success': True, 'response': reg_result.get('message', '')}
                            else:
                                # Validation error - send error message but continue registration
                                if reg_result.get('message'):
                                    whatsapp_service.send_message(phone, reg_result['message'])
                                return {'success': True, 'response': reg_result.get('message', '')}
                        else:
                            # No registration state found - restart registration
                            log_warning(f"No registration state found for {phone}, restarting")
                            welcome_message = reg_handler.start_registration(phone)
                            whatsapp_service.send_message(phone, welcome_message)
                            
                            # Update conversation state
                            self.update_conversation_state(phone, 'REGISTRATION', {
                                'type': 'trainer',
                                'current_step': 0
                            })
                            
                            return {'success': True, 'response': welcome_message}
                        
                    except ImportError as e:
                        log_error(f"Import error in trainer registration: {str(e)}")
                        error_msg = "Registration system temporarily unavailable. Please try again later."
                        whatsapp_service.send_message(phone, error_msg)
                        self.update_conversation_state(phone, 'IDLE')
                        return {'success': False, 'response': error_msg}
                            
                    except Exception as e:
                        log_error(f"Error processing trainer registration: {str(e)}")
                        error_msg = "Something went wrong with your registration. Let's start over."
                        whatsapp_service.send_message(phone, error_msg)
                        self.update_conversation_state(phone, 'IDLE')
                        return {'success': False, 'response': error_msg}
                
                elif registration_type == 'client':
                    try:
                        from services.registration.client_registration import ClientRegistrationHandler
                        reg = ClientRegistrationHandler(self.db, whatsapp_service)
                        
                        # Process the registration step
                        reg_result = reg.process_step(phone, text, current_step)
                        
                        if reg_result.get('message'):
                            whatsapp_service.send_message(phone, reg_result['message'])
                        
                        # Update state or clear if complete
                        if reg_result.get('complete'):
                            self.update_conversation_state(phone, 'IDLE')
                            log_info(f"Client registration completed for {phone}")
                        else:
                            # Update the conversation state with new step
                            new_context = conv_state.get('context', {})
                            new_context['current_step'] = reg_result.get('next_step', current_step + 1)
                            self.update_conversation_state(phone, 'REGISTRATION', new_context)
                        
                        return {'success': True, 'response': reg_result.get('message', '')}
                        
                    except ImportError:
                        # Try old class name for backward compatibility
                        try:
                            from services.registration.client_registration import ClientRegistration
                            reg = ClientRegistration(self.db)
                            reg_result = reg.process_registration_response(phone, text)
                            
                            if reg_result.get('message'):
                                whatsapp_service.send_message(phone, reg_result['message'])
                            
                            if reg_result.get('complete'):
                                self.update_conversation_state(phone, 'IDLE')
                            
                            return {'success': True, 'response': reg_result.get('message', '')}
                        except:
                            log_error("Client registration module not found")
                            self.update_conversation_state(phone, 'IDLE')
                            
                    except Exception as e:
                        log_error(f"Error processing client registration: {str(e)}")
                        self.update_conversation_state(phone, 'IDLE')
            
            # CHECK FOR HABIT LOGGING FLOW
            if conv_state.get('state') == 'HABIT_LOGGING':
                log_info(f"User {phone} is in habit logging flow")
                
                try:
                    result = self._handle_habit_logging_step(phone, text, conv_state.get('context', {}))
                    
                    if result.get('success'):
                        if result.get('completed'):
                            # Habit logging completed
                            whatsapp_service.send_message(phone, result['message'])
                            self.update_conversation_state(phone, 'IDLE')
                        else:
                            # Continue habit logging
                            whatsapp_service.send_message(phone, result['message'])
                            if result.get('context'):
                                self.update_conversation_state(phone, 'HABIT_LOGGING', result['context'])
                        
                        return {'success': True, 'response': result['message']}
                    else:
                        # Error in processing
                        whatsapp_service.send_message(phone, result['message'])
                        return {'success': False, 'response': result['message']}
                        
                except Exception as e:
                    log_error(f"Error processing habit logging: {str(e)}")
                    error_msg = "❌ Sorry, there was an error logging your habits. Please try again with `/log_habit`."
                    whatsapp_service.send_message(phone, error_msg)
                    self.update_conversation_state(phone, 'IDLE')
                    return {'success': False, 'response': error_msg}
            
            # CHECK FOR HABIT SETUP FLOW
            if conv_state.get('state') == 'HABIT_SETUP':
                log_info(f"User {phone} is in habit setup flow")
                
                try:
                    result = self._handle_habit_setup_step(phone, text, conv_state.get('context', {}))
                    
                    if result.get('success'):
                        if result.get('completed'):
                            # Habit setup completed
                            whatsapp_service.send_message(phone, result['message'])
                            self.update_conversation_state(phone, 'IDLE')
                        else:
                            # Continue habit setup
                            whatsapp_service.send_message(phone, result['message'])
                            if result.get('context'):
                                self.update_conversation_state(phone, 'HABIT_SETUP', result['context'])
                        
                        return {'success': True, 'response': result['message']}
                    else:
                        # Error in processing
                        whatsapp_service.send_message(phone, result['message'])
                        return {'success': False, 'response': result['message']}
                        
                except Exception as e:
                    log_error(f"Error processing habit setup: {str(e)}")
                    error_msg = "❌ Sorry, there was an error setting up habits. Please try again with `/setup_habits`."
                    whatsapp_service.send_message(phone, error_msg)
                    self.update_conversation_state(phone, 'IDLE')
                    return {'success': False, 'response': error_msg}
            
            # CHECK FOR CHALLENGE CREATION FLOW
            if conv_state.get('state') == 'CHALLENGE_CREATION':
                log_info(f"User {phone} is in challenge creation flow")
                
                try:
                    result = self._handle_challenge_creation_step(phone, text, conv_state.get('context', {}))
                    
                    if result.get('success'):
                        if result.get('completed'):
                            # Challenge creation completed
                            whatsapp_service.send_message(phone, result['message'])
                            self.update_conversation_state(phone, 'IDLE')
                        else:
                            # Continue challenge creation
                            whatsapp_service.send_message(phone, result['message'])
                            if result.get('context'):
                                self.update_conversation_state(phone, 'CHALLENGE_CREATION', result['context'])
                        
                        return {'success': True, 'response': result['message']}
                    else:
                        # Error in processing
                        whatsapp_service.send_message(phone, result['message'])
                        return {'success': False, 'response': result['message']}
                        
                except Exception as e:
                    log_error(f"Error processing challenge creation: {str(e)}")
                    error_msg = "❌ Sorry, there was an error creating the challenge. Please try again with `/create_challenge`."
                    whatsapp_service.send_message(phone, error_msg)
                    self.update_conversation_state(phone, 'IDLE')
                    return {'success': False, 'response': error_msg}
            
            # CHECK FOR CLIENT INVITATION RESPONSES
            if sender_type == 'unknown':
                # Check if this is a response to a trainer invitation
                invitation_response = self._handle_invitation_response(phone, text)
                if invitation_response.get('handled'):
                    whatsapp_service.send_message(phone, invitation_response['message'])
                    return {'success': True, 'response': invitation_response['message']}
                
                # Check if this is a trainer request by email
                trainer_request = self._handle_trainer_request_by_email(phone, text)
                if trainer_request.get('handled'):
                    whatsapp_service.send_message(phone, trainer_request['message'])
                    return {'success': True, 'response': trainer_request['message']}
            
            # CHECK FOR TEXT CLIENT ADDITION FLOW
            if conv_state.get('state') == 'TEXT_CLIENT_ADDITION':
                log_info(f"User {phone} is in text client addition flow")
                
                try:
                    result = self._handle_text_client_addition_step(phone, text, conv_state.get('context', {}))
                    
                    if result.get('success'):
                        if result.get('completed'):
                            # Client addition completed
                            whatsapp_service.send_message(phone, result['message'])
                            self.clear_conversation_state(phone)
                        else:
                            # Continue to next step
                            whatsapp_service.send_message(phone, result['message'])
                            self.update_conversation_state(phone, 'TEXT_CLIENT_ADDITION', result['context'])
                        
                        return {'success': True, 'response': result['message']}
                    else:
                        # Error in processing
                        whatsapp_service.send_message(phone, result['message'])
                        return {'success': False, 'response': result['message']}
                        
                except Exception as e:
                    log_error(f"Error processing text client addition: {str(e)}")
                    error_msg = "❌ Sorry, there was an error. Let's try again. What's your client's name?"
                    whatsapp_service.send_message(phone, error_msg)
                    return {'success': False, 'response': error_msg}
            
            # CHECK FOR PENDING CLIENT CONFIRMATION
            if conv_state.get('state') == 'PENDING_CLIENT_CONFIRMATION':
                log_info(f"User {phone} is confirming client addition")
                
                response_lower = text.strip().lower()
                pending_client = conv_state.get('context', {}).get('pending_client', {})
                
                if response_lower in ['yes', 'y', 'confirm', 'ok', 'proceed']:
                    # Confirm and add the client
                    try:
                        # Create the client record
                        client_data = {
                            'trainer_id': pending_client['trainer_id'],
                            'name': pending_client['name'],
                            'whatsapp': pending_client['whatsapp'],
                            'email': pending_client.get('email'),
                            'status': 'active',
                            'package_type': 'single',
                            'sessions_remaining': 1,
                            'experience_level': pending_client.get('experience_level', 'Beginner'),  # Default to Beginner
                            'health_conditions': pending_client.get('health_conditions', 'None specified'),  # Default
                            'fitness_goals': pending_client.get('fitness_goals', 'General fitness'),  # Default
                            'availability': pending_client.get('availability', 'Flexible'),  # Default
                            'created_at': datetime.now().isoformat()
                        }
                        
                        result = self.db.table('clients').insert(client_data).execute()
                        
                        if result.data:
                            client_id = result.data[0]['id']
                            client_name = pending_client['name']
                            client_phone = pending_client['whatsapp']
                            
                            # Clear conversation state
                            self.clear_conversation_state(phone)
                            
                            # Send success message to trainer
                            success_msg = (
                                f"🎉 *Client Added Successfully!*\n\n"
                                f"✅ {client_name} has been added to your client list!\n"
                                f"📱 Phone: {client_phone}\n\n"
                                f"They can now:\n"
                                f"• Book sessions with you\n"
                                f"• Track their progress\n"
                                f"• Receive workouts and guidance\n\n"
                                f"💡 *Next steps:* Send them a welcome message or start planning their first session!"
                            )
                            
                            whatsapp_service.send_message(phone, success_msg)
                            
                            # Send welcome message to the new client
                            welcome_msg = (
                                f"🌟 *Welcome to your fitness journey!*\n\n"
                                f"You've been added as a client! I'm Refiloe, your AI fitness assistant.\n\n"
                                f"I'm here to help you:\n"
                                f"• Book training sessions\n"
                                f"• Track your progress\n"
                                f"• Stay motivated\n\n"
                                f"Ready to get started? Just say 'Hi' anytime! 💪"
                            )
                            
                            whatsapp_service.send_message(client_phone, welcome_msg)
                            
                            log_info(f"Successfully added client {client_name} ({client_id}) for trainer {phone}")
                            return {'success': True, 'response': success_msg}
                        else:
                            error_msg = "❌ Sorry, there was an error adding the client. Please try again."
                            whatsapp_service.send_message(phone, error_msg)
                            self.clear_conversation_state(phone)
                            return {'success': False, 'response': error_msg}
                            
                    except Exception as e:
                        log_error(f"Error adding client: {str(e)}")
                        error_msg = "❌ Sorry, there was an error adding the client. Please try again."
                        whatsapp_service.send_message(phone, error_msg)
                        self.clear_conversation_state(phone)
                        return {'success': False, 'response': error_msg}
                
                elif response_lower in ['no', 'n', 'cancel', 'abort']:
                    # Cancel the client addition
                    cancel_msg = "❌ Client addition cancelled. No changes were made."
                    whatsapp_service.send_message(phone, cancel_msg)
                    self.clear_conversation_state(phone)
                    return {'success': True, 'response': cancel_msg}
                
                else:
                    # Invalid response, ask again
                    retry_msg = (
                        f"Please reply 'yes' to add {pending_client.get('name', 'the client')} "
                        f"or 'no' to cancel."
                    )
                    whatsapp_service.send_message(phone, retry_msg)
                    return {'success': True, 'response': retry_msg}
            
            # CHECK FOR REGISTRATION BUTTON CLICKS - ONLY FOR UNKNOWN USERS
            if sender_type == 'unknown':
                text_lower = text.strip().lower()
                
                # If we're waiting for a registration choice OR if they click a button any time
                if conv_state.get('state') == 'AWAITING_REGISTRATION_CHOICE' or any(trigger in text_lower for trigger in ["i'm a trainer", "find a trainer", "learn about me"]):
                    
                    # Check for trainer registration
                    if any(trigger in text_lower for trigger in ["i'm a trainer", "trainer", "💼"]):
                        try:
                            from services.whatsapp_flow_handler import WhatsAppFlowHandler
                            
                            # Initialize flow handler with automatic fallback
                            flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                            
                            # Handle trainer registration with flow + fallback
                            reg_result = flow_handler.handle_trainer_registration_request(phone)
                            
                            if reg_result.get('success'):
                                if reg_result.get('already_registered'):
                                    # User is already registered
                                    whatsapp_service.send_message(phone, reg_result['message'])
                                    return {'success': True, 'response': reg_result['message']}
                                
                                elif reg_result.get('method') == 'text_registration':
                                    # Text-based registration started (fallback)
                                    whatsapp_service.send_message(phone, reg_result['message'])
                                    
                                    # Update conversation state for text registration
                                    state_update = reg_result.get('conversation_state_update', {})
                                    if state_update:
                                        self.update_conversation_state(
                                            phone, 
                                            state_update.get('state', 'REGISTRATION'),
                                            state_update.get('context', {})
                                        )
                                    
                                    self.save_message(phone, reg_result['message'], 'bot', 'registration_start')
                                    log_info(f"Started text-based trainer registration for {phone}")
                                    return {'success': True, 'response': reg_result['message']}
                                
                                elif reg_result.get('method') == 'whatsapp_flow':
                                    # WhatsApp Flow sent successfully
                                    confirmation_msg = (
                                        "🎉 I've sent you a registration form! Please complete it to get started.\n\n"
                                        "If you don't see the form, I'll help you register step by step instead."
                                    )
                                    whatsapp_service.send_message(phone, confirmation_msg)
                                    
                                    # Don't update conversation state for flows - they handle their own completion
                                    self.save_message(phone, confirmation_msg, 'bot', 'flow_sent')
                                    log_info(f"Sent WhatsApp Flow for trainer registration to {phone}")
                                    return {'success': True, 'response': confirmation_msg}
                            
                            else:
                                # Registration failed
                                error_msg = reg_result.get('message', 'Registration system temporarily unavailable. Please try again later.')
                                whatsapp_service.send_message(phone, error_msg)
                                log_error(f"Trainer registration failed for {phone}: {reg_result.get('error')}")
                                return {'success': False, 'response': error_msg}
                            
                        except ImportError as e:
                            log_error(f"Import error in flow handler: {str(e)}")
                            error_msg = "Registration system temporarily unavailable. Please try again later."
                            whatsapp_service.send_message(phone, error_msg)
                            return {'success': False, 'response': error_msg}
                        except Exception as e:
                            log_error(f"Error in trainer registration flow: {str(e)}")
                            error_msg = "Sorry, I couldn't start the registration process. Please try again or type 'help' for assistance."
                            whatsapp_service.send_message(phone, error_msg)
                            return {'success': False, 'response': error_msg}
                    
                    # Check for client registration
                    elif any(trigger in text_lower for trigger in ["find a trainer", "client", "🏃"]):
                        try:
                            from services.whatsapp_flow_handler import WhatsAppFlowHandler
                            
                            # Initialize flow handler with automatic fallback
                            flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                            
                            # Handle client registration with flow + fallback
                            reg_result = flow_handler.handle_client_onboarding_request(phone)
                            
                            if reg_result.get('success'):
                                if reg_result.get('method') == 'whatsapp_flow':
                                    # WhatsApp Flow sent successfully
                                    confirmation_msg = (
                                        "🎉 I've sent you a registration form! Please complete it to get started.\n\n"
                                        "If you don't see the form, I'll help you register step by step instead."
                                    )
                                    whatsapp_service.send_message(phone, confirmation_msg)
                                    
                                    # Don't update conversation state for flows - they handle their own completion
                                    self.save_message(phone, confirmation_msg, 'bot', 'flow_sent')
                                    log_info(f"Sent WhatsApp Flow for client registration to {phone}")
                                    return {'success': True, 'response': confirmation_msg}
                                
                                elif reg_result.get('method') == 'text_fallback':
                                    # Text registration started successfully
                                    welcome_message = reg_result.get('message')
                                    whatsapp_service.send_message(phone, welcome_message)
                                    
                                    import uuid
                                    session_id = str(uuid.uuid4())
                                    
                                    self.update_conversation_state(phone, 'REGISTRATION', {
                                        'type': 'client',
                                        'step': 'name',
                                        'session_id': session_id,
                                        'current_step': 0
                                    })
                                    
                                    self.save_message(phone, welcome_message, 'bot', 'registration_start')
                                    log_info(f"Started text-based client registration for {phone}")
                                    return {'success': True, 'response': welcome_message}
                            else:
                                # Both flow and fallback failed
                                error_msg = reg_result.get('error', 'Registration failed')
                                whatsapp_service.send_message(phone, error_msg)
                                return {'success': False, 'response': error_msg}
                            
                        except Exception as e:
                            log_error(f"Error starting client registration: {str(e)}")
                            error_msg = "Sorry, I couldn't start the registration process. Please try again or type 'help' for assistance."
                            whatsapp_service.send_message(phone, error_msg)
                            return {'success': False, 'response': error_msg}
                    
                    # Check for "learn about me"
                    elif any(trigger in text_lower for trigger in ["learn about me", "learn", "📚"]):
                        info_message = (
                            "🌟 *Hi! I'm Refiloe, your AI fitness assistant!*\n\n"
                            "I was created to make fitness accessible and manageable for everyone in South Africa! "
                            "My name means 'we have been given' in Sesotho - because I'm here to give you the tools for success. 💪\n\n"
                            "*What I can do for trainers:*\n"
                            "📱 Manage your entire business via WhatsApp\n"
                            "👥 Track all your clients in one place\n"
                            "📅 Handle bookings and scheduling\n"
                            "💰 Process payments and track revenue\n"
                            "📊 Generate progress reports\n"
                            "🏋️ Create and send custom workouts\n\n"
                            "*What I can do for clients:*\n"
                            "🔍 Connect you with qualified trainers\n"
                            "📅 Book and manage your sessions\n"
                            "📈 Track your fitness progress\n"
                            "🎯 Set and achieve your goals\n"
                            "💪 Access personalized workouts\n"
                            "🏆 Join challenges and stay motivated\n\n"
                            "*Ready to start?* Tell me:\n"
                            "• Type 'trainer' if you're a fitness professional\n"
                            "• Type 'client' if you're looking for training\n\n"
                            "Let's transform your fitness journey together! 🚀"
                        )
                        
                        whatsapp_service.send_message(phone, info_message)
                        self.save_message(phone, info_message, 'bot', 'info')
                        self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
                        
                        return {'success': True, 'response': info_message}
            
            # Process with AI to understand intent
            intent = ai_handler.understand_message(
                text,
                sender_type,
                sender_data,
                history_text
            )
            
            # Generate smart response using the EXISTING method in AIIntentHandler
            response_text = ai_handler.generate_smart_response(
                intent,
                sender_type,
                sender_data
            )
            
            # Special handling for unknown users - Add welcome buttons after AI response
            if sender_type == 'unknown' and intent.get('primary_intent') in ['greeting', 'general_question', 'registration_inquiry']:
                import random
                
                # Transition phrases to connect AI response to buttons
                transitions = [
                    "I can help you achieve your fitness goals! 💪\n\nWhat brings you here today?",
                    "Let's get you started on your fitness journey! 🚀\n\nHow can I help you today?",
                    "I'm here to make fitness simple and effective! ✨\n\nWhat would you like to do?",
                    "Ready to transform your fitness experience? 💪\n\nTell me about yourself:"
                ]
                
                # Combine AI response with transition to buttons
                full_message = f"{response_text}\n\n{random.choice(transitions)}"
                
                # Create the 3 main option buttons
                buttons = [
                    {
                        'id': 'register_trainer',
                        'title': '💼 I\'m a Trainer'
                    },
                    {
                        'id': 'register_client', 
                        'title': '🏃 Find a Trainer'
                    },
                    {
                        'id': 'learn_about_me',
                        'title': '📚 Learn about me'
                    }
                ]
                
                # Send message with buttons
                whatsapp_service.send_button_message(phone, full_message, buttons)
                
                # Update conversation state to track we're waiting for registration choice
                self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
                
                # Save the full bot response with buttons
                self.save_message(phone, full_message, 'bot', 'registration_prompt')
                
                return {'success': True, 'response': full_message}
            
            # For registered users, just send the AI response normally
            whatsapp_service.send_message(phone, response_text)
            
            # Save bot response
            self.save_message(phone, response_text, 'bot', intent.get('primary_intent'))
            
            return {'success': True, 'response': response_text}
            
        except Exception as e:
            log_error(f"Error handling message: {str(e)}")
            # Fallback to a friendly error message
            return {
                'success': False,
                'response': "Sorry, I'm having a bit of trouble right now. Please try again in a moment! 😊"
            }
    
    def _handle_help_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /help command - show available commands and features"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            name = user_data.get('name', 'there') if user_data else 'there'
            
            if user_type == 'trainer':
                response = (
                    f"👋 Hi {name}! Here's what you can do:\n\n"
                    "🔧 *Profile Commands:*\n"
                    "• `/profile` - View your trainer profile\n"
                    "• `/edit_profile` - Update your profile info\n\n"
                    "👥 *Client Management:*\n"
                    "• `/clients` - View and manage your clients\n"
                    "• `/add_client` - Add a new client\n\n"
                    "💬 *General:*\n"
                    "• Just chat with me for AI assistance\n"
                    "• Ask about fitness, training, or business help\n\n"
                    "🔄 *Role Switching:*\n"
                    "• Use 'Switch Role' button if you're also a client\n\n"
                    "Need help with anything specific? Just ask! 😊"
                )
            elif user_type == 'client':
                trainer_name = user_data.get('trainer_name', 'your trainer') if user_data else 'your trainer'
                response = (
                    f"👋 Hi {name}! Here's what you can do:\n\n"
                    "🔧 *Profile Commands:*\n"
                    "• `/profile` - View your client profile\n"
                    "• `/edit_profile` - Update your profile info\n"
                    "• `/trainer` - View {trainer_name}'s info\n\n"
                    "�  *Find Trainers:*\n"
                    "• `/find_trainer` - Get help finding trainers\n"
                    "• `/request_trainer [email/phone]` - Request specific trainer\n"
                    "• `/add_trainer [email/phone]` - Add trainer directly\n"
                    "• `/invitations` - View trainer invitations\n\n"
                    "💬 *General:*\n"
                    "• Just chat with me for fitness guidance\n"
                    "• Ask about workouts, nutrition, or goals\n"
                    "• Say 'trainer john@email.com' to find trainers\n\n"
                    "🔄 *Role Switching:*\n"
                    "• Use 'Switch Role' button if you're also a trainer\n\n"
                    "Need help with your fitness journey? Just ask! 💪"
                )
            else:
                response = (
                    "👋 Welcome to Refiloe! Here's how to get started:\n\n"
                    "🚀 *Getting Started:*\n"
                    "• `/registration` - Register as a trainer or client\n"
                    "• Just say 'Hi' to start the registration process\n\n"
                    "💬 *General:*\n"
                    "• Chat with me for fitness and training advice\n"
                    "• Ask questions about health and wellness\n\n"
                    "Ready to transform your fitness journey? Let's go! 🏃‍♀️"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling help command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_profile_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /profile command - show user profile information"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if not user_data:
                response = "❌ No profile found. Please register first by saying 'Hi' or using `/registration`."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            if user_type == 'trainer':
                # Format trainer profile
                name = user_data.get('name', 'Unknown')
                email = user_data.get('email', 'Not provided')
                business_name = user_data.get('business_name', 'Not provided')
                specialization = user_data.get('specialization', 'Not provided')
                experience = user_data.get('experience_years', user_data.get('years_experience', 'Not provided'))
                city = user_data.get('city', user_data.get('location', 'Not provided'))
                pricing = user_data.get('pricing_per_session', 'Not provided')
                
                response = (
                    f"👤 *Your Trainer Profile*\n\n"
                    f"📝 *Basic Info:*\n"
                    f"• Name: {name}\n"
                    f"• Email: {email}\n"
                    f"• City: {city}\n"
                    f"• Business: {business_name}\n\n"
                    f"💼 *Professional Info:*\n"
                    f"• Specialization: {specialization}\n"
                    f"• Experience: {experience} years\n"
                    f"• Rate: R{pricing}/session\n\n"
                    f"📱 *Actions:*\n"
                    f"• Type `/edit_profile` to update your info\n"
                    f"• Type `/clients` to manage clients"
                )
            
            elif user_type == 'client':
                # Format client profile
                name = user_data.get('name', 'Unknown')
                email = user_data.get('email', 'Not provided')
                goals = user_data.get('fitness_goals', 'Not provided')
                trainer_name = user_data.get('trainer_name', 'Not assigned')
                
                response = (
                    f"👤 *Your Client Profile*\n\n"
                    f"📝 *Basic Info:*\n"
                    f"• Name: {name}\n"
                    f"• Email: {email}\n"
                    f"• Fitness Goals: {goals}\n"
                    f"• Trainer: {trainer_name}\n\n"
                    f"📱 *Actions:*\n"
                    f"• Type `/edit_profile` to update your info\n"
                    f"• Type `/trainer` to view trainer details"
                )
            
            # Enhance profile with habit information
            enhanced_response = self._enhance_profile_with_habits(phone, user_type, user_data, response)
            
            whatsapp_service.send_message(phone, enhanced_response)
            return {'success': True, 'response': enhanced_response}
            
        except Exception as e:
            log_error(f"Error handling profile command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_edit_profile_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /edit_profile command - start profile editing process using WhatsApp Flow"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if not user_data:
                response = "❌ No profile found. Please register first by saying 'Hi' or using `/registration`."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Try to send WhatsApp Flow for profile editing
            try:
                flow_result = self._send_profile_edit_flow(phone, user_type, user_data)
                
                if flow_result.get('success'):
                    return flow_result
                else:
                    # Fallback to instructions if flow fails
                    log_warning(f"Profile edit flow failed for {phone}: {flow_result.get('error')}")
                    
            except Exception as flow_error:
                log_error(f"Error sending profile edit flow: {str(flow_error)}")
            
            # Fallback: Provide instructions for manual editing
            name = user_data.get('name', 'there')
            
            if user_type == 'trainer':
                response = (
                    f"✏️ *Edit Your Trainer Profile*\n\n"
                    f"Hi {name}! I'd love to help you update your profile, but the editing flow isn't available right now.\n\n"
                    f"📧 *To update your profile:*\n"
                    f"• Email us at: support@refiloe.ai\n"
                    f"• Include your WhatsApp number: {phone}\n"
                    f"• Specify what you'd like to change\n\n"
                    f"🔄 *Alternative:*\n"
                    f"• Tell me what you'd like to update and I'll help you contact support\n\n"
                    f"💡 *Tip:* Type `/profile` to see your current info"
                )
            else:
                response = (
                    f"✏️ *Edit Your Client Profile*\n\n"
                    f"Hi {name}! I'd love to help you update your profile, but the editing flow isn't available right now.\n\n"
                    f"📧 *To update your profile:*\n"
                    f"• Email us at: support@refiloe.ai\n"
                    f"• Include your WhatsApp number: {phone}\n"
                    f"• Specify what you'd like to change\n\n"
                    f"🔄 *Alternative:*\n"
                    f"• Tell me what you'd like to update and I'll help you contact support\n\n"
                    f"💡 *Tip:* Type `/profile` to see your current info"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling edit profile command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_registration_command(self, phone: str, user_type: str) -> Dict:
        """Handle /registration command - start or restart registration"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type in ['trainer', 'client']:
                response = (
                    f"✅ You're already registered as a {user_type}!\n\n"
                    f"• Type `/profile` to view your info\n"
                    f"• Type `/help` to see available commands\n\n"
                    f"Need to register in a different role? Contact support."
                )
            else:
                response = (
                    "🚀 *Start Your Registration*\n\n"
                    "Choose how you'd like to register:\n\n"
                    "👨‍💼 *As a Trainer:*\n"
                    "• Say 'I want to be a trainer'\n"
                    "• Or just say 'trainer'\n\n"
                    "🏃‍♀️ *As a Client:*\n"
                    "• Say 'I want to find a trainer'\n"
                    "• Or just say 'client'\n\n"
                    "💬 *Quick Start:*\n"
                    "Just say 'Hi' and I'll guide you through the process!"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling registration command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_clients_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /clients command - show trainer's clients"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            trainer_id = user_data.get('id')
            if not trainer_id:
                response = "❌ Unable to find your trainer profile. Please contact support."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Get trainer's clients
            clients = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            if not clients.data:
                response = (
                    "👥 *Your Clients*\n\n"
                    "You don't have any active clients yet.\n\n"
                    "🚀 *Get Started:*\n"
                    "• Type `/add_client` to add your first client\n"
                    "• Share your WhatsApp number with potential clients\n"
                    "• They can message you to get started!\n\n"
                    "💡 *Tip:* Clients can find you by saying 'I need a trainer'"
                )
            else:
                client_list = []
                for i, client in enumerate(clients.data, 1):
                    name = client.get('name', 'Unknown')
                    sessions = client.get('sessions_remaining', 0)
                    client_list.append(f"{i}. {name} ({sessions} sessions left)")
                
                clients_text = '\n'.join(client_list)
                response = (
                    f"👥 *Your Clients ({len(clients.data)})*\n\n"
                    f"{clients_text}\n\n"
                    f"📱 *Actions:*\n"
                    f"• Type `/add_client` to add a new client\n"
                    f"• Message me about specific client needs"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling clients command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_add_client_command(self, phone: str, user_data: dict) -> Dict:
        """Enhanced /add_client command with WhatsApp Flow integration"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Check trainer subscription limits first
            trainer_id = user_data.get('id')
            if trainer_id:
                try:
                    from services.subscription_manager import SubscriptionManager
                    subscription_manager = SubscriptionManager(self.db)
                    
                    if not subscription_manager.can_add_client(trainer_id):
                        limits = subscription_manager.get_client_limits(trainer_id)
                        current_clients = limits.get('current_clients', 0)
                        max_clients = limits.get('max_clients', 'unknown')
                        
                        response = (
                            f"⚠️ *Client Limit Reached*\n\n"
                            f"You currently have {current_clients}/{max_clients} clients.\n\n"
                            f"To add more clients, please upgrade your subscription:\n"
                            f"• Visit your dashboard\n"
                            f"• Choose a higher plan\n"
                            f"• Start adding unlimited clients!\n\n"
                            f"💡 *Need help?* Contact support for assistance."
                        )
                        
                        whatsapp_service.send_message(phone, response)
                        return {'success': True, 'response': response, 'limit_reached': True}
                        
                except Exception as e:
                    log_warning(f"Could not check subscription limits: {str(e)}")
            
            # Try to send WhatsApp Flow for client addition
            try:
                from services.whatsapp_flow_handler import WhatsAppFlowHandler
                flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                
                # Send client addition flow
                flow_result = self._send_client_addition_flow(phone, flow_handler)
                
                if flow_result.get('success'):
                    return flow_result
                else:
                    # Flow failed, use text-based fallback
                    log_info(f"WhatsApp Flow failed for {phone}, using text fallback: {flow_result.get('error')}")
                    return self._start_text_client_addition(phone, whatsapp_service)
                    
            except Exception as e:
                log_warning(f"WhatsApp Flow not available for {phone}: {str(e)}")
                return self._start_text_client_addition(phone, whatsapp_service)
            
        except Exception as e:
            log_error(f"Error handling add client command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_client_addition_flow(self, phone: str, flow_handler) -> Dict:
        """Send WhatsApp Flow for client addition"""
        try:
            # Create flow message for client addition
            flow_message = self._create_client_addition_flow_message(phone)
            
            if not flow_message:
                return {
                    'success': False,
                    'error': 'Failed to create client addition flow message'
                }
            
            # Send via WhatsApp service
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            result = whatsapp_service.send_flow_message(flow_message)
            
            if result.get('success'):
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'message': '📋 I\'ve sent you a client addition form! Please fill it out to add your new client.',
                    'flow_token': flow_message['interactive']['action']['parameters']['flow_token']
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send flow: {result.get("error")}'
                }
                
        except Exception as e:
            log_error(f"Error sending client addition flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_client_addition_flow_message(self, phone: str) -> Optional[Dict]:
        """Create WhatsApp flow message for client addition"""
        try:
            import json
            import os
            from datetime import datetime
            
            # Load the client addition flow JSON
            project_root = os.path.dirname(os.path.dirname(__file__))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_add_client_flow.json')
            
            if not os.path.exists(flow_path):
                log_error(f"Client addition flow file not found: {flow_path}")
                return None
            
            with open(flow_path, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            
            # Generate flow token
            flow_token = f"add_client_{phone}_{int(datetime.now().timestamp())}"
            
            # Create flow message
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Add New Client"
                    },
                    "body": {
                        "text": "Let's add a new client to your training program! 👥"
                    },
                    "footer": {
                        "text": "Powered by Refiloe AI"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": "TRAINER_ADD_CLIENT_FLOW",  # This should match your Facebook Console flow ID
                            "flow_cta": "Add Client",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "WELCOME"
                            }
                        }
                    }
                }
            }
            
            return message
            
        except Exception as e:
            log_error(f"Error creating client addition flow message: {str(e)}")
            return None
    
    def _start_text_client_addition(self, phone: str, whatsapp_service) -> Dict:
        """Text-based client addition fallback"""
        try:
            # Set conversation state for text-based client addition
            self.update_conversation_state(phone, 'TEXT_CLIENT_ADDITION', {
                'step': 'name',
                'client_data': {}
            })
            
            response = (
                "➕ *Add New Client* (Text Mode)\n\n"
                "I'll help you add a client step by step.\n\n"
                "📝 *Step 1 of 4*\n\n"
                "What's your client's full name?"
            )
            
            whatsapp_service.send_message(phone, response)
            
            return {
                'success': True,
                'method': 'text_fallback',
                'message': response,
                'conversation_state_update': {
                    'state': 'TEXT_CLIENT_ADDITION',
                    'context': {
                        'step': 'name',
                        'client_data': {}
                    }
                }
            }
            
        except Exception as e:
            log_error(f"Error starting text client addition: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_trainer_info_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /trainer command - show client's trainer info"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get trainer info from client data
            trainer_info = user_data.get('trainers') if user_data else None
            
            if not trainer_info:
                response = (
                    "❌ No trainer assigned yet.\n\n"
                    "🔍 *Find a Trainer:*\n"
                    "• Say 'I need a trainer'\n"
                    "• Browse available trainers in your area\n\n"
                    "💬 *Have a specific trainer?*\n"
                    "Ask them for their WhatsApp number and message them directly!"
                )
            else:
                trainer_name = trainer_info.get('name', 'Unknown')
                business_name = trainer_info.get('business_name', 'Not provided')
                specialization = trainer_info.get('specialization', 'General Fitness')
                
                response = (
                    f"👨‍💼 *Your Trainer: {trainer_name}*\n\n"
                    f"🏢 Business: {business_name}\n"
                    f"🎯 Specialization: {specialization}\n\n"
                    f"📱 *Contact:*\n"
                    f"• Message them directly for sessions\n"
                    f"• Ask about scheduling and availability\n\n"
                    f"💪 *Need Help?*\n"
                    f"Just ask me about workouts, nutrition, or fitness goals!"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling trainer info command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_profile_edit_flow(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Send WhatsApp Flow for profile editing"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Determine which flow to use based on user type
            if user_type == 'trainer':
                flow_name = 'trainer_profile_edit_flow'
                flow_title = '✏️ Edit Trainer Profile'
                flow_description = 'Update your trainer profile information'
            elif user_type == 'client':
                flow_name = 'client_profile_edit_flow'
                flow_title = '✏️ Edit Client Profile'
                flow_description = 'Update your client profile information'
            else:
                return {'success': False, 'error': 'Invalid user type for profile editing'}
            
            # Generate flow token
            from datetime import datetime
            flow_token = f"profile_edit_{user_type}_{phone}_{int(datetime.now().timestamp())}"
            
            # Create flow message
            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": flow_title
                    },
                    "body": {
                        "text": f"{flow_description}. Only update the fields you want to change - leave others blank to keep current values."
                    },
                    "footer": {
                        "text": "Quick and easy profile updates"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": flow_name,
                            "flow_cta": "Edit Profile",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {}
                            }
                        }
                    }
                }
            }
            
            # Send the flow message
            result = whatsapp_service.send_flow_message(flow_message)
            
            if result.get('success'):
                # Store flow token for tracking
                self._store_profile_edit_token(phone, flow_token, user_type)
                
                log_info(f"Profile edit flow sent to {phone} ({user_type})")
                return {
                    'success': True,
                    'message': f'{flow_title} sent successfully',
                    'flow_token': flow_token
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send flow: {result.get("error")}',
                    'fallback_required': True
                }
                
        except Exception as e:
            log_error(f"Error sending profile edit flow: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_required': True
            }
    
    def _store_profile_edit_token(self, phone: str, flow_token: str, user_type: str):
        """Store profile edit flow token for tracking"""
        try:
            from datetime import datetime
            
            token_data = {
                'phone_number': phone,
                'flow_token': flow_token,
                'flow_type': f'{user_type}_profile_edit',
                'created_at': datetime.now().isoformat()
            }
            
            self.db.table('flow_tokens').insert(token_data).execute()
            log_info(f"Stored profile edit flow token for {phone}")
            
        except Exception as e:
            log_error(f"Error storing profile edit flow token: {str(e)}")
    
    def _handle_reset_command(self, phone: str) -> Dict:
        """Handle /reset_me command to completely reset user data from all 7 core tables"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Safety check - only allow for specific test numbers
            ALLOWED_RESET_NUMBERS = [
                '27731863036',  # Your test number from logs
                '27837896738',  # Add other test numbers as needed
                "8801902604456",
                "8801876078348",

            ]
            
            if phone not in ALLOWED_RESET_NUMBERS:
                response = "⚠️ Reset command is currently only available for test accounts.\n\nIf you need to reset your account, please contact support."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Track what happens
            debug_info = []
            deleted_count = 0
            
            # Delete from trainers
            try:
                result = self.db.table('trainers').delete().eq('whatsapp', phone).execute()
                if result.data:
                    deleted_count += len(result.data)
                    debug_info.append(f"✓ Deleted {len(result.data)} trainer record(s)")
                else:
                    debug_info.append("• No trainer records found")
            except Exception as e:
                debug_info.append(f"✗ Trainer delete error: {str(e)[:50]}")
            
            # Delete from clients
            try:
                result = self.db.table('clients').delete().eq('whatsapp', phone).execute()
                if result.data:
                    deleted_count += len(result.data)
                    debug_info.append(f"✓ Deleted {len(result.data)} client record(s)")
                else:
                    debug_info.append("• No client records found")
            except Exception as e:
                debug_info.append(f"✗ Client delete error: {str(e)[:50]}")
            
            # Delete conversation states
            try:
                result = self.db.table('conversation_states').delete().eq('phone_number', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted conversation state")
                else:
                    debug_info.append("• No conversation state found")
            except Exception as e:
                debug_info.append(f"✗ Conversation state error: {str(e)[:50]}")
            
            # Delete message history
            try:
                result = self.db.table('message_history').delete().eq('phone_number', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted {len(result.data)} messages")
                else:
                    debug_info.append("• No message history found")
            except Exception as e:
                debug_info.append(f"✗ Message history error: {str(e)[:50]}")
            
            # Delete registration sessions
            try:
                result = self.db.table('registration_sessions').delete().eq('phone', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted registration session")
                else:
                    debug_info.append("• No registration session found")
            except Exception as e:
                debug_info.append(f"✗ Registration session error: {str(e)[:50]}")
            
            # Delete registration state
            try:
                result = self.db.table('registration_state').delete().eq('phone', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted registration state")
                else:
                    debug_info.append("• No registration state found")
            except Exception as e:
                debug_info.append(f"✗ Registration state error: {str(e)[:50]}")
            
            # Delete registration analytics
            try:
                result = self.db.table('registration_analytics').delete().eq('phone', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted {len(result.data)} analytics record(s)")
                else:
                    debug_info.append("• No registration analytics found")
            except Exception as e:
                debug_info.append(f"✗ Registration analytics error: {str(e)[:50]}")
            
            # Delete flow tokens
            try:
                result = self.db.table('flow_tokens').delete().eq('phone_number', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted {len(result.data)} flow token(s)")
                else:
                    debug_info.append("• No flow tokens found")
            except Exception as e:
                debug_info.append(f"✗ Flow tokens error: {str(e)[:50]}")
            
            # Delete processed messages (legacy table)
            try:
                result = self.db.table('processed_messages').delete().eq('phone_number', phone).execute()
                if result.data:
                    debug_info.append(f"✓ Deleted {len(result.data)} processed messages")
                else:
                    debug_info.append("• No processed messages found")
            except Exception as e:
                debug_info.append(f"✗ Processed messages error: {str(e)[:50]}")
            
            log_info(f"Reset for {phone} - Results: {debug_info}")
            
            # Count successful deletions
            successful_deletions = len([item for item in debug_info if item.startswith("✓")])
            
            # Send detailed response
            response = (
                "🔧 *Complete Account Reset Results:*\n\n" +
                "\n".join(debug_info) +
                f"\n\n📊 *Summary:*\n"
                f"• Tables processed: 7 core tables\n"
                f"• Successful operations: {successful_deletions}\n"
                f"• Total records deleted: {deleted_count}\n\n"
                "✨ Your account has been completely reset!\n"
                "You can now say 'Hi' to start fresh! 🚀"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            error_msg = str(e)
            log_error(f"Error resetting user {phone}: {error_msg}")
            
            # Send detailed error
            response = (
                f"❌ Reset failed!\n\n"
                f"Error: {error_msg[:200]}\n\n"
                "This usually means:\n"
                "• Database connection issue\n"
                "• Missing tables\n"
                "• Permission problem\n\n"
                "Try again or check the logs."
            )
            
            try:
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                whatsapp_service.send_message(phone, response)
            except:
                pass
            
            return {'success': False, 'response': response}
    
    def _handle_test_command(self, phone: str, command: str) -> Dict:
        """Handle test commands for easier testing of different user states"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Safety check - only for test numbers
            ALLOWED_TEST_NUMBERS = [
                '27731863036',
                '27837896738',
                # Add your test numbers
            ]
            
            if phone not in ALLOWED_TEST_NUMBERS:
                return {'success': True, 'response': "Command not recognized."}
            
            if command == '/test_trainer':
                # Make user a trainer for testing
                self.db.table('clients').delete().eq('whatsapp', phone).execute()
                self.db.table('trainers').upsert({
                    'whatsapp': phone,
                    'name': 'Test Trainer',
                    'email': f'test_trainer_{phone}@test.com',
                    'status': 'active',
                    'business_name': 'Test Fitness',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                response = "✅ You're now registered as a trainer!\n\nYou can test trainer features like:\n• Adding clients\n• Creating workouts\n• Managing bookings"
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_client':
                # Make user a client for testing
                self.db.table('trainers').delete().eq('whatsapp', phone).execute()
                self.db.table('clients').upsert({
                    'whatsapp': phone,
                    'name': 'Test Client',
                    'email': f'test_client_{phone}@test.com',
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                response = "✅ You're now registered as a client!\n\nYou can test client features like:\n• Viewing workouts\n• Booking sessions\n• Tracking habits"
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_new':
                # Make user unknown (same as reset but quicker to type)
                self.db.table('trainers').delete().eq('whatsapp', phone).execute()
                self.db.table('clients').delete().eq('whatsapp', phone).execute()
                self.db.table('conversation_states').delete().eq('phone_number', phone).execute()
                
                response = "✅ You're now a new user!\n\nSay 'Hi' to see the welcome message with registration options."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_help':
                response = (
                    "🧪 *Test Commands Available:*\n\n"
                    "*/reset_me* - Complete account reset\n"
                    "*/test_trainer* - Become a trainer\n"
                    "*/test_client* - Become a client\n"
                    "*/test_new* - Become unknown user\n"
                    "*/test_help* - Show this help\n\n"
                    "_These commands are only available for test accounts._"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            return {'success': True, 'response': "Unknown test command. Try /test_help"}
            
        except Exception as e:
            log_error(f"Error handling test command: {str(e)}")
            return {'success': False, 'response': "Test command failed."}
    
    def _handle_registration_choice(self, phone: str, message: str, whatsapp_service) -> Dict:
        """Handle button clicks for registration choice"""
        try:
            # Clear the awaiting state
            self.update_conversation_state(phone, 'IDLE')
            
            # Handle "I'm a Trainer" button
            if 'register_trainer' in message.lower() or "i'm a trainer" in message.lower() or "trainer" in message.lower():
                from services.registration.trainer_registration import TrainerRegistration
                reg = TrainerRegistration(self.db)
                reg_result = reg.start_registration(phone)
                if reg_result.get('buttons'):
                    whatsapp_service.send_button_message(
                        phone,
                        reg_result['message'],
                        reg_result['buttons']
                    )
                else:
                    whatsapp_service.send_message(phone, reg_result['message'])
                
                self.update_conversation_state(phone, 'REGISTRATION', {'type': 'trainer'})
                return {'success': True}
            
            # Handle "Find a Trainer" button
            elif 'register_client' in message.lower() or "find a trainer" in message.lower() or "find trainer" in message.lower():
                from services.registration.client_registration import ClientRegistration
                reg = ClientRegistration(self.db)
                reg_result = reg.start_registration(phone)
                if reg_result.get('buttons'):
                    whatsapp_service.send_button_message(
                        phone,
                        reg_result['message'],
                        reg_result['buttons']
                    )
                else:
                    whatsapp_service.send_message(phone, reg_result['message'])
                
                self.update_conversation_state(phone, 'REGISTRATION', {'type': 'client'})
                return {'success': True}
            
            # Handle "Learn about me" button
            elif 'learn_about_me' in message.lower() or "learn about me" in message.lower():
                info_message = (
                    "🌟 *Hi! I'm Refiloe, your AI fitness assistant!*\n\n"
                    "I was created to make fitness accessible and manageable for everyone passionate about health and wellness "
                    "My name means 'we have been given' in Sesotho - and I'm here to give you the tools for success. 💪\n\n"
                    "✨ *What I Can Do?*\n\n"
                    "📱 *For Personal Trainers:*\n"
                    "• Manage all your clients in one place\n"
                    "• Schedule & track sessions\n"
                    "• Share workouts instantly\n"
                    "• Handle payments seamlessly\n"
                    "• Track client progress\n\n"
                    "🏃 *For Fitness Enthusiasts:*\n"
                    "• Match you with qualified trainers\n"
                    "• Book sessions easily\n"
                    "• Track your fitness journey\n"
                    "• Get personalized workouts\n"
                    "• Monitor your progress\n\n"
                    "I'm available 24/7 right here on WhatsApp! No apps to download, "
                    "no complicated setups - just message me anytime! 🚀\n\n"
                    "Ready to start? Let me know if you're a trainer or looking for one!"
                )
                
                # After learning about Refiloe, offer the registration options
                buttons = [
                    {
                        'id': 'register_trainer',
                        'title': '💼 I\'m a Trainer'
                    },
                    {
                        'id': 'register_client',
                        'title': '🏃 Find a Trainer'
                    }
                ]
                
                whatsapp_service.send_button_message(phone, info_message, buttons)
                
                # Keep state as awaiting choice for the follow-up buttons
                self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
                
                return {'success': True}
            
            # If message doesn't match any button, treat as new message
            else:
                # Reset state and process as normal message
                self.update_conversation_state(phone, 'IDLE')
                return self.handle_message(phone, message)
                
        except Exception as e:
            log_error(f"Error handling registration choice: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, something went wrong. Please try again or just tell me if you're a trainer or looking for one!"
            }
    
    def _handle_text_client_addition_step(self, phone: str, message: str, context: Dict) -> Dict:
        """Handle text-based client addition steps"""
        try:
            step = context.get('step', 'name')
            client_data = context.get('client_data', {})
            
            if step == 'name':
                # Validate name
                name = message.strip()
                if len(name) < 2:
                    return {
                        'success': False,
                        'message': "Please enter a valid name (at least 2 characters)."
                    }
                
                client_data['name'] = name
                
                return {
                    'success': True,
                    'message': f"Great! Now what's {name}'s phone number?\n\n📱 *Step 2 of 4*\n\nEnter their South African number (e.g., 0821234567)",
                    'context': {
                        'step': 'phone',
                        'client_data': client_data
                    }
                }
            
            elif step == 'phone':
                # Validate phone number
                from utils.validators import Validators
                validator = Validators()
                
                is_valid, formatted_phone, error = validator.validate_phone_number(message.strip())
                
                if not is_valid:
                    return {
                        'success': False,
                        'message': f"❌ {error}\n\nPlease enter a valid South African number (e.g., 0821234567 or +27821234567)"
                    }
                
                # Check for duplicate
                user_context = self.get_user_context(phone)
                trainer_id = user_context.get('user_data', {}).get('id')
                
                if trainer_id:
                    existing_client = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', formatted_phone).execute()
                    if existing_client.data:
                        return {
                            'success': False,
                            'message': f"❌ You already have a client with phone number {formatted_phone}.\n\nPlease enter a different number."
                        }
                
                client_data['phone'] = formatted_phone
                
                return {
                    'success': True,
                    'message': f"Perfect! What's {client_data['name']}'s email address?\n\n📧 *Step 3 of 4*\n\nEnter their email or type 'skip' if they don't have one.",
                    'context': {
                        'step': 'email',
                        'client_data': client_data
                    }
                }
            
            elif step == 'email':
                # Validate email (optional)
                email_input = message.strip().lower()
                
                if email_input == 'skip':
                    client_data['email'] = None
                else:
                    from utils.validators import Validators
                    validator = Validators()
                    
                    is_valid, error = validator.validate_email(email_input)
                    
                    if not is_valid:
                        return {
                            'success': False,
                            'message': f"❌ {error}\n\nPlease enter a valid email or type 'skip'"
                        }
                    
                    client_data['email'] = email_input
                
                return {
                    'success': True,
                    'message': f"Excellent! How would you like to add {client_data['name']}?\n\n🤔 *Step 4 of 4*\n\n1️⃣ Send them an invitation (they accept via WhatsApp)\n2️⃣ Add them directly (they can start messaging you)\n\nReply '1' or '2'",
                    'context': {
                        'step': 'method',
                        'client_data': client_data
                    }
                }
            
            elif step == 'method':
                # Process addition method
                method_input = message.strip()
                
                if method_input == '1':
                    # Send invitation
                    return self._process_text_client_invitation(phone, client_data)
                elif method_input == '2':
                    # Add directly
                    return self._process_text_client_direct_add(phone, client_data)
                else:
                    return {
                        'success': False,
                        'message': "Please reply '1' to send an invitation or '2' to add them directly."
                    }
            
            else:
                return {
                    'success': False,
                    'message': "❌ Something went wrong. Let's start over. Type /add_client to begin."
                }
                
        except Exception as e:
            log_error(f"Error handling text client addition step: {str(e)}")
            return {
                'success': False,
                'message': "❌ Sorry, there was an error. Please try again."
            }
    
    def _process_text_client_invitation(self, trainer_phone: str, client_data: Dict) -> Dict:
        """Process client invitation from text flow"""
        try:
            # Get trainer info
            user_context = self.get_user_context(trainer_phone)
            trainer_id = user_context.get('user_data', {}).get('id')
            
            if not trainer_id:
                return {
                    'success': False,
                    'message': "❌ Could not find your trainer profile. Please try again."
                }
            
            # Use the WhatsApp flow handler to create and send invitation
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            from services.whatsapp_flow_handler import WhatsAppFlowHandler
            
            flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
            result = flow_handler._create_and_send_invitation(trainer_id, client_data)
            
            if result.get('success'):
                return {
                    'success': True,
                    'completed': True,
                    'message': result['message']
                }
            else:
                return {
                    'success': False,
                    'message': f"❌ Failed to send invitation: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            log_error(f"Error processing text client invitation: {str(e)}")
            return {
                'success': False,
                'message': "❌ Sorry, there was an error sending the invitation. Please try again."
            }
    
    def _process_text_client_direct_add(self, trainer_phone: str, client_data: Dict) -> Dict:
        """Process direct client addition from text flow"""
        try:
            # Get trainer info
            user_context = self.get_user_context(trainer_phone)
            trainer_id = user_context.get('user_data', {}).get('id')
            
            if not trainer_id:
                return {
                    'success': False,
                    'message': "❌ Could not find your trainer profile. Please try again."
                }
            
            # Use the WhatsApp flow handler to add client directly
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            from services.whatsapp_flow_handler import WhatsAppFlowHandler
            
            flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
            result = flow_handler._add_client_directly(trainer_id, client_data)
            
            if result.get('success'):
                return {
                    'success': True,
                    'completed': True,
                    'message': result['message']
                }
            else:
                return {
                    'success': False,
                    'message': f"❌ Failed to add client: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            log_error(f"Error processing text client direct add: {str(e)}")
            return {
                'success': False,
                'message': "❌ Sorry, there was an error adding the client. Please try again."
            }
    
    def _handle_invitation_response(self, client_phone: str, message: str) -> Dict:
        """Handle client's response to trainer invitation"""
        try:
            message_lower = message.strip().lower()
            
            # Check if this looks like an invitation acceptance
            acceptance_keywords = ['accept', 'yes', 'join', 'start', 'ok', 'sure', 'let\'s go', 'i accept']
            decline_keywords = ['decline', 'no', 'not interested', 'cancel', 'reject']
            
            is_acceptance = any(keyword in message_lower for keyword in acceptance_keywords)
            is_decline = any(keyword in message_lower for keyword in decline_keywords)
            
            if not (is_acceptance or is_decline):
                return {'handled': False}
            
            # Look for pending invitation for this phone number
            invitation_result = self.db.table('client_invitations').select('*').eq('client_phone', client_phone).eq('status', 'pending').execute()
            
            if not invitation_result.data:
                # No pending invitation found
                if is_acceptance:
                    return {
                        'handled': True,
                        'message': "I don't see any pending trainer invitations for your number. If you're looking for a trainer, say 'find a trainer' and I'll help you get started! 🏃"
                    }
                else:
                    return {'handled': False}
            
            # Get the most recent invitation
            invitation = invitation_result.data[0]
            invitation_id = invitation['id']
            trainer_id = invitation['trainer_id']
            
            # Check if invitation has expired
            from datetime import datetime
            import pytz
            
            sa_tz = pytz.timezone('Africa/Johannesburg')
            now = datetime.now(sa_tz)
            expires_at = datetime.fromisoformat(invitation['expires_at'].replace('Z', '+00:00'))
            
            if now > expires_at:
                # Invitation expired
                self.db.table('client_invitations').update({'status': 'expired'}).eq('id', invitation_id).execute()
                
                return {
                    'handled': True,
                    'message': "⏰ Sorry, this invitation has expired. Please contact your trainer for a new invitation, or say 'find a trainer' to search for trainers."
                }
            
            if is_acceptance:
                # Accept the invitation
                return self._process_invitation_acceptance(invitation, client_phone)
            else:
                # Decline the invitation
                return self._process_invitation_decline(invitation, client_phone)
                
        except Exception as e:
            log_error(f"Error handling invitation response: {str(e)}")
            return {'handled': False}
    
    def _process_invitation_acceptance(self, invitation: Dict, client_phone: str) -> Dict:
        """Process client acceptance of trainer invitation"""
        try:
            invitation_id = invitation['id']
            trainer_id = invitation['trainer_id']
            client_name = invitation['client_name']
            
            # Update invitation status
            self.db.table('client_invitations').update({
                'status': 'accepted',
                'updated_at': datetime.now().isoformat()
            }).eq('id', invitation_id).execute()
            
            # Get trainer info
            trainer_result = self.db.table('trainers').select('name, business_name').eq('id', trainer_id).execute()
            trainer_name = 'Your trainer'
            business_name = 'the training program'
            
            if trainer_result.data:
                trainer_info = trainer_result.data[0]
                trainer_name = trainer_info.get('name', 'Your trainer')
                business_name = trainer_info.get('business_name') or f"{trainer_name}'s training program"
            
            # Start client registration process
            from services.registration.client_registration import ClientRegistrationHandler
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            client_reg_handler = ClientRegistrationHandler(self.db, whatsapp_service)
            
            # Set conversation state for registration
            self.update_conversation_state(client_phone, 'REGISTRATION', {
                'type': 'client',
                'current_step': 0,
                'trainer_id': trainer_id,
                'invitation_accepted': True
            })
            
            # Start registration with trainer context
            welcome_message = client_reg_handler.start_registration(client_phone, trainer_id)
            
            # Notify trainer of acceptance
            try:
                trainer_phone = self.db.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
                if trainer_phone.data:
                    trainer_notification = (
                        f"🎉 *Great News!*\n\n"
                        f"{client_name} accepted your invitation and is now registering!\n\n"
                        f"I'm guiding them through the setup process. You'll be notified when they complete registration."
                    )
                    
                    from app import app
                    whatsapp_service = app.config['services']['whatsapp']
                    whatsapp_service.send_message(trainer_phone.data[0]['whatsapp'], trainer_notification)
                    
            except Exception as e:
                log_warning(f"Could not notify trainer of invitation acceptance: {str(e)}")
            
            return {
                'handled': True,
                'message': welcome_message
            }
            
        except Exception as e:
            log_error(f"Error processing invitation acceptance: {str(e)}")
            return {
                'handled': True,
                'message': "❌ Sorry, there was an error processing your acceptance. Please contact your trainer directly."
            }
    
    def _process_invitation_decline(self, invitation: Dict, client_phone: str) -> Dict:
        """Process client decline of trainer invitation"""
        try:
            invitation_id = invitation['id']
            trainer_id = invitation['trainer_id']
            client_name = invitation['client_name']
            
            # Update invitation status
            self.db.table('client_invitations').update({
                'status': 'declined',
                'updated_at': datetime.now().isoformat()
            }).eq('id', invitation_id).execute()
            
            # Notify trainer of decline
            try:
                trainer_phone = self.db.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
                if trainer_phone.data:
                    trainer_notification = (
                        f"📋 *Invitation Update*\n\n"
                        f"{client_name} declined your training invitation.\n\n"
                        f"No worries! You can always send new invitations to other potential clients."
                    )
                    
                    from app import app
                    whatsapp_service = app.config['services']['whatsapp']
                    whatsapp_service.send_message(trainer_phone.data[0]['whatsapp'], trainer_notification)
                    
            except Exception as e:
                log_warning(f"Could not notify trainer of invitation decline: {str(e)}")
            
            return {
                'handled': True,
                'message': (
                    "✅ I've noted that you're not interested in this training program.\n\n"
                    "If you change your mind or want to find a different trainer, just say 'find a trainer' anytime! 🏃"
                )
            }
            
        except Exception as e:
            log_error(f"Error processing invitation decline: {str(e)}")
            return {
                'handled': True,
                'message': "✅ I've noted your response. If you want to find a trainer later, just say 'find a trainer'!"
            }
    
    def _handle_trainer_request_by_email(self, client_phone: str, message: str) -> Dict:
        """Handle client request for specific trainer by email"""
        try:
            message_lower = message.strip().lower()
            
            # Check if this looks like a trainer email request
            email_patterns = [
                r'trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'i want trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'find trainer\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
            
            import re
            trainer_email = None
            
            for pattern in email_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    trainer_email = match.group(1)
                    break
            
            if not trainer_email:
                return {'handled': False}
            
            # Look up trainer by email
            trainer_result = self.db.table('trainers').select('*').eq('email', trainer_email).execute()
            
            if not trainer_result.data:
                return {
                    'handled': True,
                    'message': f"I couldn't find a trainer with email {trainer_email}. Please check the email address or ask them to register as a trainer first."
                }
            
            trainer = trainer_result.data[0]
            trainer_id = trainer['id']
            trainer_name = trainer['name']
            business_name = trainer.get('business_name', f"{trainer_name}'s Training")
            
            # Check if client already has this trainer
            existing_client = self.db.table('clients').select('*').eq('whatsapp', client_phone).eq('trainer_id', trainer_id).execute()
            
            if existing_client.data:
                return {
                    'handled': True,
                    'message': f"You're already connected with {trainer_name}! You can start booking sessions and tracking your progress."
                }
            
            # Check for existing pending request
            existing_request = self.db.table('clients').select('*').eq('whatsapp', client_phone).eq('trainer_id', trainer_id).eq('connection_status', 'pending').execute()
            
            if existing_request.data:
                return {
                    'handled': True,
                    'message': f"You already have a pending request with {trainer_name}. Please wait for them to approve your request."
                }
            
            # Create client request (pending approval)
            client_data = {
                'name': 'Pending Client',  # Will be updated during registration
                'whatsapp': client_phone,
                'trainer_id': trainer_id,
                'connection_status': 'pending',
                'requested_by': 'client',
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            result = self.db.table('clients').insert(client_data).execute()
            
            if result.data:
                # Notify trainer of new client request
                trainer_phone = trainer['whatsapp']
                trainer_notification = (
                    f"👋 *New Client Request!*\n\n"
                    f"Someone wants to train with you!\n"
                    f"📱 Phone: {client_phone}\n\n"
                    f"💡 *Actions:*\n"
                    f"• `/pending_requests` - View all requests\n"
                    f"• `/approve_client {client_phone}` - Approve this client\n"
                    f"• `/decline_client {client_phone}` - Decline this request\n\n"
                    f"What would you like to do?"
                )
                
                try:
                    from app import app
                    whatsapp_service = app.config['services']['whatsapp']
                    whatsapp_service.send_message(trainer_phone, trainer_notification)
                except Exception as e:
                    log_warning(f"Could not notify trainer of client request: {str(e)}")
                
                return {
                    'handled': True,
                    'message': (
                        f"✅ *Request Sent!*\n\n"
                        f"I've sent your training request to {trainer_name} from {business_name}.\n\n"
                        f"They'll review your request and get back to you soon. You'll receive a notification once they respond!\n\n"
                        f"💡 *What happens next:*\n"
                        f"• {trainer_name} will review your request\n"
                        f"• If approved, you'll start registration\n"
                        f"• If declined, you can search for other trainers\n\n"
                        f"Thanks for your patience! 🙏"
                    )
                }
            else:
                return {
                    'handled': True,
                    'message': "❌ Sorry, there was an error sending your trainer request. Please try again."
                }
                
        except Exception as e:
            log_error(f"Error handling trainer request by email: {str(e)}")
            return {'handled': False}
    
    def _handle_pending_requests_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /pending_requests command - show pending client requests"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            trainer_id = user_data.get('id')
            
            # Get pending client requests
            pending_requests = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('connection_status', 'pending').execute()
            
            if not pending_requests.data:
                response = (
                    "📋 *No Pending Requests*\n\n"
                    "You don't have any pending client requests at the moment.\n\n"
                    "💡 *To get more clients:*\n"
                    "• Use `/add_client` to invite clients directly\n"
                    "• Share your email with potential clients\n"
                    "• They can request you by saying 'trainer [your email]'\n\n"
                    "Keep growing your business! 💪"
                )
            else:
                request_count = len(pending_requests.data)
                
                response = f"👋 *Pending Client Requests ({request_count})*\n\n"
                
                for i, request in enumerate(pending_requests.data, 1):
                    client_phone = request['whatsapp']
                    requested_date = request['created_at'][:10]
                    
                    response += f"{i}. 📱 {client_phone}\n"
                    response += f"   📅 Requested: {requested_date}\n"
                    response += f"   ✅ `/approve_client {client_phone}`\n"
                    response += f"   ❌ `/decline_client {client_phone}`\n\n"
                
                response += "💡 *Quick Actions:*\n"
                response += "• Reply with the approve/decline commands above\n"
                response += "• Or just say 'approve [phone]' or 'decline [phone]'"
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling pending requests command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_approve_client_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /approve_client [identifier] command"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            trainer_id = user_data.get('id')
            
            # Extract client identifier from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "❓ *Usage:* `/approve_client [phone_number]`\n\n"
                    "Example: `/approve_client +27821234567`\n\n"
                    "💡 Use `/pending_requests` to see all pending requests."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            client_identifier = parts[1].strip()
            
            # Find pending client request
            pending_client = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', client_identifier).eq('connection_status', 'pending').execute()
            
            if not pending_client.data:
                response = (
                    f"❌ *No Pending Request Found*\n\n"
                    f"I couldn't find a pending request from {client_identifier}.\n\n"
                    f"💡 Use `/pending_requests` to see all current requests."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            client_record = pending_client.data[0]
            client_phone = client_record['whatsapp']
            
            # Approve the client - update status and start registration
            self.db.table('clients').update({
                'connection_status': 'approved',
                'approved_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).eq('id', client_record['id']).execute()
            
            # Start client registration process
            from services.registration.client_registration import ClientRegistrationHandler
            
            client_reg_handler = ClientRegistrationHandler(self.db, whatsapp_service)
            
            # Set conversation state for registration
            self.update_conversation_state(client_phone, 'REGISTRATION', {
                'type': 'client',
                'current_step': 0,
                'trainer_id': trainer_id,
                'approved_by_trainer': True
            })
            
            # Start registration with trainer context
            welcome_message = client_reg_handler.start_registration(client_phone, trainer_id)
            
            # Send welcome message to client
            whatsapp_service.send_message(client_phone, welcome_message)
            
            # Confirm to trainer
            trainer_name = user_data.get('name', 'You')
            response = (
                f"✅ *Client Approved!*\n\n"
                f"Great! I've approved the client request from {client_phone}.\n\n"
                f"🚀 *What happens next:*\n"
                f"• They're now starting registration\n"
                f"• I'll guide them through the setup process\n"
                f"• You'll be notified when they complete registration\n\n"
                f"Welcome to your growing training business! 💪"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling approve client command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_decline_client_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /decline_client [identifier] command"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            trainer_id = user_data.get('id')
            
            # Extract client identifier from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "❓ *Usage:* `/decline_client [phone_number]`\n\n"
                    "Example: `/decline_client +27821234567`\n\n"
                    "💡 Use `/pending_requests` to see all pending requests."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            client_identifier = parts[1].strip()
            
            # Find pending client request
            pending_client = self.db.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', client_identifier).eq('connection_status', 'pending').execute()
            
            if not pending_client.data:
                response = (
                    f"❌ *No Pending Request Found*\n\n"
                    f"I couldn't find a pending request from {client_identifier}.\n\n"
                    f"💡 Use `/pending_requests` to see all current requests."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            client_record = pending_client.data[0]
            client_phone = client_record['whatsapp']
            
            # Decline the client - update status
            self.db.table('clients').update({
                'connection_status': 'declined',
                'updated_at': datetime.now().isoformat()
            }).eq('id', client_record['id']).execute()
            
            # Notify client of decline
            decline_message = (
                f"📋 *Training Request Update*\n\n"
                f"Thank you for your interest in training! Unfortunately, your trainer request wasn't approved at this time.\n\n"
                f"💡 *Don't worry!* There are many great trainers available:\n"
                f"• Say 'find a trainer' to search for other trainers\n"
                f"• Ask friends for trainer recommendations\n"
                f"• Try reaching out to other trainers directly\n\n"
                f"Keep pursuing your fitness goals! 💪"
            )
            
            whatsapp_service.send_message(client_phone, decline_message)
            
            # Confirm to trainer
            response = (
                f"✅ *Client Request Declined*\n\n"
                f"I've declined the request from {client_phone} and notified them politely.\n\n"
                f"💡 *Remember:* You can always change your mind later if you have capacity for more clients.\n\n"
                f"Focus on providing great service to your current clients! 🌟"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling decline client command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_client_invitations_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /invitations command - show client's trainer invitations"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get pending invitations for this client
            pending_invitations = self.db.table('client_invitations').select('*').eq('client_phone', phone).eq('status', 'pending').execute()
            
            if not pending_invitations.data:
                response = (
                    "📧 *No Pending Invitations*\n\n"
                    "You don't have any pending trainer invitations at the moment.\n\n"
                    "💡 *To connect with trainers:*\n"
                    "• Use `/find_trainer` to search for trainers\n"
                    "• Ask friends for trainer recommendations\n"
                    "• If you know a trainer's email, say 'trainer [email]'\n\n"
                    "Ready to start your fitness journey? 💪"
                )
            else:
                invitation_count = len(pending_invitations.data)
                
                response = f"📧 *Trainer Invitations ({invitation_count})*\n\n"
                
                for i, invitation in enumerate(pending_invitations.data, 1):
                    trainer_id = invitation['trainer_id']
                    invitation_token = invitation['invitation_token']
                    invited_date = invitation['created_at'][:10]
                    expires_date = invitation['expires_at'][:10]
                    custom_message = invitation.get('message', '')
                    
                    # Get trainer info
                    trainer_result = self.db.table('trainers').select('name, business_name, email').eq('id', trainer_id).execute()
                    
                    if trainer_result.data:
                        trainer_info = trainer_result.data[0]
                        trainer_name = trainer_info.get('name', 'Unknown Trainer')
                        business_name = trainer_info.get('business_name', f"{trainer_name}'s Training")
                        trainer_email = trainer_info.get('email', '')
                        
                        response += f"{i}. 🏋️ **{business_name}**\n"
                        response += f"   👨‍💼 Trainer: {trainer_name}\n"
                        response += f"   📧 Email: {trainer_email}\n"
                        response += f"   📅 Invited: {invited_date}\n"
                        response += f"   ⏰ Expires: {expires_date}\n"
                        
                        if custom_message:
                            response += f"   💬 Message: \"{custom_message}\"\n"
                        
                        response += f"   ✅ `/accept_invitation {invitation_token[:8]}`\n"
                        response += f"   ❌ `/decline_invitation {invitation_token[:8]}`\n\n"
                
                response += "💡 *Quick Actions:*\n"
                response += "• Reply with the accept/decline commands above\n"
                response += "• Or just say 'accept [trainer name]' or 'decline [trainer name]'"
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling client invitations command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_accept_invitation_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /accept_invitation [token] command"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Extract invitation token from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "❓ *Usage:* `/accept_invitation [token]`\n\n"
                    "Example: `/accept_invitation abc12345`\n\n"
                    "💡 Use `/invitations` to see all your invitations with tokens."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            token_partial = parts[1].strip()
            
            # Find invitation by partial token (first 8 characters)
            invitations = self.db.table('client_invitations').select('*').eq('client_phone', phone).eq('status', 'pending').execute()
            
            matching_invitation = None
            for invitation in invitations.data:
                if invitation['invitation_token'].startswith(token_partial):
                    matching_invitation = invitation
                    break
            
            if not matching_invitation:
                response = (
                    f"❌ *Invitation Not Found*\n\n"
                    f"I couldn't find a pending invitation with token '{token_partial}'.\n\n"
                    f"💡 Use `/invitations` to see all your current invitations."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Check if invitation has expired
            from datetime import datetime
            import pytz
            
            sa_tz = pytz.timezone('Africa/Johannesburg')
            now = datetime.now(sa_tz)
            expires_at = datetime.fromisoformat(matching_invitation['expires_at'].replace('Z', '+00:00'))
            
            if now > expires_at:
                # Mark as expired
                self.db.table('client_invitations').update({'status': 'expired'}).eq('id', matching_invitation['id']).execute()
                
                response = (
                    "⏰ *Invitation Expired*\n\n"
                    "Sorry, this invitation has expired. Please contact the trainer for a new invitation.\n\n"
                    "💡 Use `/find_trainer` to search for other trainers."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Accept the invitation - use existing invitation response handler
            invitation_response = self._process_invitation_acceptance(matching_invitation, phone)
            
            whatsapp_service.send_message(phone, invitation_response['message'])
            return {'success': True, 'response': invitation_response['message']}
            
        except Exception as e:
            log_error(f"Error handling accept invitation command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_decline_invitation_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /decline_invitation [token] command"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Extract invitation token from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "❓ *Usage:* `/decline_invitation [token]`\n\n"
                    "Example: `/decline_invitation abc12345`\n\n"
                    "💡 Use `/invitations` to see all your invitations with tokens."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            token_partial = parts[1].strip()
            
            # Find invitation by partial token
            invitations = self.db.table('client_invitations').select('*').eq('client_phone', phone).eq('status', 'pending').execute()
            
            matching_invitation = None
            for invitation in invitations.data:
                if invitation['invitation_token'].startswith(token_partial):
                    matching_invitation = invitation
                    break
            
            if not matching_invitation:
                response = (
                    f"❌ *Invitation Not Found*\n\n"
                    f"I couldn't find a pending invitation with token '{token_partial}'.\n\n"
                    f"💡 Use `/invitations` to see all your current invitations."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Decline the invitation - use existing invitation response handler
            invitation_response = self._process_invitation_decline(matching_invitation, phone)
            
            whatsapp_service.send_message(phone, invitation_response['message'])
            return {'success': True, 'response': invitation_response['message']}
            
        except Exception as e:
            log_error(f"Error handling decline invitation command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_find_trainer_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /find_trainer command - help client find trainers"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            response = (
                "🔍 *Find Your Perfect Trainer*\n\n"
                "Here are several ways to connect with a trainer:\n\n"
                "📧 **By Email (Recommended):**\n"
                "• If you know a trainer's email, say: 'trainer [email]'\n"
                "• Example: 'trainer john@fitlife.com'\n\n"
                "👥 **Get Recommendations:**\n"
                "• Ask friends and family for trainer recommendations\n"
                "• Check local gyms and fitness centers\n"
                "• Look for trainers on social media\n\n"
                "📱 **Direct Contact:**\n"
                "• Ask trainers to send you an invitation\n"
                "• They can use '/add_client' to invite you\n\n"
                "💡 **Tips for Choosing:**\n"
                "• Look for certified trainers\n"
                "• Check their specializations\n"
                "• Read reviews and testimonials\n"
                "• Consider location and availability\n\n"
                "Ready to start your fitness journey? Just say 'trainer [email]' when you find someone! 💪"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling find trainer command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_request_trainer_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /request_trainer [email/phone] command - request specific trainer"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Extract trainer contact info from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "📧 **Request Trainer Command**\n\n"
                    "Usage: `/request_trainer [email or phone]`\n\n"
                    "Examples:\n"
                    "• `/request_trainer john@fitlife.com`\n"
                    "• `/request_trainer 0821234567`\n\n"
                    "This will send a request to the trainer for approval."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            trainer_contact = parts[1].strip()
            
            # Use AI intent handler to process the request
            ai_handler = app.config['services'].get('ai_intent_handler')
            if ai_handler:
                # Create intent data for the request
                intent_data = {
                    'primary_intent': 'request_trainer',
                    'extracted_data': {
                        'original_message': f"trainer {trainer_contact}"
                    }
                }
                
                # Check if it's email or phone and add to extracted data
                import re
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', trainer_contact):
                    intent_data['extracted_data']['email'] = trainer_contact
                elif re.match(r'^(?:0|27|\+27)?[678]\d{8}$', trainer_contact):
                    # Normalize phone number
                    clean_phone = re.sub(r'^(?:27|\+27)', '0', trainer_contact)
                    if not clean_phone.startswith('0'):
                        clean_phone = '0' + clean_phone
                    intent_data['extracted_data']['phone_number'] = clean_phone
                
                result = ai_handler._handle_request_trainer(phone, intent_data, 'client', user_data)
                whatsapp_service.send_message(phone, result)
                return {'success': True, 'response': result}
            else:
                # Fallback to existing trainer request handler
                result = self._handle_trainer_request_by_email(phone, f"trainer {trainer_contact}")
                if result.get('handled'):
                    whatsapp_service.send_message(phone, result['message'])
                    return {'success': True, 'response': result['message']}
                else:
                    response = f"I couldn't process your trainer request for {trainer_contact}. Please check the contact details and try again."
                    whatsapp_service.send_message(phone, response)
                    return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling request trainer command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_add_trainer_command(self, phone: str, command: str, user_data: dict) -> Dict:
        """Handle /add_trainer [email/phone] command - directly add trainer"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Extract trainer contact info from command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                response = (
                    "🚀 **Add Trainer Command**\n\n"
                    "Usage: `/add_trainer [email or phone]`\n\n"
                    "Examples:\n"
                    "• `/add_trainer sarah@gym.com`\n"
                    "• `/add_trainer 0829876543`\n\n"
                    "This will try to add you directly to the trainer's program.\n"
                    "Note: Only works if the trainer allows auto-approval."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            trainer_contact = parts[1].strip()
            
            # Use AI intent handler to process the direct addition
            ai_handler = app.config['services'].get('ai_intent_handler')
            if ai_handler:
                # Create intent data for the direct addition
                intent_data = {
                    'primary_intent': 'add_trainer_direct',
                    'extracted_data': {
                        'original_message': f"add me to trainer {trainer_contact}"
                    }
                }
                
                # Check if it's email or phone and add to extracted data
                import re
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', trainer_contact):
                    intent_data['extracted_data']['email'] = trainer_contact
                elif re.match(r'^(?:0|27|\+27)?[678]\d{8}$', trainer_contact):
                    # Normalize phone number
                    clean_phone = re.sub(r'^(?:27|\+27)', '0', trainer_contact)
                    if not clean_phone.startswith('0'):
                        clean_phone = '0' + clean_phone
                    intent_data['extracted_data']['phone_number'] = clean_phone
                
                result = ai_handler._handle_add_trainer_direct(phone, intent_data, 'client', user_data)
                whatsapp_service.send_message(phone, result)
                return {'success': True, 'response': result}
            else:
                # Fallback - try request instead
                response = (
                    f"Direct trainer addition is not available right now.\n\n"
                    f"Try using `/request_trainer {trainer_contact}` to send a request instead."
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling add trainer command: {str(e)}")
            return {'success': False, 'error': str(e)}
    # ==================== HABIT TRACKING COMMAND HANDLERS ====================
    
    def _handle_habits_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /habits command - show habit overview and options"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type == 'trainer':
                return self._show_trainer_habit_dashboard(phone, user_data, whatsapp_service)
            elif user_type == 'client':
                return self._show_client_habit_dashboard(phone, user_data, whatsapp_service)
            else:
                return self._show_habit_registration_prompt(phone, whatsapp_service)
                
        except Exception as e:
            log_error(f"Error handling habits command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _show_trainer_habit_dashboard(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Show trainer's client habit management dashboard"""
        try:
            # Get trainer's clients
            clients_result = self.db.table('clients').select('id, name, whatsapp').eq(
                'trainer_id', user_data['id']
            ).eq('status', 'active').execute()
            
            if not clients_result.data:
                response = (
                    "📊 *Client Habit Management*\n\n"
                    "You don't have any active clients yet.\n\n"
                    "Add clients first using `/add_client` to start tracking their habits!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Get habit tracking stats for clients
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            response = "📊 *Client Habit Management*\n\n"
            
            for client in clients_result.data[:5]:  # Limit to 5 clients for readability
                client_habits = habits_service.get_client_habits(client['id'], days=7)
                
                if client_habits['success'] and client_habits['days_tracked'] > 0:
                    # Calculate streaks for this client
                    streaks = []
                    for habit_type in habits_service.habit_types:
                        streak = habits_service.calculate_streak(client['id'], habit_type)
                        if streak > 0:
                            streaks.append(f"{habit_type.replace('_', ' ').title()}: {streak}d")
                    
                    streak_text = ", ".join(streaks[:3]) if streaks else "No active streaks"
                    response += f"👤 *{client['name']}*\n🔥 {streak_text}\n\n"
                else:
                    response += f"👤 *{client['name']}*\n📝 No habits logged yet\n\n"
            
            response += (
                "*Quick Actions:*\n"
                "• `/setup_habits` - Setup habits for a client\n"
                "• Type client name to view detailed progress\n"
                "• `/habit_goals` - Manage client goals"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error showing trainer habit dashboard: {str(e)}")
            response = "❌ Error loading habit dashboard. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _show_client_habit_dashboard(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Show client's personal habit tracking dashboard"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Get client's habit data for the last 7 days
            habits_data = habits_service.get_client_habits(user_data['id'], days=7)
            
            if not habits_data['success'] or habits_data['days_tracked'] == 0:
                # Start habit onboarding for new users
                return self._start_habit_onboarding(phone, user_type, user_data)
            
            # Generate progress report
            response = self._format_habit_progress_report(user_data['id'], habits_service)
            
            response += (
                "\n*Quick Actions:*\n"
                "• `/log_habit` - Log today's habits\n"
                "• `/habit_streak` - Check all your streaks\n"
                "• `/habit_goals` - Manage your goals"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error showing client habit dashboard: {str(e)}")
            response = "❌ Error loading your habit progress. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _show_habit_registration_prompt(self, phone: str, whatsapp_service) -> Dict:
        """Show habit tracking registration prompt for unknown users"""
        response = (
            "🎯 *Habit Tracking Available!*\n\n"
            "Track your daily habits and build lasting healthy routines!\n\n"
            "To access habit tracking, please register first:\n\n"
            "• Type `/registration` to get started\n"
            "• Choose 'Client' to track your personal habits\n"
            "• Choose 'Trainer' to help clients with their habits\n\n"
            "Ready to build better habits? Let's get you registered! 🚀"
        )
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
    
    def _handle_log_habit_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /log_habit command - quick habit logging"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type != 'client':
                response = (
                    "📝 *Habit Logging*\n\n"
                    "Habit logging is available for clients only.\n\n"
                    "If you're a trainer, use `/habits` to manage client habits.\n"
                    "If you want to track personal habits, register as a client too!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Try WhatsApp Flow first, fallback to conversation state
            try:
                from services.whatsapp_flow_handler import WhatsAppFlowHandler
                flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                
                # Send WhatsApp Flow
                flow_result = flow_handler.send_client_habit_logging_flow(phone, user_data)
                
                if flow_result.get('success'):
                    log_info(f"Sent client habit logging flow to {phone}")
                    return {
                        'success': True,
                        'method': 'whatsapp_flow',
                        'response': 'Habit logging flow sent! Please complete the interactive form.'
                    }
                else:
                    log_warning(f"WhatsApp Flow failed for habit logging: {flow_result.get('error')}")
                    # Continue to fallback below
                    
            except Exception as flow_error:
                log_warning(f"WhatsApp Flow handler error: {str(flow_error)}")
                # Continue to fallback below
            
            # FALLBACK: Use conversation state method
            log_info(f"Using conversation state fallback for habit logging: {phone}")
            return self._start_habit_logging_flow(phone, user_data, whatsapp_service)
            
        except Exception as e:
            log_error(f"Error handling log habit command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _start_habit_logging_flow(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Start habit logging flow for client"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Check what habits they've logged today
            today = datetime.now().date().isoformat()
            today_habits = habits_service.get_client_habits(user_data['id'], days=1)
            
            logged_today = []
            if today_habits['success'] and today in today_habits['data']:
                logged_today = list(today_habits['data'][today].keys())
            
            # Show quick logging options
            response = "📝 *Log Today's Habits*\n\n"
            
            if logged_today:
                response += "*Already logged today:*\n"
                for habit in logged_today:
                    habit_name = habit.replace('_', ' ').title()
                    value = today_habits['data'][today][habit]
                    response += f"✅ {habit_name}: {value}\n"
                response += "\n"
            
            response += (
                "*Quick logging examples:*\n"
                "• 'drank 2 liters water'\n"
                "• 'slept 8 hours'\n"
                "• 'walked 10000 steps'\n"
                "• 'workout completed'\n"
                "• 'weight 75kg'\n\n"
                "Just tell me what you did today! 💪"
            )
            
            # Set conversation state for habit logging
            self.update_conversation_state(phone, 'HABIT_LOGGING', {
                'client_id': user_data['id'],
                'date': today
            })
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error starting habit logging flow: {str(e)}")
            response = "❌ Error starting habit logging. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _handle_habit_streak_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /habit_streak command - show current streaks"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type != 'client':
                response = (
                    "🔥 *Habit Streaks*\n\n"
                    "Streak tracking is available for clients only.\n\n"
                    "If you're a trainer, use `/habits` to view client streaks.\n"
                    "If you want personal streaks, register as a client too!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            return self._show_habit_streaks(phone, user_data, whatsapp_service)
            
        except Exception as e:
            log_error(f"Error handling habit streak command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _show_habit_streaks(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Display current habit streaks with motivational messages"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Calculate streaks for all habit types
            streaks = {}
            for habit_type in habits_service.habit_types:
                streak = habits_service.calculate_streak(user_data['id'], habit_type)
                if streak > 0:
                    streaks[habit_type] = streak
            
            if not streaks:
                response = (
                    "🔥 *Your Habit Streaks*\n\n"
                    "No active streaks yet, but that's okay! Every expert was once a beginner.\n\n"
                    "Start building your first streak:\n"
                    "• `/log_habit` - Log today's habits\n"
                    "• Even 1 day is a great start! 💪\n\n"
                    "Remember: Consistency beats perfection! 🎯"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            response = "🔥 *Your Current Streaks*\n\n"
            
            # Sort streaks by length (longest first)
            sorted_streaks = sorted(streaks.items(), key=lambda x: x[1], reverse=True)
            
            for habit_type, streak in sorted_streaks:
                habit_name = habit_type.replace('_', ' ').title()
                fire_emoji = '🔥' * min(streak // 3, 5)  # More fire for longer streaks
                
                if streak >= 21:
                    status = "🌟 AMAZING!"
                elif streak >= 14:
                    status = "💪 STRONG!"
                elif streak >= 7:
                    status = "🚀 BUILDING!"
                else:
                    status = "✨ STARTING!"
                
                response += f"• {habit_name}: {streak} days {fire_emoji} {status}\n"
            
            # Add motivational message based on total streaks
            total_streak_days = sum(streaks.values())
            
            response += "\n"
            if total_streak_days > 50:
                response += "🌟 *Incredible consistency! You're building amazing habits!*"
            elif total_streak_days > 20:
                response += "💪 *Great progress! Keep up the momentum!*"
            elif total_streak_days > 10:
                response += "🚀 *Good start! Consistency is key to success!*"
            else:
                response += "✨ *Every day counts! You're on the right track!*"
            
            response += (
                "\n\n*Keep it going:*\n"
                "• `/log_habit` - Log today's habits\n"
                "• Don't break the chain! 🔗"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error showing habit streaks: {str(e)}")
            response = "❌ Error loading your streaks. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _handle_habit_goals_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /habit_goals command - manage habit goals"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type == 'trainer':
                response = (
                    "🎯 *Client Habit Goals*\n\n"
                    "Goal management for clients is coming soon!\n\n"
                    "For now, use `/habits` to view client progress.\n"
                    "You can help clients set goals through conversation."
                )
            elif user_type == 'client':
                response = (
                    "🎯 *Your Habit Goals*\n\n"
                    "Goal setting is coming soon!\n\n"
                    "For now, focus on building consistency:\n"
                    "• `/log_habit` - Log daily habits\n"
                    "• `/habit_streak` - Track your progress\n\n"
                    "Remember: Small daily actions lead to big results! 💪"
                )
            else:
                response = (
                    "🎯 *Habit Goals*\n\n"
                    "Goal setting is available for registered users.\n\n"
                    "Type `/registration` to get started!"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling habit goals command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_setup_habits_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /setup_habits command - trainer sets up client habits"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Try WhatsApp Flow first, fallback to conversation state
            try:
                from services.whatsapp_flow_handler import WhatsAppFlowHandler
                flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                
                # Send WhatsApp Flow
                flow_result = flow_handler.send_trainer_habit_setup_flow(phone, user_data)
                
                if flow_result.get('success'):
                    log_info(f"Sent trainer habit setup flow to {phone}")
                    return {
                        'success': True,
                        'method': 'whatsapp_flow',
                        'response': 'Habit setup flow sent! Please complete the interactive form.'
                    }
                else:
                    log_warning(f"WhatsApp Flow failed for habit setup: {flow_result.get('error')}")
                    # Continue to fallback below
                    
            except Exception as flow_error:
                log_warning(f"WhatsApp Flow handler error: {str(flow_error)}")
                # Continue to fallback below
            
            # FALLBACK: Use conversation state method
            log_info(f"Using conversation state fallback for habit setup: {phone}")
            
            # Get trainer's clients
            clients_result = self.db.table('clients').select('id, name, whatsapp').eq(
                'trainer_id', user_data['id']
            ).eq('status', 'active').execute()
            
            if not clients_result.data:
                response = (
                    "👥 *Setup Client Habits*\n\n"
                    "You don't have any active clients yet.\n\n"
                    "Add clients first using `/add_client` to start setting up their habits!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            response = (
                "👥 *Setup Client Habits*\n\n"
                "Choose a client to setup habits for:\n\n"
            )
            
            for i, client in enumerate(clients_result.data[:10], 1):  # Limit to 10 clients
                response += f"{i}. {client['name']}\n"
            
            response += (
                "\nReply with the client's name or number to continue.\n\n"
                "Example: 'Sarah' or '1'"
            )
            
            # Set conversation state for habit setup
            self.update_conversation_state(phone, 'HABIT_SETUP', {
                'trainer_id': user_data['id'],
                'clients': clients_result.data,
                'step': 'select_client'
            })
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'method': 'conversation_state', 'response': response}
            
        except Exception as e:
            log_error(f"Error handling setup habits command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _format_habit_progress_report(self, client_id: str, habits_service) -> str:
        """Create rich text progress report with visual elements"""
        try:
            # Get habit data for the last 7 days
            habits_data = habits_service.get_client_habits(client_id, days=7)
            
            if not habits_data['success']:
                return "📊 No habit data available yet. Start logging to see your progress!"
            
            report = "📊 *Your Habit Progress*\n\n"
            
            # Calculate current streaks
            streaks = {}
            for habit_type in habits_service.habit_types:
                streak = habits_service.calculate_streak(client_id, habit_type)
                if streak > 0:
                    streaks[habit_type] = streak
            
            if streaks:
                report += "*🔥 Current Streaks:*\n"
                for habit, streak in sorted(streaks.items(), key=lambda x: x[1], reverse=True):
                    habit_name = habit.replace('_', ' ').title()
                    fire_emoji = '🔥' * min(streak // 3, 5)  # More fire for longer streaks
                    report += f"• {habit_name}: {streak} days {fire_emoji}\n"
                report += "\n"
            
            # Weekly completion chart
            report += "*📅 This Week:*\n"
            
            # Create simple text-based chart for key habits
            key_habits = [
                ('water_intake', '💧 Water'),
                ('workout_completed', '💪 Workout'),
                ('sleep_hours', '😴 Sleep'),
                ('steps', '🚶 Steps')
            ]
            
            for habit_type, habit_display in key_habits:
                if habit_type in [h for h in habits_service.habit_types]:
                    completion_line = f"{habit_display}: "
                    
                    # Check each day of the week (last 7 days)
                    for i in range(7):
                        date = (datetime.now() - timedelta(days=6-i)).date().isoformat()
                        
                        # Check if habit was logged for this date
                        completed = False
                        if date in habits_data['data'] and habit_type in habits_data['data'][date]:
                            completed = True
                        
                        completion_line += "✅" if completed else "⭕"
                    
                    report += completion_line + "\n"
            
            # Add motivational message
            total_streaks = sum(streaks.values())
            if total_streaks > 20:
                report += "\n🌟 *Amazing consistency! You're building incredible habits!*"
            elif total_streaks > 10:
                report += "\n💪 *Great progress! Keep up the momentum!*"
            elif total_streaks > 0:
                report += "\n🚀 *Good start! Consistency is key to success!*"
            else:
                report += "\n🎯 *Ready to start building healthy habits? You've got this!*"
            
            return report
            
        except Exception as e:
            log_error(f"Error formatting habit progress report: {str(e)}")
            return "📊 Error loading progress report. Please try again."    
   
 # ==================== HABIT CONVERSATION FLOW HANDLERS ====================
    
    def _handle_habit_logging_step(self, phone: str, text: str, context: dict) -> Dict:
        """Handle habit logging conversation step"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            client_id = context.get('client_id')
            if not client_id:
                return {
                    'success': False,
                    'message': '❌ Session expired. Please use `/log_habit` to start again.',
                    'completed': True
                }
            
            # Check if user wants to finish
            if text.lower().strip() in ['done', 'finish', 'complete', 'exit', 'stop']:
                return {
                    'success': True,
                    'message': '✅ *Habit logging completed!* Great job staying consistent with your habits! 💪',
                    'completed': True
                }
            
            # Get client's allowed habits first
            client_habits_data = habits_service.get_client_habits(client_id, days=30)
            allowed_habits = set()
            
            if client_habits_data['success'] and client_habits_data['data']:
                for date_data in client_habits_data['data'].values():
                    allowed_habits.update(date_data.keys())
            
            if not allowed_habits:
                return {
                    'success': False,
                    'message': (
                        '❌ *No habits setup yet!*\n\n'
                        'You need to setup habit tracking first. Ask your trainer to use `/setup_habits` '
                        'to configure your habits.'
                    ),
                    'completed': True
                }
            
            # Parse habit data from natural language
            parsed_habits = habits_service.parse_habit_from_text(text)
            
            if not parsed_habits:
                # Show available habits to help user
                habit_examples = []
                for habit in list(allowed_habits)[:4]:  # Show up to 4 examples
                    if habit == 'water_intake':
                        habit_examples.append("'drank 2 liters water'")
                    elif habit == 'sleep_hours':
                        habit_examples.append("'slept 8 hours'")
                    elif habit == 'steps':
                        habit_examples.append("'walked 10000 steps'")
                    elif habit == 'workout_completed':
                        habit_examples.append("'workout completed'")
                    elif habit == 'weight':
                        habit_examples.append("'weight 75kg'")
                
                return {
                    'success': True,
                    'message': (
                        f"I didn't detect any habits in your message. Try these examples:\n\n"
                        f"{chr(10).join(['• ' + ex for ex in habit_examples])}\n\n"
                        f"Or type 'done' when finished logging."
                    ),
                    'completed': False,
                    'context': context
                }
            
            # Validate and log the detected habits
            logged_habits = []
            invalid_habits = []
            streaks = {}
            
            for habit_data in parsed_habits:
                habit_type = habit_data.get('type')
                value = habit_data.get('value')
                
                if habit_type and value:
                    # Check if this habit is allowed for this client
                    if habit_type in allowed_habits:
                        result = habits_service.log_habit(client_id, habit_type, value)
                        if result.get('success'):
                            logged_habits.append(habit_type)
                            streaks[habit_type] = result.get('streak', 0)
                    else:
                        invalid_habits.append(habit_type)
            
            # Handle results
            if invalid_habits and not logged_habits:
                return {
                    'success': True,
                    'message': (
                        f"❌ The habits you mentioned ({', '.join(invalid_habits)}) are not setup for you.\n\n"
                        f"You can only log these habits: {', '.join([h.replace('_', ' ').title() for h in allowed_habits])}\n\n"
                        f"Ask your trainer to setup additional habits if needed."
                    ),
                    'completed': False,
                    'context': context
                }
            elif not logged_habits:
                return {
                    'success': True,
                    'message': (
                        "❌ Couldn't log any habits from your message. Please try again with specific values for your setup habits:\n\n"
                        f"Available habits: {', '.join([h.replace('_', ' ').title() for h in allowed_habits])}"
                    ),
                    'completed': False,
                    'context': context
                }
            
            # Generate success message
            message = f"✅ *Logged {len(logged_habits)} habit(s)!*\n\n"
            
            for habit_type in logged_habits:
                habit_name = habit_type.replace('_', ' ').title()
                streak = streaks.get(habit_type, 0)
                fire_emoji = '🔥' * min(streak // 3, 5)
                
                if streak > 0:
                    message += f"• {habit_name}: {streak} day streak {fire_emoji}\n"
                else:
                    message += f"• {habit_name}: Logged ✅\n"
            
            message += (
                "\n💪 *Great job!* Keep logging more habits or type 'done' when finished.\n\n"
                "Examples: 'workout completed', 'mood: great', 'calories 2000'"
            )
            
            return {
                'success': True,
                'message': message,
                'completed': False,
                'context': context
            }
            
        except Exception as e:
            log_error(f"Error handling habit logging step: {str(e)}")
            return {
                'success': False,
                'message': '❌ Error logging habits. Please try again.',
                'completed': True
            }
    
    def _handle_habit_setup_step(self, phone: str, text: str, context: dict) -> Dict:
        """Handle habit setup conversation step"""
        try:
            step = context.get('step', 'select_client')
            trainer_id = context.get('trainer_id')
            clients = context.get('clients', [])
            
            if step == 'select_client':
                # User is selecting a client
                text_lower = text.strip().lower()
                
                # Try to match by name or number
                selected_client = None
                
                # Try matching by number first
                if text_lower.isdigit():
                    client_index = int(text_lower) - 1
                    if 0 <= client_index < len(clients):
                        selected_client = clients[client_index]
                
                # Try matching by name
                if not selected_client:
                    for client in clients:
                        if text_lower in client['name'].lower():
                            selected_client = client
                            break
                
                if not selected_client:
                    # No match found
                    response = (
                        "❌ Client not found. Please choose from your client list:\n\n"
                    )
                    
                    for i, client in enumerate(clients[:10], 1):
                        response += f"{i}. {client['name']}\n"
                    
                    response += "\nReply with the client's name or number."
                    
                    return {
                        'success': True,
                        'message': response,
                        'completed': False,
                        'context': context
                    }
                
                # Client selected, move to habit selection
                response = (
                    f"👤 *Setting up habits for {selected_client['name']}*\n\n"
                    f"Choose habits to track (reply with numbers, e.g., '1,3,5'):\n\n"
                    f"1. 💧 Water Intake - Daily water consumption\n"
                    f"2. 😴 Sleep Hours - Hours of sleep per night\n"
                    f"3. 🚶 Daily Steps - Step count per day\n"
                    f"4. 💪 Workout Completion - Daily workout completion\n"
                    f"5. ⚖️ Weight Tracking - Body weight monitoring\n"
                    f"6. 🍽️ Meal Logging - Number of meals logged\n"
                    f"7. 🔥 Calorie Tracking - Daily calorie intake\n"
                    f"8. 😊 Mood Tracking - Daily mood and energy\n\n"
                    f"Example: '1,2,4' for water, sleep, and workouts"
                )
                
                new_context = context.copy()
                new_context['step'] = 'select_habits'
                new_context['selected_client'] = selected_client
                
                return {
                    'success': True,
                    'message': response,
                    'completed': False,
                    'context': new_context
                }
            
            elif step == 'select_habits':
                # User is selecting habits
                selected_client = context.get('selected_client')
                
                # Parse habit selection
                habit_types = [
                    'water_intake', 'sleep_hours', 'steps', 'workout_completed',
                    'weight', 'meals_logged', 'calories', 'mood'
                ]
                
                habit_names = [
                    '💧 Water Intake', '😴 Sleep Hours', '🚶 Daily Steps', '💪 Workout Completion',
                    '⚖️ Weight Tracking', '🍽️ Meal Logging', '🔥 Calorie Tracking', '😊 Mood Tracking'
                ]
                
                # Parse numbers from input
                import re
                numbers = re.findall(r'\d+', text)
                
                if not numbers:
                    return {
                        'success': True,
                        'message': (
                            "❌ Please select habits by number (e.g., '1,3,5'):\n\n"
                            "1. 💧 Water  2. 😴 Sleep  3. 🚶 Steps  4. 💪 Workout\n"
                            "5. ⚖️ Weight  6. 🍽️ Meals  7. 🔥 Calories  8. 😊 Mood"
                        ),
                        'completed': False,
                        'context': context
                    }
                
                selected_habits = []
                selected_names = []
                
                for num_str in numbers:
                    num = int(num_str)
                    if 1 <= num <= 8:
                        selected_habits.append(habit_types[num - 1])
                        selected_names.append(habit_names[num - 1])
                
                if not selected_habits:
                    return {
                        'success': True,
                        'message': "❌ Please select valid habit numbers (1-8).",
                        'completed': False,
                        'context': context
                    }
                
                # Initialize habits for the client
                from services.habits import HabitTrackingService
                habits_service = HabitTrackingService(self.db)
                
                success_count = 0
                for habit_type in selected_habits:
                    # Create initial habit entry
                    result = habits_service.log_habit(
                        selected_client['id'],
                        habit_type,
                        'initialized',
                        datetime.now().date().isoformat()
                    )
                    if result.get('success'):
                        success_count += 1
                
                # Send completion message
                message = (
                    f"🎉 *Habit Tracking Setup Complete!*\n\n"
                    f"✅ Client: {selected_client['name']}\n"
                    f"📊 Habits activated: {len(selected_habits)}\n\n"
                    f"*Selected habits:*\n"
                )
                
                for name in selected_names:
                    message += f"• {name}\n"
                
                message += (
                    f"\n💡 Your client can now:\n"
                    f"• Use `/log_habit` to log daily habits\n"
                    f"• Use `/habit_streak` to check streaks\n"
                    f"• Simply tell me what they did (e.g., 'drank 2L water')\n\n"
                    f"You can track their progress with `/habits`!"
                )
                
                return {
                    'success': True,
                    'message': message,
                    'completed': True
                }
            
            else:
                return {
                    'success': False,
                    'message': '❌ Invalid setup step. Please start over with `/setup_habits`.',
                    'completed': True
                }
                
        except Exception as e:
            log_error(f"Error handling habit setup step: {str(e)}")
            return {
                'success': False,
                'message': '❌ Error setting up habits. Please try again.',
                'completed': True
            }
    
    def _start_habit_onboarding(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Start guided habit tracking onboarding for new users"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type == 'client':
                # Generate personalized recommendations
                recommendations = self._generate_habit_recommendations(user_data, user_type)
                
                # Create personalized message based on fitness goals
                goals = user_data.get('fitness_goals', '').lower()
                
                if 'weight loss' in goals or 'lose weight' in goals:
                    goal_message = "Since you're focused on weight loss, I recommend starting with habits that boost metabolism and track nutrition:"
                elif 'muscle' in goals or 'strength' in goals:
                    goal_message = "Since you're building muscle and strength, I recommend habits that support recovery and performance:"
                elif 'endurance' in goals or 'cardio' in goals:
                    goal_message = "Since you're focused on endurance and cardio, I recommend habits that support performance and recovery:"
                else:
                    goal_message = "Based on your profile, I recommend starting with these foundational healthy habits:"
                
                # Client onboarding - personal habit setup with recommendations
                message = (
                    f"🎯 *Welcome to Habit Tracking!*\n\n"
                    f"Building healthy habits is key to reaching your fitness goals! "
                    f"{goal_message}\n\n"
                )
                
                # Add recommended habits
                habit_display_names = {
                    'water_intake': '💧 Water intake - Stay hydrated and boost metabolism',
                    'sleep_hours': '😴 Sleep hours - Essential for recovery and performance',
                    'steps': '🚶 Daily steps - Increase daily activity and burn calories',
                    'workout_completed': '💪 Workout completion - Build strength and consistency',
                    'weight': '⚖️ Weight tracking - Monitor your progress',
                    'meals_logged': '🍽️ Meal logging - Track nutrition and eating patterns'
                }
                
                for habit in recommendations:
                    if habit in habit_display_names:
                        message += f"{habit_display_names[habit]}\n"
                
                message += "\nWould you like to start tracking these recommended habits?"
                
                # Set up for habit onboarding flow
                self.update_conversation_state(phone, 'HABIT_ONBOARDING', {
                    'user_type': 'client',
                    'user_id': user_data['id'],
                    'step': 'confirm_start'
                })
                
            elif user_type == 'trainer':
                # Trainer onboarding - client habit management
                message = (
                    "📊 *Client Habit Tracking*\n\n"
                    "Help your clients build lasting healthy habits! "
                    "You can track their progress with:\n\n"
                    "💧 Hydration goals - Keep them hydrated\n"
                    "😴 Sleep quality - Ensure proper recovery\n"
                    "🏃 Activity levels - Monitor daily movement\n"
                    "💪 Workout consistency - Track training\n"
                    "📈 Progress metrics - Measure success\n\n"
                    "Ready to setup habit tracking for your clients?"
                )
                
                # Set up for trainer habit onboarding
                self.update_conversation_state(phone, 'HABIT_ONBOARDING', {
                    'user_type': 'trainer',
                    'user_id': user_data['id'],
                    'step': 'confirm_start'
                })
            
            else:
                message = (
                    "🎯 *Habit Tracking Available!*\n\n"
                    "Track your daily habits and build lasting healthy routines!\n\n"
                    "To access habit tracking, please register first:\n"
                    "• Type `/registration` to get started\n"
                    "• Choose your role (Client or Trainer)\n\n"
                    "Ready to build better habits? Let's get you registered! 🚀"
                )
            
            whatsapp_service.send_message(phone, message)
            return {'success': True, 'response': message}
            
        except Exception as e:
            log_error(f"Error starting habit onboarding: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _generate_habit_recommendations(self, user_data: dict, user_type: str) -> List[str]:
        """Generate personalized habit recommendations based on user goals"""
        try:
            recommendations = []
            
            if user_type == 'client':
                # Based on fitness goals
                goals = user_data.get('fitness_goals', '').lower()
                
                if any(goal in goals for goal in ['weight loss', 'lose weight', 'fat loss']):
                    recommendations.extend([
                        'water_intake',    # Hydration helps metabolism
                        'steps',           # Daily activity for calorie burn
                        'sleep_hours',     # Recovery for weight loss
                        'meals_logged'     # Nutrition tracking
                    ])
                elif any(goal in goals for goal in ['muscle', 'strength', 'build', 'gain']):
                    recommendations.extend([
                        'workout_completed',  # Consistency is key
                        'sleep_hours',        # Recovery for muscle growth
                        'water_intake',       # Hydration for performance
                        'weight'              # Track muscle gain
                    ])
                elif any(goal in goals for goal in ['endurance', 'cardio', 'running', 'fitness']):
                    recommendations.extend([
                        'steps',              # Daily activity
                        'water_intake',       # Hydration for performance
                        'sleep_hours',        # Recovery
                        'workout_completed'   # Training consistency
                    ])
                else:
                    # General fitness recommendations
                    recommendations.extend([
                        'water_intake',       # Universal health benefit
                        'sleep_hours',        # Essential for recovery
                        'workout_completed',  # Basic fitness
                        'steps'               # Daily movement
                    ])
            
            elif user_type == 'trainer':
                # Trainer recommendations for client management
                recommendations.extend([
                    'water_intake',       # Easy to track and important
                    'workout_completed',  # Core to training
                    'sleep_hours',        # Recovery tracking
                    'weight'              # Progress monitoring
                ])
            
            return recommendations[:4]  # Limit to 4 habits for better compliance
            
        except Exception as e:
            log_error(f"Error generating habit recommendations: {str(e)}")
            return ['water_intake', 'sleep_hours', 'workout_completed', 'steps']
    
    def _get_client_available_habits(self, client_id: str) -> Dict:
        """Get list of habits available for a specific client"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Get client's habit history
            client_habits_data = habits_service.get_client_habits(client_id, days=30)
            
            available_habits = set()
            if client_habits_data['success'] and client_habits_data['data']:
                for date_data in client_habits_data['data'].values():
                    available_habits.update(date_data.keys())
            
            # Format for display
            habit_display_names = {
                'water_intake': '💧 Water Intake (liters)',
                'sleep_hours': '😴 Sleep Hours',
                'steps': '🚶 Daily Steps',
                'workout_completed': '💪 Workout Completion',
                'weight': '⚖️ Weight (kg)',
                'meals_logged': '🍽️ Meals Logged',
                'calories': '🔥 Calories',
                'mood': '😊 Mood Rating'
            }
            
            formatted_habits = []
            for habit in available_habits:
                display_name = habit_display_names.get(habit, habit.replace('_', ' ').title())
                formatted_habits.append(display_name)
            
            return {
                'success': True,
                'habits': list(available_habits),
                'formatted_habits': formatted_habits,
                'count': len(available_habits)
            }
            
        except Exception as e:
            log_error(f"Error getting client available habits: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'habits': [],
                'formatted_habits': [],
                'count': 0
            }    

    # ==================== PHASE 4: ADVANCED FEATURES ====================
    
    def _handle_habit_challenges_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /habit_challenges command - show and manage habit challenges"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type == 'trainer':
                return self._show_trainer_challenges_dashboard(phone, user_data, whatsapp_service)
            elif user_type == 'client':
                return self._show_client_challenges_dashboard(phone, user_data, whatsapp_service)
            else:
                response = (
                    "🏆 *Habit Challenges Available!*\n\n"
                    "Join exciting habit challenges to stay motivated!\n\n"
                    "Register first to access challenges:\n"
                    "• Type `/registration` to get started"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
                
        except Exception as e:
            log_error(f"Error handling habit challenges command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _show_trainer_challenges_dashboard(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Show trainer's challenge management dashboard"""
        try:
            # Get active challenges created by this trainer
            challenges_result = self.db.table('habit_challenges').select(
                'id, name, challenge_type, start_date, end_date, participant_count'
            ).eq('trainer_id', user_data['id']).eq('is_active', True).execute()
            
            response = "🏆 *Habit Challenges Dashboard*\n\n"
            
            if challenges_result.data:
                response += "*Your Active Challenges:*\n"
                for challenge in challenges_result.data[:5]:
                    participants = challenge.get('participant_count', 0)
                    response += f"🎯 {challenge['name']}\n"
                    response += f"   👥 {participants} participants\n"
                    response += f"   📅 {challenge['start_date']} - {challenge['end_date']}\n\n"
            else:
                response += "No active challenges yet.\n\n"
            
            response += (
                "*Quick Actions:*\n"
                "• `/create_challenge` - Create new challenge\n"
                "• `/challenge_templates` - Use pre-made templates\n"
                "• Type challenge name to view details"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error showing trainer challenges dashboard: {str(e)}")
            response = "❌ Error loading challenges dashboard. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _show_client_challenges_dashboard(self, phone: str, user_data: dict, whatsapp_service) -> Dict:
        """Show client's available and active challenges"""
        try:
            # Get client's active challenges
            active_challenges = self.db.table('challenge_participants').select(
                'challenge_id, joined_at, current_score'
            ).eq('client_id', user_data['id']).eq('is_active', True).execute()
            
            # Get available challenges (from their trainer)
            trainer_id = user_data.get('trainer_id')
            available_challenges = []
            
            if trainer_id:
                available_result = self.db.table('habit_challenges').select(
                    'id, name, description, challenge_type, reward'
                ).eq('trainer_id', trainer_id).eq('is_active', True).execute()
                available_challenges = available_result.data or []
            
            response = "🏆 *Your Habit Challenges*\n\n"
            
            if active_challenges.data:
                response += "*🔥 Active Challenges:*\n"
                for participation in active_challenges.data:
                    # Get challenge details
                    challenge_details = self.db.table('habit_challenges').select(
                        'name, challenge_type'
                    ).eq('id', participation['challenge_id']).execute()
                    
                    if challenge_details.data:
                        challenge = challenge_details.data[0]
                        score = participation.get('current_score', 0)
                        response += f"🎯 {challenge['name']}\n"
                        response += f"   📊 Current Score: {score} points\n\n"
            
            if available_challenges:
                response += "*🆕 Available Challenges:*\n"
                for challenge in available_challenges[:3]:
                    response += f"🎯 {challenge['name']}\n"
                    response += f"   {challenge.get('description', 'No description')}\n"
                    response += f"   🏆 Reward: {challenge.get('reward', 'Achievement badge')}\n\n"
            
            if not active_challenges.data and not available_challenges:
                response += (
                    "No challenges available yet.\n\n"
                    "Ask your trainer to create challenges for you!"
                )
            else:
                response += (
                    "*Quick Actions:*\n"
                    "• `/join_challenge` - Join a new challenge\n"
                    "• `/challenge_leaderboard` - View rankings\n"
                    "• `/my_progress` - Check your progress"
                )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error showing client challenges dashboard: {str(e)}")
            response = "❌ Error loading your challenges. Please try again."
            whatsapp_service.send_message(phone, response)
            return {'success': False, 'error': str(e)}
    
    def _create_habit_challenge(self, trainer_id: str, challenge_data: dict) -> Dict:
        """Create habit-based challenges for clients"""
        try:
            # Validate challenge data
            required_fields = ['name', 'challenge_type', 'duration_days', 'target_habit']
            for field in required_fields:
                if field not in challenge_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Calculate end date
            from datetime import datetime, timedelta
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=challenge_data['duration_days'])
            
            # Create challenge record
            challenge_record = {
                'trainer_id': trainer_id,
                'name': challenge_data['name'],
                'description': challenge_data.get('description', ''),
                'challenge_type': challenge_data['challenge_type'],
                'target_habit': challenge_data['target_habit'],
                'target_value': challenge_data.get('target_value'),
                'duration_days': challenge_data['duration_days'],
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'reward': challenge_data.get('reward', 'Achievement badge'),
                'is_active': True,
                'participant_count': 0,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.db.table('habit_challenges').insert(challenge_record).execute()
            
            if result.data:
                challenge_id = result.data[0]['id']
                log_info(f"Created habit challenge: {challenge_data['name']} (ID: {challenge_id})")
                
                return {
                    'success': True,
                    'challenge_id': challenge_id,
                    'message': f"🎉 Challenge '{challenge_data['name']}' created successfully!"
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create challenge record'
                }
                
        except Exception as e:
            log_error(f"Error creating habit challenge: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_challenge_templates(self) -> List[Dict]:
        """Get pre-defined challenge templates"""
        return [
            {
                'name': '7-Day Water Challenge',
                'description': 'Drink at least 2 liters of water daily for 7 days',
                'challenge_type': 'consistency',
                'target_habit': 'water_intake',
                'target_value': '2',
                'duration_days': 7,
                'reward': 'Hydration Hero Badge'
            },
            {
                'name': '30-Day Workout Streak',
                'description': 'Complete a workout every day for 30 days',
                'challenge_type': 'streak',
                'target_habit': 'workout_completed',
                'duration_days': 30,
                'reward': 'Consistency Champion Badge'
            },
            {
                'name': '14-Day Sleep Quality Challenge',
                'description': 'Get 7+ hours of sleep for 14 consecutive days',
                'challenge_type': 'consistency',
                'target_habit': 'sleep_hours',
                'target_value': '7',
                'duration_days': 14,
                'reward': 'Sleep Master Badge'
            },
            {
                'name': '21-Day Step Challenge',
                'description': 'Walk 10,000+ steps daily for 21 days',
                'challenge_type': 'consistency',
                'target_habit': 'steps',
                'target_value': '10000',
                'duration_days': 21,
                'reward': 'Step Champion Badge'
            },
            {
                'name': 'Team Water Competition',
                'description': 'Compete with other clients on daily water intake',
                'challenge_type': 'competition',
                'target_habit': 'water_intake',
                'duration_days': 14,
                'reward': 'Hydration Team Winner'
            }
        ]
    
    def _send_habit_reminders(self) -> Dict:
        """Send personalized habit reminders based on user preferences"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Get all active clients
            clients_result = self.db.table('clients').select(
                'id, name, whatsapp, trainer_id'
            ).eq('status', 'active').execute()
            
            if not clients_result.data:
                return {'success': True, 'message': 'No active clients found'}
            
            reminders_sent = 0
            today = datetime.now().date().isoformat()
            
            for client in clients_result.data:
                try:
                    # Check if client has logged habits today
                    today_habits = habits_service.get_client_habits(client['id'], days=1)
                    
                    has_logged_today = False
                    if today_habits['success'] and today in today_habits.get('data', {}):
                        has_logged_today = True
                    
                    # Only send reminder if they haven't logged today
                    if not has_logged_today:
                        # Get their active habits
                        client_habits = habits_service.get_client_habits(client['id'], days=7)
                        
                        if client_habits['success'] and client_habits.get('days_tracked', 0) > 0:
                            # Get current streaks for motivation
                            streaks = []
                            for habit_type in habits_service.habit_types:
                                streak = habits_service.calculate_streak(client['id'], habit_type)
                                if streak > 0:
                                    streaks.append(f"{habit_type.replace('_', ' ').title()}: {streak}d")
                            
                            # Create personalized reminder
                            reminder_message = f"🌟 *Daily Habit Reminder*\n\n"
                            reminder_message += f"Hi {client['name']}! Time for your daily habit check-in.\n\n"
                            
                            if streaks:
                                reminder_message += f"🔥 *Keep these streaks going:*\n"
                                for streak in streaks[:3]:
                                    reminder_message += f"• {streak}\n"
                                reminder_message += "\n"
                            
                            reminder_message += (
                                "💪 *Quick log:* Just tell me what you did today!\n"
                                "Examples: 'drank 2L water', 'slept 8 hours', 'workout done'\n\n"
                                "Or use `/log_habit` for the interactive form."
                            )
                            
                            # Send reminder
                            whatsapp_service.send_message(client['whatsapp'], reminder_message)
                            reminders_sent += 1
                            
                            log_info(f"Sent habit reminder to {client['name']} ({client['whatsapp']})")
                
                except Exception as client_error:
                    log_error(f"Error sending reminder to client {client['id']}: {str(client_error)}")
                    continue
            
            return {
                'success': True,
                'message': f'Sent {reminders_sent} habit reminders',
                'reminders_sent': reminders_sent
            }
            
        except Exception as e:
            log_error(f"Error sending habit reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_habit_analytics(self, trainer_id: str) -> Dict:
        """Generate habit analytics for trainers to monitor client progress"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Get trainer's clients
            clients_result = self.db.table('clients').select('id, name').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            if not clients_result.data:
                return {
                    'success': False,
                    'error': 'No active clients found'
                }
            
            analytics = {
                'total_clients': len(clients_result.data),
                'clients_with_habits': 0,
                'average_compliance': 0,
                'habit_popularity': {},
                'top_performers': [],
                'needs_attention': [],
                'total_streaks': 0,
                'longest_streak': 0
            }
            
            client_scores = []
            habit_counts = {}
            
            for client in clients_result.data:
                client_id = client['id']
                client_name = client['name']
                
                # Get client's habit data for last 30 days
                habits_data = habits_service.get_client_habits(client_id, days=30)
                
                if habits_data['success'] and habits_data.get('days_tracked', 0) > 0:
                    analytics['clients_with_habits'] += 1
                    
                    # Calculate compliance rate (days logged / 30)
                    compliance_rate = (habits_data['days_tracked'] / 30) * 100
                    
                    # Count habit types
                    client_habits = set()
                    total_entries = 0
                    
                    for date_data in habits_data['data'].values():
                        for habit_type in date_data.keys():
                            client_habits.add(habit_type)
                            total_entries += 1
                    
                    # Update habit popularity
                    for habit in client_habits:
                        habit_counts[habit] = habit_counts.get(habit, 0) + 1
                    
                    # Calculate streaks
                    client_streaks = []
                    for habit_type in client_habits:
                        streak = habits_service.calculate_streak(client_id, habit_type)
                        if streak > 0:
                            client_streaks.append(streak)
                            analytics['total_streaks'] += 1
                            if streak > analytics['longest_streak']:
                                analytics['longest_streak'] = streak
                    
                    # Client performance score
                    avg_streak = sum(client_streaks) / len(client_streaks) if client_streaks else 0
                    performance_score = (compliance_rate + avg_streak) / 2
                    
                    client_scores.append({
                        'name': client_name,
                        'compliance_rate': compliance_rate,
                        'avg_streak': avg_streak,
                        'performance_score': performance_score,
                        'total_habits': len(client_habits)
                    })
            
            # Calculate overall metrics
            if client_scores:
                analytics['average_compliance'] = sum(c['compliance_rate'] for c in client_scores) / len(client_scores)
                
                # Sort by performance
                client_scores.sort(key=lambda x: x['performance_score'], reverse=True)
                
                # Top performers (top 3 or top 25%)
                top_count = max(1, min(3, len(client_scores) // 4))
                analytics['top_performers'] = client_scores[:top_count]
                
                # Needs attention (bottom 25% with < 50% compliance)
                needs_attention = [c for c in client_scores if c['compliance_rate'] < 50]
                analytics['needs_attention'] = needs_attention[-3:]  # Bottom 3
            
            # Most popular habits
            if habit_counts:
                sorted_habits = sorted(habit_counts.items(), key=lambda x: x[1], reverse=True)
                analytics['habit_popularity'] = dict(sorted_habits)
            
            return {
                'success': True,
                'analytics': analytics
            }
            
        except Exception as e:
            log_error(f"Error generating habit analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }  
  
    # ==================== PHASE 5: INTEGRATION WITH EXISTING FEATURES ====================
    
    def _enhance_profile_with_habits(self, phone: str, user_type: str, user_data: dict, base_profile: str) -> str:
        """Enhance profile information with habit tracking data"""
        try:
            if user_type == 'client':
                from services.habits import HabitTrackingService
                habits_service = HabitTrackingService(self.db)
                
                # Get current streaks
                streaks = []
                total_streak_days = 0
                
                for habit_type in habits_service.habit_types:
                    streak = habits_service.calculate_streak(user_data['id'], habit_type)
                    if streak > 0:
                        habit_name = habit_type.replace('_', ' ').title()
                        streaks.append(f"{habit_name}: {streak}d")
                        total_streak_days += streak
                
                if streaks:
                    habit_section = "\n\n🔥 *Current Habit Streaks:*\n"
                    for streak in streaks[:4]:  # Show top 4 streaks
                        habit_section += f"• {streak}\n"
                    
                    if total_streak_days > 50:
                        habit_section += "\n🌟 Amazing consistency! You're building incredible habits!"
                    elif total_streak_days > 20:
                        habit_section += "\n💪 Great progress! Keep up the momentum!"
                    else:
                        habit_section += "\n🚀 Good start! Consistency is key to success!"
                    
                    return base_profile + habit_section
                else:
                    # No habits tracked yet
                    habit_section = (
                        "\n\n🎯 *Habit Tracking:*\n"
                        "No habits tracked yet. Start building healthy habits!\n"
                        "• Use `/habits` to get started\n"
                        "• Use `/log_habit` to track daily progress"
                    )
                    return base_profile + habit_section
            
            elif user_type == 'trainer':
                # Get trainer's client habit statistics
                clients_result = self.db.table('clients').select('id').eq(
                    'trainer_id', user_data['id']
                ).eq('status', 'active').execute()
                
                if clients_result.data:
                    from services.habits import HabitTrackingService
                    habits_service = HabitTrackingService(self.db)
                    
                    clients_with_habits = 0
                    total_active_streaks = 0
                    
                    for client in clients_result.data:
                        client_habits = habits_service.get_client_habits(client['id'], days=7)
                        if client_habits['success'] and client_habits.get('days_tracked', 0) > 0:
                            clients_with_habits += 1
                            
                            # Count active streaks
                            for habit_type in habits_service.habit_types:
                                streak = habits_service.calculate_streak(client['id'], habit_type)
                                if streak > 0:
                                    total_active_streaks += 1
                    
                    habit_section = (
                        f"\n\n📊 *Client Habit Tracking:*\n"
                        f"• Clients with habits: {clients_with_habits}/{len(clients_result.data)}\n"
                        f"• Active streaks: {total_active_streaks}\n"
                        f"• Use `/habits` to manage client habits"
                    )
                    return base_profile + habit_section
            
            return base_profile
            
        except Exception as e:
            log_error(f"Error enhancing profile with habits: {str(e)}")
            return base_profile
    
    def _add_habit_setup_to_registration_completion(self, phone: str, user_type: str, user_data: dict, base_message: str) -> str:
        """Add habit tracking setup information to registration completion message"""
        try:
            if user_type == 'client':
                habit_section = (
                    "\n\n🎯 *Next Steps - Build Healthy Habits:*\n"
                    "• Type `/habits` to start tracking your progress\n"
                    "• Use `/log_habit` to log daily habits\n"
                    "• Check your streaks with `/habit_streak`\n\n"
                    "💡 *Tip:* Consistent habit tracking is key to reaching your fitness goals!"
                )
            elif user_type == 'trainer':
                habit_section = (
                    "\n\n📊 *Help Your Clients Build Habits:*\n"
                    "• Use `/setup_habits` to configure client habits\n"
                    "• Monitor progress with `/habits` dashboard\n"
                    "• Create challenges with `/create_challenge`\n\n"
                    "💡 *Tip:* Habit tracking increases client engagement and results!"
                )
            else:
                return base_message
            
            return base_message + habit_section
            
        except Exception as e:
            log_error(f"Error adding habit setup to registration: {str(e)}")
            return base_message
    
    def _handle_habit_analytics_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /habit_analytics command - show detailed habit analytics"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type != 'trainer':
                response = (
                    "📊 *Habit Analytics*\n\n"
                    "Analytics are available for trainers only.\n\n"
                    "If you're a trainer, make sure you're registered as one.\n"
                    "If you're a client, ask your trainer for progress reports!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Generate analytics
            analytics_result = self._generate_habit_analytics(user_data['id'])
            
            if not analytics_result['success']:
                response = f"❌ Error generating analytics: {analytics_result['error']}"
                whatsapp_service.send_message(phone, response)
                return {'success': False, 'response': response}
            
            analytics = analytics_result['analytics']
            
            # Format analytics report
            response = "📊 *Habit Analytics Dashboard*\n\n"
            
            # Overview stats
            response += "*📈 Overview:*\n"
            response += f"• Total Clients: {analytics['total_clients']}\n"
            response += f"• Clients with Habits: {analytics['clients_with_habits']}\n"
            response += f"• Average Compliance: {analytics['average_compliance']:.1f}%\n"
            response += f"• Total Active Streaks: {analytics['total_streaks']}\n"
            response += f"• Longest Streak: {analytics['longest_streak']} days\n\n"
            
            # Top performers
            if analytics['top_performers']:
                response += "*🏆 Top Performers:*\n"
                for performer in analytics['top_performers']:
                    response += f"• {performer['name']}: {performer['compliance_rate']:.1f}% compliance\n"
                response += "\n"
            
            # Needs attention
            if analytics['needs_attention']:
                response += "*⚠️ Needs Attention:*\n"
                for client in analytics['needs_attention']:
                    response += f"• {client['name']}: {client['compliance_rate']:.1f}% compliance\n"
                response += "\n"
            
            # Popular habits
            if analytics['habit_popularity']:
                response += "*📊 Most Popular Habits:*\n"
                for habit, count in list(analytics['habit_popularity'].items())[:5]:
                    habit_name = habit.replace('_', ' ').title()
                    response += f"• {habit_name}: {count} clients\n"
                response += "\n"
            
            response += (
                "*Quick Actions:*\n"
                "• `/send_reminders` - Send habit reminders\n"
                "• `/create_challenge` - Create new challenge\n"
                "• `/habits` - View client progress"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling habit analytics command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_send_reminders_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Handle /send_reminders command - manually send habit reminders"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type != 'trainer':
                response = (
                    "📱 *Habit Reminders*\n\n"
                    "Only trainers can send habit reminders to clients.\n\n"
                    "If you're a client, you'll receive automatic reminders!"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Send reminders
            reminder_result = self._send_habit_reminders()
            
            if reminder_result['success']:
                response = (
                    f"📱 *Reminders Sent Successfully!*\n\n"
                    f"✅ Sent {reminder_result['reminders_sent']} habit reminders to clients\n\n"
                    f"Reminders were sent to clients who haven't logged habits today."
                )
            else:
                response = f"❌ Error sending reminders: {reminder_result['error']}"
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling send reminders command: {str(e)}")
            return {'success': False, 'error': str(e)}    

    def _handle_create_challenge_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /create_challenge command - start challenge creation flow"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get challenge templates
            templates = self._get_challenge_templates()
            
            response = (
                "🏆 *Create Habit Challenge*\n\n"
                "Choose from these popular challenge templates:\n\n"
            )
            
            for i, template in enumerate(templates, 1):
                response += f"{i}. **{template['name']}**\n"
                response += f"   {template['description']}\n"
                response += f"   Duration: {template['duration_days']} days\n\n"
            
            response += (
                "Reply with the number of the template you want to use, "
                "or type 'custom' to create a custom challenge.\n\n"
                "Example: '1' for 7-Day Water Challenge"
            )
            
            # Set conversation state for challenge creation
            self.update_conversation_state(phone, 'CHALLENGE_CREATION', {
                'trainer_id': user_data['id'],
                'step': 'select_template',
                'templates': templates
            })
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling create challenge command: {str(e)}")
            return {'success': False, 'error': str(e)}    

    def _handle_challenge_creation_step(self, phone: str, text: str, context: dict) -> Dict:
        """Handle challenge creation conversation step"""
        try:
            step = context.get('step', 'select_template')
            trainer_id = context.get('trainer_id')
            templates = context.get('templates', [])
            
            if step == 'select_template':
                # User is selecting a template
                text_lower = text.strip().lower()
                
                if text_lower == 'custom':
                    return {
                        'success': True,
                        'message': (
                            "🎨 *Custom Challenge Creation*\n\n"
                            "Custom challenge creation is coming soon!\n\n"
                            "For now, please choose from the available templates by typing the number (1-5)."
                        ),
                        'completed': False,
                        'context': context
                    }
                
                # Try to parse template selection
                try:
                    template_index = int(text_lower) - 1
                    if 0 <= template_index < len(templates):
                        selected_template = templates[template_index]
                        
                        # Create the challenge
                        challenge_result = self._create_habit_challenge(trainer_id, selected_template)
                        
                        if challenge_result['success']:
                            message = (
                                f"🎉 *Challenge Created Successfully!*\n\n"
                                f"✅ **{selected_template['name']}**\n"
                                f"📝 {selected_template['description']}\n"
                                f"⏱️ Duration: {selected_template['duration_days']} days\n"
                                f"🏆 Reward: {selected_template['reward']}\n\n"
                                f"Your clients can now join this challenge!\n"
                                f"Use `/habit_challenges` to manage all your challenges."
                            )
                            
                            return {
                                'success': True,
                                'message': message,
                                'completed': True
                            }
                        else:
                            return {
                                'success': False,
                                'message': f"❌ Error creating challenge: {challenge_result['error']}",
                                'completed': True
                            }
                    else:
                        return {
                            'success': True,
                            'message': (
                                f"❌ Invalid selection. Please choose a number between 1 and {len(templates)}, "
                                f"or type 'custom' for a custom challenge."
                            ),
                            'completed': False,
                            'context': context
                        }
                        
                except ValueError:
                    return {
                        'success': True,
                        'message': (
                            f"❌ Please enter a valid number (1-{len(templates)}) or 'custom'.\n\n"
                            f"Example: Type '1' to select the 7-Day Water Challenge."
                        ),
                        'completed': False,
                        'context': context
                    }
            
            else:
                return {
                    'success': False,
                    'message': '❌ Invalid challenge creation step. Please start over with `/create_challenge`.',
                    'completed': True
                }
                
        except Exception as e:
            log_error(f"Error handling challenge creation step: {str(e)}")
            return {
                'success': False,
                'message': '❌ Error creating challenge. Please try again.',
                'completed': True
            }    

    def _handle_habit_progress_command(self, phone: str, user_data: dict) -> Dict:
        """Handle /habit_progress command - show detailed progress using WhatsApp flow"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Try WhatsApp Flow first, fallback to text report
            try:
                from services.whatsapp_flow_handler import WhatsAppFlowHandler
                flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                
                # Send WhatsApp Flow
                flow_result = flow_handler.send_habit_progress_flow(phone, user_data)
                
                if flow_result.get('success'):
                    log_info(f"Sent habit progress flow to {phone}")
                    return {
                        'success': True,
                        'method': 'whatsapp_flow',
                        'response': 'Progress flow sent! View your detailed habit progress.'
                    }
                else:
                    log_warning(f"WhatsApp Flow failed for habit progress: {flow_result.get('error')}")
                    # Continue to fallback below
                    
            except Exception as flow_error:
                log_warning(f"WhatsApp Flow handler error: {str(flow_error)}")
                # Continue to fallback below
            
            # FALLBACK: Use text-based progress report
            log_info(f"Using text fallback for habit progress: {phone}")
            
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.db)
            
            # Generate progress report
            response = self._format_habit_progress_report(user_data['id'], habits_service)
            
            response += (
                "\n*Quick Actions:*\n"
                "• `/log_habit` - Log today's habits\n"
                "• `/habit_streak` - Check all your streaks\n"
                "• `/habits` - View habit dashboard"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'method': 'text_fallback', 'response': response}
            
        except Exception as e:
            log_error(f"Error handling habit progress command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _test_habit_flows(self, phone: str, user_type: str, user_data: dict) -> Dict:
        """Test method to verify habit flows are working - can be called via /test_flows"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            if user_type == 'trainer':
                # Test trainer habit setup flow
                try:
                    from services.whatsapp_flow_handler import WhatsAppFlowHandler
                    flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                    
                    result = flow_handler.send_trainer_habit_setup_flow(phone, user_data)
                    
                    response = f"🧪 *Flow Test Results:*\n\n"
                    response += f"**Trainer Habit Setup Flow:**\n"
                    response += f"Success: {result.get('success')}\n"
                    response += f"Method: {result.get('method', 'N/A')}\n"
                    response += f"Error: {result.get('error', 'None')}\n"
                    
                    whatsapp_service.send_message(phone, response)
                    return {'success': True, 'response': response}
                    
                except Exception as e:
                    error_response = f"❌ Flow test failed: {str(e)}"
                    whatsapp_service.send_message(phone, error_response)
                    return {'success': False, 'error': str(e)}
            
            elif user_type == 'client':
                # Test client habit logging flow
                try:
                    from services.whatsapp_flow_handler import WhatsAppFlowHandler
                    flow_handler = WhatsAppFlowHandler(self.db, whatsapp_service)
                    
                    result = flow_handler.send_client_habit_logging_flow(phone, user_data)
                    
                    response = f"🧪 *Flow Test Results:*\n\n"
                    response += f"**Client Habit Logging Flow:**\n"
                    response += f"Success: {result.get('success')}\n"
                    response += f"Method: {result.get('method', 'N/A')}\n"
                    response += f"Error: {result.get('error', 'None')}\n"
                    
                    whatsapp_service.send_message(phone, response)
                    return {'success': True, 'response': response}
                    
                except Exception as e:
                    error_response = f"❌ Flow test failed: {str(e)}"
                    whatsapp_service.send_message(phone, error_response)
                    return {'success': False, 'error': str(e)}
            
            else:
                response = "🧪 Flow testing is only available for registered trainers and clients."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
                
        except Exception as e:
            log_error(f"Error testing habit flows: {str(e)}")
            return {'success': False, 'error': str(e)}