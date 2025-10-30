"""
Registration Completion Handler
Handles completion of registration process and database saving
"""
from typing import Dict
from utils.logger import log_info, log_error


class RegistrationCompletionHandler:
    """Handles registration completion and database operations"""
    
    def __init__(self, db, whatsapp, auth_service, reg_service, message_builder, task_manager):
        self.db = db
        self.whatsapp = whatsapp
        self.auth = auth_service
        self.reg = reg_service
        self.message_builder = message_builder
        self.task_manager = task_manager
    
    def complete_trainer_registration(self, phone: str, data: Dict, task: Dict) -> Dict:
        """Complete trainer registration and save to database"""
        try:
            log_info(f"Completing trainer registration for {phone}")
            
            # Save trainer registration
            success, message, user_id = self.reg.save_trainer_registration(phone, data)
            
            if success:
                # Complete the task
                self.task_manager.complete_flow_task(task, 'trainer')
                
                # Send success message
                self.whatsapp.send_message(phone, message)
                
                # Send welcome message with available commands
                welcome_msg = self.message_builder.build_welcome_message('trainer', user_id, data.get('first_name'))
                self.whatsapp.send_message(phone, welcome_msg)
                
                return {
                    'success': True,
                    'response': message,
                    'handler': 'trainer_registration_complete'
                }
            else:
                # Registration failed
                error_msg = self.message_builder.build_error_message(
                    f"Trainer registration failed: {message}",
                    "Please try registering again"
                )
                self.whatsapp.send_message(phone, error_msg)
                
                # Stop the task
                self.task_manager.stop_flow_task(task, 'trainer')
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'trainer_registration_save_error'
                }
                
        except Exception as e:
            log_error(f"Error completing trainer registration: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, 'trainer')
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "trainer registration",
                "Please try registering again"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'trainer_registration_complete_error'
            }
    
    def complete_client_registration(self, phone: str, data: Dict, task: Dict) -> Dict:
        """Complete client registration and save to database"""
        try:
            log_info(f"Completing client registration for {phone}")
            
            # Check if this is trainer-created client
            task_data = task.get('task_data', {})
            created_by_trainer = task_data.get('created_by_trainer', False)
            trainer_id = task_data.get('trainer_id')
            
            # Save client registration
            success, message, user_id = self.reg.save_client_registration(
                phone, data, created_by_trainer, trainer_id
            )
            
            if success:
                # Complete the task
                self.task_manager.complete_flow_task(task, 'client')
                
                # Send success message to trainer (who initiated the registration)
                self.whatsapp.send_message(phone, message)
                
                # If created by trainer, don't send welcome message to trainer
                # The client will get their own welcome when they first contact the bot
                if not created_by_trainer:
                    # Send welcome message with available commands (for self-registration)
                    welcome_msg = self.message_builder.build_welcome_message('client', user_id, data.get('full_name'))
                    self.whatsapp.send_message(phone, welcome_msg)
                
                return {
                    'success': True,
                    'response': message,
                    'handler': 'client_registration_complete'
                }
            else:
                # Registration failed
                error_msg = self.message_builder.build_error_message(
                    f"Client registration failed: {message}",
                    "Please try registering again"
                )
                self.whatsapp.send_message(phone, error_msg)
                
                # Stop the task
                self.task_manager.stop_flow_task(task, 'client')
                
                return {
                    'success': False,
                    'response': error_msg,
                    'handler': 'client_registration_save_error'
                }
                
        except Exception as e:
            log_error(f"Error completing client registration: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, 'client')
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "client registration",
                "Please try registering again"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'client_registration_complete_error'
            }