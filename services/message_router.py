"""
Message Router - Phase 1 Integration
Routes incoming messages based on authentication status and user role
"""
from typing import Dict, Optional
from utils.logger import log_info, log_error
from services.auth import AuthenticationService, RegistrationService, TaskService


class MessageRouter:
    """Routes messages to appropriate handlers based on user authentication state"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = AuthenticationService(supabase_client)
        self.reg_service = RegistrationService(supabase_client)
        self.task_service = TaskService(supabase_client)
    
    def route_message(self, phone: str, message: str) -> Dict:
        """
        Main routing logic - determines where to send the message
        Returns: {'success': bool, 'response': str, 'handler': str}
        """
        try:
            log_info(f"Routing message from {phone}: {message[:50]}")
            
            # Step 1: Check for universal commands (work regardless of state)
            if message.startswith('/'):
                return self._handle_universal_command(phone, message)
            
            # Step 2: Check if user exists
            user = self.auth_service.check_user_exists(phone)
            
            if not user:
                # New user - start registration flow
                return self._handle_new_user(phone, message)
            
            # Step 3: Check login status
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                # User exists but not logged in
                return self._handle_login_flow(phone, message)
            
            # Step 4: User is logged in - route to role handler
            return self._handle_logged_in_user(phone, message, login_status)
            
        except Exception as e:
            log_error(f"Error routing message: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'error'
            }

    
    def _handle_universal_command(self, phone: str, command: str) -> Dict:
        """Handle universal commands that work in any state"""
        try:
            cmd = command.lower().strip()
            
            if cmd == '/help':
                from services.commands.help_command import handle_help
                return handle_help(phone, self.auth_service, self.whatsapp)
            
            elif cmd == '/logout':
                from services.commands.logout_command import handle_logout
                return handle_logout(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif cmd == '/switch-role':
                from services.commands.switch_role_command import handle_switch_role
                return handle_switch_role(phone, self.auth_service, self.task_service, self.whatsapp)
            
            elif cmd == '/register':
                from services.commands.register_command import handle_register
                return handle_register(phone, self.auth_service, self.whatsapp)
            
            elif cmd == '/stop':
                from services.commands.stop_command import handle_stop
                return handle_stop(phone, self.auth_service, self.task_service, self.whatsapp)
            
            else:
                # Not a universal command, return None to continue routing
                return None
                
        except Exception as e:
            log_error(f"Error handling universal command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing command: {str(e)}",
                'handler': 'universal_command_error'
            }
    
    def _handle_new_user(self, phone: str, message: str) -> Dict:
        """Handle messages from new users (not in database)"""
        try:
            from services.flows.registration_flow import RegistrationFlowHandler
            
            flow_handler = RegistrationFlowHandler(
                self.db, self.whatsapp, self.auth_service, 
                self.reg_service, self.task_service
            )
            
            return flow_handler.handle_new_user(phone, message)
            
        except Exception as e:
            log_error(f"Error handling new user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error during registration. Please try again.",
                'handler': 'new_user_error'
            }
    
    def _handle_login_flow(self, phone: str, message: str) -> Dict:
        """Handle login flow for existing users"""
        try:
            from services.flows.login_flow import LoginFlowHandler
            
            flow_handler = LoginFlowHandler(
                self.db, self.whatsapp, self.auth_service, self.task_service
            )
            
            return flow_handler.handle_login(phone, message)
            
        except Exception as e:
            log_error(f"Error handling login flow: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error during login. Please try again.",
                'handler': 'login_flow_error'
            }
    
    def _handle_logged_in_user(self, phone: str, message: str, role: str) -> Dict:
        """Handle messages from logged-in users"""
        try:
            # Get user ID for this role
            user_id = self.auth_service.get_user_id_by_role(phone, role)
            
            if not user_id:
                log_error(f"User ID not found for {phone} with role {role}")
                return {
                    'success': False,
                    'response': "Sorry, there was an error with your account. Please try logging in again.",
                    'handler': 'user_id_error'
                }
            
            # Check for role-specific commands
            if message.startswith('/'):
                return self._handle_role_command(phone, message, role, user_id)
            
            # Check for running task
            running_task = self.task_service.get_running_task(user_id, role)
            
            if running_task and running_task.get('task_status') == 'running':
                # Continue with the running task
                return self._continue_task(phone, message, role, user_id, running_task)
            
            # No running task - use AI to determine intent
            return self._handle_ai_intent(phone, message, role, user_id)
            
        except Exception as e:
            log_error(f"Error handling logged-in user: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'logged_in_error'
            }

    
    def _handle_role_command(self, phone: str, command: str, role: str, user_id: str) -> Dict:
        """Handle role-specific commands"""
        try:
            cmd = command.lower().strip()
            
            # Common commands (both roles)
            if cmd == '/view-profile':
                from services.commands.profile_commands import handle_view_profile
                return handle_view_profile(phone, role, user_id, self.db, self.whatsapp, self.reg_service)
            
            elif cmd == '/edit-profile':
                from services.commands.profile_commands import handle_edit_profile
                return handle_edit_profile(phone, role, user_id, self.db, self.whatsapp, 
                                          self.reg_service, self.task_service)
            
            elif cmd == '/delete-account':
                from services.commands.profile_commands import handle_delete_account
                return handle_delete_account(phone, role, user_id, self.db, self.whatsapp,
                                            self.auth_service, self.task_service)
            
            # Trainer commands (Phase 2 - placeholders)
            elif role == 'trainer':
                if cmd == '/invite-trainee':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/create-trainee':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/view-trainees':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/remove-trainee':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
            
            # Client commands (Phase 2 - placeholders)
            elif role == 'client':
                if cmd == '/search-trainer':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/invite-trainer':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/view-trainers':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
                elif cmd == '/remove-trainer':
                    return {'success': True, 'response': "🚧 This feature is coming in Phase 2!", 'handler': 'phase2'}
            
            # Unknown command
            return {
                'success': True,
                'response': f"❓ Unknown command: {command}\n\nType /help to see available commands.",
                'handler': 'unknown_command'
            }
            
        except Exception as e:
            log_error(f"Error handling role command: {str(e)}")
            return {
                'success': False,
                'response': f"Error processing command: {str(e)}",
                'handler': 'role_command_error'
            }
    
    def _continue_task(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue with a running task"""
        try:
            task_type = task.get('task_type')
            task_id = task.get('id')
            
            log_info(f"Continuing task {task_type} for {phone}")
            
            # Route to appropriate task handler
            if task_type == 'registration':
                from services.flows.registration_flow import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, role, task)
            
            elif task_type == 'edit_profile':
                from services.flows.profile_flow import ProfileFlowHandler
                handler = ProfileFlowHandler(
                    self.db, self.whatsapp, self.reg_service, self.task_service
                )
                return handler.continue_edit_profile(phone, message, role, user_id, task)
            
            elif task_type == 'delete_account':
                from services.flows.profile_flow import ProfileFlowHandler
                handler = ProfileFlowHandler(
                    self.db, self.whatsapp, self.reg_service, self.task_service
                )
                return handler.continue_delete_account(phone, message, role, user_id, task)
            
            else:
                log_error(f"Unknown task type: {task_type}")
                # Stop the unknown task
                self.task_service.stop_task(task_id, role)
                return {
                    'success': True,
                    'response': "Sorry, I lost track of what we were doing. Let's start fresh. What can I help you with?",
                    'handler': 'unknown_task'
                }
                
        except Exception as e:
            log_error(f"Error continuing task: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Type /stop to cancel the current task.",
                'handler': 'task_continue_error'
            }
    
    def _handle_ai_intent(self, phone: str, message: str, role: str, user_id: str) -> Dict:
        """Use AI to determine user intent and respond"""
        try:
            # Get recent tasks and chat history for context
            recent_tasks = self.task_service.get_recent_completed_tasks(user_id, role, limit=5)
            
            # Get chat history from message_history table
            chat_history = self._get_chat_history(phone, limit=10)
            
            # Save current message to history
            self._save_message(phone, message, 'user')
            
            # Use AI to determine intent
            from services.ai_intent_handler_phase1 import AIIntentHandler
            ai_handler = AIIntentHandler(self.db, self.whatsapp)
            
            result = ai_handler.handle_intent(
                phone, message, role, user_id,
                recent_tasks, chat_history
            )
            
            # Save bot response to history
            if result.get('response'):
                self._save_message(phone, result['response'], 'bot')
            
            return result
            
        except Exception as e:
            log_error(f"Error handling AI intent: {str(e)}")
            return {
                'success': True,
                'response': (
                    "I'm here to help! Here are some things you can do:\n\n"
                    "• Type /help to see all commands\n"
                    "• Type /view-profile to see your profile\n"
                    "• Type /edit-profile to update your information\n\n"
                    "What would you like to do?"
                ),
                'handler': 'ai_intent_fallback'
            }
    
    def _get_chat_history(self, phone: str, limit: int = 10) -> list:
        """Get recent chat history"""
        try:
            result = self.db.table('message_history').select('*').eq(
                'phone_number', phone
            ).order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                # Reverse to get chronological order
                return list(reversed(result.data))
            return []
            
        except Exception as e:
            log_error(f"Error getting chat history: {str(e)}")
            return []
    
    def _save_message(self, phone: str, message: str, sender: str) -> bool:
        """Save message to history"""
        try:
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            
            message_data = {
                'phone_number': phone,
                'message': message[:1000],  # Limit message length
                'sender': sender,  # 'user' or 'bot'
                'created_at': datetime.now(sa_tz).isoformat()
            }
            
            self.db.table('message_history').insert(message_data).execute()
            return True
            
        except Exception as e:
            log_error(f"Error saving message: {str(e)}")
            return False
