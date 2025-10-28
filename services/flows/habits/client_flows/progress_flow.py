"""
Client Habit Progress Flow
Handles client viewing their habit progress
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.logging_service import LoggingService


class ProgressFlow:
    """Handles habit progress viewing flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.logging_service = LoggingService(db)
    
    def continue_view_progress(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle view progress flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_date')
            
            if step == 'ask_date':
                # Parse date
                date_input = message.strip().lower()
                
                try:
                    if date_input == 'today':
                        target_date = date.today()
                    elif date_input == 'yesterday':
                        target_date = date.today() - timedelta(days=1)
                    else:
                        target_date = datetime.strptime(message.strip(), '%Y-%m-%d').date()
                except ValueError:
                    msg = "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15) or type 'today'/'yesterday'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'view_progress_invalid_date'}
                
                # Get progress
                success, msg, progress_list = self.logging_service.calculate_daily_progress(
                    client_id, target_date
                )
                
                if not success:
                    error_msg = f"❌ Error calculating progress: {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'view_progress_error'}
                
                if not progress_list:
                    no_data_msg = (
                        f"📊 *No Progress Data*\n\n"
                        f"No habits logged for {target_date.strftime('%Y-%m-%d')}.\n\n"
                        f"Use /log-habits to log your progress!"
                    )
                    self.whatsapp.send_message(phone, no_data_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': no_data_msg, 'handler': 'view_progress_no_data'}
                
                # Format progress
                response_msg = f"📊 *Your Progress*\n\n"
                response_msg += f"*Date:* {target_date.strftime('%A, %B %d, %Y')}\n\n"
                
                for i, progress in enumerate(progress_list, 1):
                    response_msg += f"*{i}. {progress['habit_name']}*\n"
                    response_msg += f"   Target: {progress['target']} {progress['unit']}\n"
                    response_msg += f"   Completed: {progress['completed']} {progress['unit']}\n"
                    response_msg += f"   Due: {progress['due']} {progress['unit']}\n"
                    response_msg += f"   Progress: {progress['percentage']}%\n"
                    
                    if progress['log_count'] > 1:
                        response_msg += f"   Logged {progress['log_count']} times\n"
                    
                    if progress['percentage'] >= 100:
                        response_msg += "   ✅ Target achieved!\n"
                    elif progress['percentage'] >= 75:
                        response_msg += "   💪 Almost there!\n"
                    elif progress['percentage'] >= 50:
                        response_msg += "   👍 Good progress!\n"
                    elif progress['percentage'] > 0:
                        response_msg += "   📈 Keep going!\n"
                    else:
                        response_msg += "   ⏳ Not started yet\n"
                    
                    response_msg += "\n"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'client')
                return {'success': True, 'response': response_msg, 'handler': 'view_progress_success'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'view_progress'}
            
        except Exception as e:
            log_error(f"Error in view progress flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error viewing progress', 'handler': 'view_progress_error'}