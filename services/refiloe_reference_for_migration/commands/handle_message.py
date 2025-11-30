"""
Handle Message
Handle incoming WhatsApp message - main entry point
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

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

        # CHECK FOR PACKAGE DEAL CLARIFICATION
        if conv_state.get('state') == 'PACKAGE_DEAL_CLARIFICATION':
            log_info(f"User {phone} is providing package deal clarification")

            try:
                result = self._handle_package_clarification(phone, text, conv_state.get('context', {}))

                if result.get('success'):
                    whatsapp_service.send_message(phone, result['message'])
                    self.clear_conversation_state(phone)
                    return {'success': True, 'response': result['message']}
                else:
                    whatsapp_service.send_message(phone, result['message'])
                    return {'success': False, 'response': result['message']}

            except Exception as e:
                log_error(f"Error processing package clarification: {str(e)}")
                error_msg = "❌ Sorry, there was an error processing your package details. Please try again."
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
