"""
Stop Command Handler - Phase 1
Handles stopping current task
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_stop(phone: str, auth_service, task_service, whatsapp) -> Dict:
    """Enhanced stop command - handles infinite loops and stuck situations"""
    try:
        log_info(f"Stop command initiated by {phone}")
        
        # Get current login status
        login_status = auth_service.get_login_status(phone)
        stopped_tasks = []
        
        # PHASE 1: Try to find and stop tasks using normal methods
        if login_status:
            user_id = auth_service.get_user_id_by_role(phone, login_status)
            if user_id:
                # Check for task with phone (task operations use phone as identifier)
                running_task = task_service.get_running_task(phone, login_status)
                if running_task:
                    task_type = running_task.get('task_type', 'unknown')
                    # Use complete_task instead of stop_task for cleaner closure
                    if task_service.complete_task(running_task['id'], login_status):
                        stopped_tasks.append(f"{task_type} ({login_status})")
                        log_info(f"Completed {task_type} task for {phone}")
        
        # PHASE 2: Check for registration tasks (using phone as ID)
        for role in ['trainer', 'client']:
            reg_task = task_service.get_running_task(phone, role)
            if reg_task and reg_task.get('task_type') == 'registration':
                if task_service.complete_task(reg_task['id'], role):
                    stopped_tasks.append(f"registration ({role})")
                    log_info(f"Completed registration task for {phone} as {role}")
        
        # PHASE 3: Comprehensive cleanup - stop ALL running tasks for this user
        # This handles edge cases and stuck situations
        try:
            if login_status:
                user_id = auth_service.get_user_id_by_role(phone, login_status)
                if user_id:
                    # Force stop all running tasks for this user (use phone for task identification)
                    cleanup_result = task_service.stop_all_running_tasks(phone, login_status)
                    if cleanup_result:
                        log_info(f"Force cleanup completed for {phone}")
        except Exception as cleanup_error:
            log_error(f"Cleanup error for {phone}: {str(cleanup_error)}")
        
        # PHASE 4: Nuclear option - direct database cleanup for stuck situations
        try:
            from datetime import datetime
            import pytz
            
            sa_tz = pytz.timezone('Africa/Johannesburg')
            now = datetime.now(sa_tz).isoformat()
            
            # Get database client
            db = task_service.db
            
            # Update any running tasks for this phone to completed
            # This handles cases where tasks are stuck in running state
            
            # For logged-in users
            if login_status and user_id:
                table = 'trainer_tasks' if login_status == 'trainer' else 'client_tasks'
                id_column = 'trainer_id' if login_status == 'trainer' else 'client_id'
                
                stuck_tasks = db.table(table).select('id, task_type').eq(
                    id_column, user_id
                ).eq('task_status', 'running').execute()
                
                if stuck_tasks.data:
                    for task in stuck_tasks.data:
                        db.table(table).update({
                            'task_status': 'completed',
                            'completed_at': now,
                            'updated_at': now
                        }).eq('id', task['id']).execute()
                        
                        stopped_tasks.append(f"stuck_{task.get('task_type', 'unknown')}")
                        log_info(f"Force completed stuck task {task['id']} for {phone}")
            
            # For registration tasks (using phone as ID)
            for role in ['trainer', 'client']:
                table = f'{role}_tasks'
                id_column = f'{role}_id'
                
                try:
                    stuck_reg_tasks = db.table(table).select('id, task_type').eq(
                        id_column, phone
                    ).eq('task_status', 'running').execute()
                    
                    if stuck_reg_tasks.data:
                        for task in stuck_reg_tasks.data:
                            db.table(table).update({
                                'task_status': 'completed',
                                'completed_at': now,
                                'updated_at': now
                            }).eq('id', task['id']).execute()
                            
                            stopped_tasks.append(f"stuck_registration_{role}")
                            log_info(f"Force completed stuck registration task {task['id']} for {phone}")
                except Exception as role_cleanup_error:
                    log_error(f"Role cleanup error for {phone} as {role}: {str(role_cleanup_error)}")
                    
        except Exception as nuclear_error:
            log_error(f"Nuclear cleanup error for {phone}: {str(nuclear_error)}")
        
        # PHASE 5: Send appropriate response
        if stopped_tasks:
            task_list = ", ".join(stopped_tasks)
            msg = (
                f"✅ *All Tasks Stopped!*\n\n"
                f"I've cancelled the following tasks:\n"
                f"• {task_list}\n\n"
                f"You're now free to start fresh! 🎉\n\n"
                f"What would you like to do next?"
            )
            whatsapp.send_message(phone, msg)
            
            log_info(f"Successfully stopped {len(stopped_tasks)} tasks for {phone}: {task_list}")
            
            return {
                'success': True,
                'response': msg,
                'handler': 'stop_success_multiple'
            }
        else:
            msg = (
                "✅ *System Clean!*\n\n"
                "You don't have any active tasks to stop.\n\n"
                "Everything looks good! Type /help to see what you can do."
            )
            whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'stop_no_task'
            }
            
    except Exception as e:
        log_error(f"Critical error in stop command for {phone}: {str(e)}")
        
        # Last resort - always send a helpful message even if everything fails
        try:
            msg = (
                "🔧 *Emergency Stop*\n\n"
                "I encountered an error but I've done my best to clear any stuck tasks.\n\n"
                "If you're still having issues, try:\n"
                "• Wait 30 seconds and try again\n"
                "• Type /help for available commands\n"
                "• Contact support if problems persist"
            )
            whatsapp.send_message(phone, msg)
        except Exception as final_error:
            log_error(f"Final fallback failed for {phone}: {str(final_error)}")
        
        return {
            'success': False,
            'response': "Emergency stop attempted - check if issues persist",
            'handler': 'stop_emergency'
        }