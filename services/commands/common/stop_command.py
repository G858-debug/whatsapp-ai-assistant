"""
Stop Command Handler - Phase 1
Handles stopping current task
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_stop(phone: str, auth_service, task_service, whatsapp) -> Dict:
    """Handle stop command"""
    try:
        # Get current login status
        login_status = auth_service.get_login_status(phone)
        
        # Try to find running task - check both with user_id and phone
        running_task = None
        
        if login_status:
            # User is logged in - get user ID
            user_id = auth_service.get_user_id_by_role(phone, login_status)
            
            if user_id:
                # Check for task with user_id
                running_task = task_service.get_running_task(user_id, login_status)
        
        # If no task found with user_id, check with phone (for registration tasks)
        if not running_task:
            # Check trainer tasks with phone
            trainer_task = task_service.get_running_task(phone, 'trainer')
            if trainer_task:
                running_task = trainer_task
                login_status = 'trainer'
            else:
                # Check client tasks with phone
                client_task = task_service.get_running_task(phone, 'client')
                if client_task:
                    running_task = client_task
                    login_status = 'client'
        
        if not running_task:
            msg = (
                "✅ You don't have any active tasks to stop.\n\n"
                "Type /help to see what you can do."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'stop_no_task'
            }
        
        # Stop the task
        task_type = running_task.get('task_type', 'task')
        task_type_display = task_type.replace('_', ' ').title()
        success = task_service.stop_task(running_task['id'], login_status)
        
        if success:
            msg = (
                f"✅ *Task Stopped!*\n\n"
                f"I've cancelled your *{task_type_display}* task.\n\n"
                f"What would you like to do next?"
            )
            whatsapp.send_message(phone, msg)
            
            log_info(f"Stopped {task_type} task for {phone}")
            
            return {
                'success': True,
                'response': msg,
                'handler': 'stop_success'
            }
        else:
            msg = "❌ Failed to stop task. Please try again."
            whatsapp.send_message(phone, msg)
            
            return {
                'success': False,
                'response': msg,
                'handler': 'stop_failed'
            }
            
    except Exception as e:
        log_error(f"Error in stop command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error stopping the task.",
            'handler': 'stop_error'
        }