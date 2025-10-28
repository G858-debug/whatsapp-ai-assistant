"""
Account Deletion Handler
Handles account deletion flow logic
"""
from typing import Dict
from utils.logger import log_info, log_error


class AccountDeletionHandler:
    """Handles account deletion flows"""
    
    def __init__(self, db, whatsapp, message_builder, task_manager):
        self.db = db
        self.whatsapp = whatsapp
        self.message_builder = message_builder
        self.task_manager = task_manager
    
    def continue_delete_account(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue account deletion flow"""
        try:
            msg_lower = message.lower().strip()
            
            # Check for cancellation
            if msg_lower in ['cancel', 'no', 'stop']:
                msg = self.message_builder.build_cancellation_message("Account Deletion")
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task_manager.stop_flow_task(task, role)
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_cancelled'
                }
            
            # Check for confirmation
            if msg_lower == 'yes delete':
                return self._execute_account_deletion(phone, role, user_id, task)
            
            # Invalid response
            msg = (
                "❌ Invalid response.\n\n"
                "Please reply with:\n"
                "• 'YES DELETE' to confirm deletion\n"
                "• 'CANCEL' to cancel"
            )
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'delete_account_invalid_response'
            }
            
        except Exception as e:
            log_error(f"Error continuing account deletion: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "account deletion",
                "Your account is safe"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'delete_account_continue_error'
            }
    
    def _execute_account_deletion(self, phone: str, role: str, user_id: str, task: Dict) -> Dict:
        """Execute account deletion"""
        try:
            log_info(f"Executing account deletion for {phone} ({role})")
            
            # Import auth service
            from services.auth import AuthenticationService
            auth_service = AuthenticationService(self.db)
            
            # Delete role data (this handles all cleanup)
            success = auth_service.delete_user_role(phone, role)
            
            if success:
                # Check if user has other role
                roles = auth_service.get_user_roles(phone)
                other_role = 'client' if role == 'trainer' else 'trainer'
                
                if roles[other_role]:
                    # User still has other role
                    msg = (
                        f"✅ *{role.title()} Account Deleted*\n\n"
                        f"Your {role} account has been permanently deleted.\n\n"
                        f"Your {other_role} account is still active.\n\n"
                        f"Type /help to see what you can do as a {other_role}."
                    )
                else:
                    # User completely deleted
                    msg = (
                        "✅ *Account Deleted*\n\n"
                        "Your account has been permanently deleted.\n\n"
                        "Thank you for using Refiloe. You're welcome back anytime!\n\n"
                        "To register again, just send me a message."
                    )
                
                self.whatsapp.send_message(phone, msg)
                
                # Complete task
                self.task_manager.complete_flow_task(task, role)
                
                log_info(f"Account deletion completed for {phone}")
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_success'
                }
            else:
                # Deletion failed
                msg = self.message_builder.build_error_message(
                    "account deletion",
                    "Please try again"
                )
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task_manager.stop_flow_task(task, role)
                
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'delete_account_failed'
                }
                
        except Exception as e:
            log_error(f"Error executing account deletion: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message
            error_msg = (
                "❌ *Deletion Failed*\n\n"
                "Sorry, I encountered an error deleting your account.\n\n"
                "Your account is still active. Please try again or contact support."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'delete_account_execute_error'
            }