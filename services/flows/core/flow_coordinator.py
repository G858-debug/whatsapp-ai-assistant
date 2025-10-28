"""
Flow Coordinator Base Class
Provides common functionality for all conversation flows
"""
from typing import Dict, Any, Optional
from utils.logger import log_info, log_error


class FlowCoordinator:
    """Base class for all flow coordinators"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
    
    def handle_flow_error(self, phone: str, task: Dict, error: Exception, 
                         role: str, error_context: str) -> Dict:
        """Handle flow errors consistently"""
        try:
            log_error(f"Error in {error_context}: {str(error)}")
            
            # Stop the task if it exists
            if task and task.get('id'):
                self.task_service.stop_task(task['id'], role)
            
            # Send error message
            error_msg = (
                f"❌ *Error Occurred*\n\n"
                f"Sorry, I encountered an error during {error_context}.\n\n"
                f"The process has been cancelled. Please try again."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': f'{error_context}_error'
            }
            
        except Exception as e:
            log_error(f"Error handling flow error: {str(e)}")
            return {
                'success': False,
                'response': "An unexpected error occurred.",
                'handler': 'flow_error_handler_error'
            }
    
    def send_progress_message(self, phone: str, current_step: int, total_steps: int, 
                            next_prompt: str) -> None:
        """Send progress message with next prompt"""
        try:
            if total_steps > 1:
                progress_msg = f"✅ Got it! ({current_step}/{total_steps})\n\n"
                full_msg = progress_msg + next_prompt
            else:
                full_msg = next_prompt
            
            self.whatsapp.send_message(phone, full_msg)
            
        except Exception as e:
            log_error(f"Error sending progress message: {str(e)}")
            # Fallback to just the prompt
            self.whatsapp.send_message(phone, next_prompt)
    
    def complete_flow(self, task: Dict, role: str, success_message: str, 
                     phone: str) -> Dict:
        """Complete a flow successfully"""
        try:
            # Complete the task
            if task and task.get('id'):
                self.task_service.complete_task(task['id'], role)
            
            # Send success message
            self.whatsapp.send_message(phone, success_message)
            
            return {
                'success': True,
                'response': success_message,
                'handler': 'flow_complete'
            }
            
        except Exception as e:
            log_error(f"Error completing flow: {str(e)}")
            return {
                'success': False,
                'response': "Process completed but encountered an error.",
                'handler': 'flow_complete_error'
            }
    
    def update_task_data(self, task: Dict, role: str, updates: Dict) -> bool:
        """Update task data safely"""
        try:
            if not task or not task.get('id'):
                return False
            
            current_data = task.get('task_data', {})
            current_data.update(updates)
            
            return self.task_service.update_task(
                task_id=task['id'],
                role=role,
                task_data=current_data
            )
            
        except Exception as e:
            log_error(f"Error updating task data: {str(e)}")
            return False
    
    def get_task_data(self, task: Dict, key: str, default: Any = None) -> Any:
        """Get task data safely"""
        try:
            return task.get('task_data', {}).get(key, default)
        except Exception:
            return default