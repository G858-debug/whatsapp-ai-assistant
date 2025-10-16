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
            elif command == '/trainer' and user_type == 'client':
                return self._handle_trainer_info_command(phone, user_data)
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
                "• `/add_client` - Add a new client"
            )
        elif user_type == 'client':
            return (
                "• `/help` - Show all commands\n"
                "• `/profile` - View your profile\n"
                "• `/edit_profile` - Edit your profile\n"
                "• `/trainer` - View trainer info"
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
                            from services.registration.client_registration import ClientRegistrationHandler
                            reg = ClientRegistrationHandler(self.db, whatsapp_service)
                            
                            welcome_message = reg.start_registration(phone)
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
                            log_info(f"Started client registration for {phone}")
                            return {'success': True, 'response': welcome_message}
                            
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
                    "💬 *General:*\n"
                    "• Just chat with me for fitness guidance\n"
                    "• Ask about workouts, nutrition, or goals\n\n"
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
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
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
        """Handle /add_client command - start client addition process"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            response = (
                "➕ *Add New Client*\n\n"
                "To add a client, they need to message you directly!\n\n"
                "📱 *How it works:*\n"
                "1. Share your WhatsApp number with your client\n"
                "2. Ask them to send you a message saying 'Hi'\n"
                "3. I'll help them register as your client\n\n"
                "🔄 *Alternative:*\n"
                "• Give them this message to send: 'I want trainer [your name]'\n"
                "• They can also say 'I need a trainer'\n\n"
                "💡 *Coming Soon:* Direct client invitation links!"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error handling add client command: {str(e)}")
            return {'success': False, 'error': str(e)}
    
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
