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
    
    def route_message(self, phone: str, message: str, button_id: str = None) -> Dict:
        """
        Main routing logic - determines where to send the message
        Returns: {'success': bool, 'response': str, 'handler': str}
        """
        try:
            log_info(f"Routing message from {phone}: {message[:50]}")
            
            # Step 0: Check for button responses (Phase 2 invitations)
            if button_id:
                return self._handle_button_response(phone, button_id)
            
            # Step 1: Check for universal commands (work regardless of state)
            if message.startswith('/'):
                return self._handle_universal_command(phone, message)
            
            # Step 2: Check for running registration tasks (before checking user exists)
            # This handles the case where registration is in progress but user not created yet
            trainer_task = self.task_service.get_running_task(phone, 'trainer')
            client_task = self.task_service.get_running_task(phone, 'client')
            
            if trainer_task and trainer_task.get('task_type') == 'registration':
                from services.flows.registration_flow import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'trainer', trainer_task)
            
            if client_task and client_task.get('task_type') == 'registration':
                from services.flows.registration_flow import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.continue_registration(phone, message, 'client', client_task)
            
            # Step 3: Check if user exists
            user = self.auth_service.check_user_exists(phone)
            
            if not user:
                # New user - start registration flow
                return self._handle_new_user(phone, message)
            
            # Step 4: Check login status
            login_status = self.auth_service.get_login_status(phone)
            
            if not login_status:
                # User exists but not logged in
                return self._handle_login_flow(phone, message)
            
            # Step 5: User is logged in - route to role handler
            return self._handle_logged_in_user(phone, message, login_status)
            
        except Exception as e:
            log_error(f"Error routing message: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'error'
            }

    
    def _handle_button_response(self, phone: str, button_id: str) -> Dict:
        """Handle button responses for Phase 2 invitations"""
        try:
            log_info(f"Handling button response: {button_id} from {phone}")
            
            from services.relationships import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            # Parse button ID
            if button_id.startswith('accept_trainer_'):
                # Client accepting trainer invitation
                trainer_id = button_id.replace('accept_trainer_', '')
                
                # Get client_id
                user = self.auth_service.check_user_exists(phone)
                if not user or not user.get('client_id'):
                    return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
                
                client_id = user['client_id']
                
                # Approve relationship
                success = relationship_service.approve_relationship(trainer_id, client_id)
                
                if success:
                    # Get trainer info
                    trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                        
                        # Notify client
                        msg = f"✅ You're now connected with {trainer_name}!"
                        self.whatsapp.send_message(phone, msg)
                        
                        # Notify trainer
                        client_result = self.db.table('clients').select('first_name, last_name').eq(
                            'client_id', client_id
                        ).execute()
                        
                        if client_result.data:
                            client = client_result.data[0]
                            client_name = f"{client.get('first_name')} {client.get('last_name')}"
                            trainer_msg = f"✅ {client_name} accepted your invitation!"
                            self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                        
                        return {'success': True, 'response': msg, 'handler': 'accept_trainer'}
                
                return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_trainer_failed'}
            
            elif button_id.startswith('decline_trainer_'):
                # Client declining trainer invitation
                trainer_id = button_id.replace('decline_trainer_', '')
                
                # Get client_id
                user = self.auth_service.check_user_exists(phone)
                if not user or not user.get('client_id'):
                    return {'success': False, 'response': 'Error: Client ID not found', 'handler': 'button_error'}
                
                client_id = user['client_id']
                
                # Decline relationship
                success = relationship_service.decline_relationship(trainer_id, client_id)
                
                if success:
                    # Get trainer info
                    trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                        
                        # Notify client
                        msg = f"You declined the invitation from {trainer_name}."
                        self.whatsapp.send_message(phone, msg)
                        
                        # Notify trainer
                        client_result = self.db.table('clients').select('first_name, last_name').eq(
                            'client_id', client_id
                        ).execute()
                        
                        if client_result.data:
                            client = client_result.data[0]
                            client_name = f"{client.get('first_name')} {client.get('last_name')}"
                            trainer_msg = f"ℹ️ {client_name} declined your invitation."
                            self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                        
                        return {'success': True, 'response': msg, 'handler': 'decline_trainer'}
                
                return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_trainer_failed'}
            
            elif button_id.startswith('accept_client_'):
                # Trainer accepting client invitation
                client_id = button_id.replace('accept_client_', '')
                
                # Get trainer_id
                user = self.auth_service.check_user_exists(phone)
                if not user or not user.get('trainer_id'):
                    return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
                
                trainer_id = user['trainer_id']
                
                # Approve relationship
                success = relationship_service.approve_relationship(trainer_id, client_id)
                
                if success:
                    # Get client info
                    client_result = self.db.table('clients').select('first_name, last_name, phone_number').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = f"{client.get('first_name')} {client.get('last_name')}"
                        
                        # Notify trainer
                        msg = f"✅ You're now connected with {client_name}!"
                        self.whatsapp.send_message(phone, msg)
                        
                        # Notify client
                        trainer_result = self.db.table('trainers').select('first_name, last_name').eq(
                            'trainer_id', trainer_id
                        ).execute()
                        
                        if trainer_result.data:
                            trainer = trainer_result.data[0]
                            trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                            client_msg = f"✅ {trainer_name} accepted your invitation!"
                            self.whatsapp.send_message(client['phone_number'], client_msg)
                        
                        return {'success': True, 'response': msg, 'handler': 'accept_client'}
                
                return {'success': False, 'response': 'Failed to accept invitation', 'handler': 'accept_client_failed'}
            
            elif button_id.startswith('decline_client_'):
                # Trainer declining client invitation
                client_id = button_id.replace('decline_client_', '')
                
                # Get trainer_id
                user = self.auth_service.check_user_exists(phone)
                if not user or not user.get('trainer_id'):
                    return {'success': False, 'response': 'Error: Trainer ID not found', 'handler': 'button_error'}
                
                trainer_id = user['trainer_id']
                
                # Decline relationship
                success = relationship_service.decline_relationship(trainer_id, client_id)
                
                if success:
                    # Get client info
                    client_result = self.db.table('clients').select('first_name, last_name, phone_number').eq(
                        'client_id', client_id
                    ).execute()
                    
                    if client_result.data:
                        client = client_result.data[0]
                        client_name = f"{client.get('first_name')} {client.get('last_name')}"
                        
                        # Notify trainer
                        msg = f"You declined the invitation from {client_name}."
                        self.whatsapp.send_message(phone, msg)
                        
                        # Notify client
                        trainer_result = self.db.table('trainers').select('first_name, last_name').eq(
                            'trainer_id', trainer_id
                        ).execute()
                        
                        if trainer_result.data:
                            trainer = trainer_result.data[0]
                            trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                            client_msg = f"ℹ️ {trainer_name} declined your invitation."
                            self.whatsapp.send_message(client['phone_number'], client_msg)
                        
                        return {'success': True, 'response': msg, 'handler': 'decline_client'}
                
                return {'success': False, 'response': 'Failed to decline invitation', 'handler': 'decline_client_failed'}
            
            elif button_id.startswith('approve_new_client_'):
                # New client approving account creation
                trainer_id = button_id.replace('approve_new_client_', '')
                
                # Get prefilled data from invitation (stored in a temporary table or task)
                # For now, we'll retrieve from a pending_invitations table or similar
                try:
                    # Check if there's a pending invitation for this phone and trainer
                    invitation_result = self.db.table('client_invitations').select('*').eq(
                        'phone_number', phone
                    ).eq('trainer_id', trainer_id).eq('status', 'pending').execute()
                    
                    if not invitation_result.data:
                        msg = "❌ Invitation not found or expired. Please ask your trainer to send a new invitation."
                        self.whatsapp.send_message(phone, msg)
                        return {'success': False, 'response': msg, 'handler': 'approve_new_client_no_invitation'}
                    
                    invitation = invitation_result.data[0]
                    prefilled_data = invitation.get('prefilled_data', {})
                    
                    # Generate client_id
                    from services.auth.authentication_service import AuthenticationService
                    auth_service = AuthenticationService(self.db)
                    client_id = auth_service.generate_unique_id(
                        prefilled_data.get('first_name', 'Client'),
                        'clients',
                        'client_id'
                    )
                    
                    # Create client account
                    from datetime import datetime
                    import pytz
                    sa_tz = pytz.timezone('Africa/Johannesburg')
                    
                    client_data = {
                        'client_id': client_id,
                        'phone_number': phone,
                        'first_name': prefilled_data.get('first_name'),
                        'last_name': prefilled_data.get('last_name'),
                        'email': prefilled_data.get('email'),
                        'fitness_goals': prefilled_data.get('fitness_goals'),
                        'experience_level': prefilled_data.get('experience_level'),
                        'health_conditions': prefilled_data.get('health_conditions'),
                        'preferred_workout_time': prefilled_data.get('preferred_workout_time'),
                        'registration_date': datetime.now(sa_tz).isoformat()
                    }
                    
                    # Insert into clients table
                    self.db.table('clients').insert(client_data).execute()
                    
                    # Create user entry
                    user_data = {
                        'phone_number': phone,
                        'client_id': client_id,
                        'login_status': 'client',
                        'created_at': datetime.now(sa_tz).isoformat()
                    }
                    self.db.table('users').insert(user_data).execute()
                    
                    # Create relationship
                    from services.relationships import RelationshipService
                    relationship_service = RelationshipService(self.db)
                    relationship_service.create_relationship(trainer_id, client_id)
                    
                    # Update invitation status
                    self.db.table('client_invitations').update({
                        'status': 'accepted',
                        'accepted_at': datetime.now(sa_tz).isoformat()
                    }).eq('id', invitation['id']).execute()
                    
                    # Notify new client
                    msg = (
                        f"✅ *Account Created Successfully!*\n\n"
                        f"Welcome to Refiloe, {prefilled_data.get('first_name')}!\n\n"
                        f"*Your Client ID:* {client_id}\n\n"
                        f"You're now connected with your trainer.\n"
                        f"Type /help to see what you can do!"
                    )
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                        'trainer_id', trainer_id
                    ).execute()
                    
                    if trainer_result.data:
                        trainer = trainer_result.data[0]
                        trainer_msg = (
                            f"✅ *New Client Added!*\n\n"
                            f"{prefilled_data.get('first_name')} {prefilled_data.get('last_name')} "
                            f"approved your invitation!\n\n"
                            f"*Client ID:* {client_id}\n\n"
                            f"They're now in your client list."
                        )
                        self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'approve_new_client_success'}
                    
                except Exception as e:
                    log_error(f"Error creating new client account: {str(e)}")
                    msg = "❌ Error creating account. Please try again or contact your trainer."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': False, 'response': msg, 'handler': 'approve_new_client_error'}
            
            elif button_id.startswith('reject_new_client_'):
                # New client rejecting account creation
                trainer_id = button_id.replace('reject_new_client_', '')
                
                # Get trainer info and notify
                trainer_result = self.db.table('trainers').select('first_name, last_name, phone_number').eq(
                    'trainer_id', trainer_id
                ).execute()
                
                if trainer_result.data:
                    trainer = trainer_result.data[0]
                    trainer_name = f"{trainer.get('first_name')} {trainer.get('last_name')}"
                    
                    # Notify user
                    msg = f"You declined the invitation from {trainer_name}."
                    self.whatsapp.send_message(phone, msg)
                    
                    # Notify trainer
                    trainer_msg = f"ℹ️ The invitation you sent was declined."
                    self.whatsapp.send_message(trainer['phone_number'], trainer_msg)
                    
                    return {'success': True, 'response': msg, 'handler': 'reject_new_client'}
            
            # Handle registration buttons
            elif button_id == 'register_trainer':
                log_info(f"Registration button clicked: register_trainer")
                from services.flows.registration_flow import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.start_registration(phone, 'trainer')
            
            elif button_id == 'register_client':
                log_info(f"Registration button clicked: register_client")
                from services.flows.registration_flow import RegistrationFlowHandler
                handler = RegistrationFlowHandler(
                    self.db, self.whatsapp, self.auth_service,
                    self.reg_service, self.task_service
                )
                return handler.start_registration(phone, 'client')
            
            # Handle login buttons
            elif button_id == 'login_trainer':
                log_info(f"Login button clicked: login_trainer")
                from services.flows.login_flow import LoginFlowHandler
                handler = LoginFlowHandler(self.db, self.whatsapp, self.auth_service)
                return handler.handle_role_selection(phone, 'trainer')
            
            elif button_id == 'login_client':
                log_info(f"Login button clicked: login_client")
                from services.flows.login_flow import LoginFlowHandler
                handler = LoginFlowHandler(self.db, self.whatsapp, self.auth_service)
                return handler.handle_role_selection(phone, 'client')
            
            else:
                log_error(f"Unknown button ID: {button_id}")
                return {'success': False, 'response': 'Unknown button action', 'handler': 'button_unknown'}
                
        except Exception as e:
            log_error(f"Error handling button response: {str(e)}")
            return {'success': False, 'response': 'Error processing button', 'handler': 'button_error'}
    
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
            
            # Trainer commands (Phase 2 & 3)
            elif role == 'trainer':
                # Phase 2: Relationship commands
                if cmd == '/invite-trainee':
                    from services.commands.trainer_relationship_commands import handle_invite_trainee
                    return handle_invite_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/create-trainee':
                    from services.commands.trainer_relationship_commands import handle_create_trainee
                    return handle_create_trainee(phone, user_id, self.db, self.whatsapp, self.reg_service, self.task_service)
                elif cmd == '/view-trainees':
                    from services.commands.trainer_relationship_commands import handle_view_trainees
                    return handle_view_trainees(phone, user_id, self.db, self.whatsapp)
                elif cmd == '/remove-trainee':
                    from services.commands.trainer_relationship_commands import handle_remove_trainee
                    return handle_remove_trainee(phone, user_id, self.db, self.whatsapp, self.task_service)
                
                # Phase 3: Habit commands
                elif cmd == '/create-habit':
                    from services.commands.trainer_habit_commands import handle_create_habit
                    return handle_create_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/edit-habit':
                    from services.commands.trainer_habit_commands import handle_edit_habit
                    return handle_edit_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/delete-habit':
                    from services.commands.trainer_habit_commands import handle_delete_habit
                    return handle_delete_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/assign-habit':
                    from services.commands.trainer_habit_commands import handle_assign_habit
                    return handle_assign_habit(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/view-habits':
                    from services.commands.trainer_habit_commands import handle_view_habits
                    return handle_view_habits(phone, user_id, self.db, self.whatsapp)
                elif cmd == '/view-trainee-progress':
                    from services.commands.trainer_habit_commands import handle_view_trainee_progress
                    return handle_view_trainee_progress(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/trainee-weekly-report':
                    from services.commands.trainer_habit_commands import handle_trainee_report
                    return handle_trainee_report(phone, user_id, self.db, self.whatsapp, self.task_service, 'weekly')
                elif cmd == '/trainee-monthly-report':
                    from services.commands.trainer_habit_commands import handle_trainee_report
                    return handle_trainee_report(phone, user_id, self.db, self.whatsapp, self.task_service, 'monthly')
            
            # Client commands (Phase 2 & 3)
            elif role == 'client':
                # Phase 2: Relationship commands
                if cmd == '/search-trainer':
                    from services.commands.client_relationship_commands import handle_search_trainer
                    return handle_search_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/invite-trainer':
                    from services.commands.client_relationship_commands import handle_invite_trainer
                    return handle_invite_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/view-trainers':
                    from services.commands.client_relationship_commands import handle_view_trainers
                    return handle_view_trainers(phone, user_id, self.db, self.whatsapp)
                elif cmd == '/remove-trainer':
                    from services.commands.client_relationship_commands import handle_remove_trainer
                    return handle_remove_trainer(phone, user_id, self.db, self.whatsapp, self.task_service)
                
                # Phase 3: Habit commands
                elif cmd == '/view-my-habits':
                    from services.commands.client_habit_commands import handle_view_my_habits
                    return handle_view_my_habits(phone, user_id, self.db, self.whatsapp)
                elif cmd == '/log-habits':
                    from services.commands.client_habit_commands import handle_log_habits
                    return handle_log_habits(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/view-progress':
                    from services.commands.client_habit_commands import handle_view_progress
                    return handle_view_progress(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/weekly-report':
                    from services.commands.client_habit_commands import handle_weekly_report
                    return handle_weekly_report(phone, user_id, self.db, self.whatsapp, self.task_service)
                elif cmd == '/monthly-report':
                    from services.commands.client_habit_commands import handle_monthly_report
                    return handle_monthly_report(phone, user_id, self.db, self.whatsapp, self.task_service)
            
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
            
            # Phase 2: Trainer relationship tasks
            elif task_type == 'invite_trainee':
                from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
                handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_invite_trainee(phone, message, user_id, task)
            
            elif task_type == 'create_trainee':
                from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
                handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service, self.reg_service)
                return handler.continue_create_trainee(phone, message, user_id, task)
            
            elif task_type == 'remove_trainee':
                from services.flows.trainer_relationship_flows import TrainerRelationshipFlows
                handler = TrainerRelationshipFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_remove_trainee(phone, message, user_id, task)
            
            # Phase 2: Client relationship tasks
            elif task_type == 'search_trainer':
                from services.flows.client_relationship_flows import ClientRelationshipFlows
                handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_search_trainer(phone, message, user_id, task)
            
            elif task_type == 'invite_trainer':
                from services.flows.client_relationship_flows import ClientRelationshipFlows
                handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_invite_trainer(phone, message, user_id, task)
            
            elif task_type == 'remove_trainer':
                from services.flows.client_relationship_flows import ClientRelationshipFlows
                handler = ClientRelationshipFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_remove_trainer(phone, message, user_id, task)
            
            # Phase 3: Trainer habit tasks
            elif task_type == 'create_habit':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_create_habit(phone, message, user_id, task)
            
            elif task_type == 'edit_habit':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_edit_habit(phone, message, user_id, task)
            
            elif task_type == 'delete_habit':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_delete_habit(phone, message, user_id, task)
            
            elif task_type == 'assign_habit':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_assign_habit(phone, message, user_id, task)
            
            elif task_type == 'view_trainee_progress':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_view_trainee_progress(phone, message, user_id, task)
            
            elif task_type == 'trainee_report':
                from services.flows.trainer_habit_flows import TrainerHabitFlows
                handler = TrainerHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_trainee_report(phone, message, user_id, task)
            
            # Phase 3: Client habit tasks
            elif task_type == 'log_habits':
                from services.flows.client_habit_flows import ClientHabitFlows
                handler = ClientHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_log_habits(phone, message, user_id, task)
            
            elif task_type == 'view_progress':
                from services.flows.client_habit_flows import ClientHabitFlows
                handler = ClientHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_view_progress(phone, message, user_id, task)
            
            elif task_type == 'weekly_report':
                from services.flows.client_habit_flows import ClientHabitFlows
                handler = ClientHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_weekly_report(phone, message, user_id, task)
            
            elif task_type == 'monthly_report':
                from services.flows.client_habit_flows import ClientHabitFlows
                handler = ClientHabitFlows(self.db, self.whatsapp, self.task_service)
                return handler.continue_monthly_report(phone, message, user_id, task)
            
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
            from services.ai_intent_handler_phase1 import AIIntentHandler  # Will be renamed to ai_intent_handler.py
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
