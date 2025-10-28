"""
Client Habit Logging Flow
Handles client logging their habit progress
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.habits.assignment_service import AssignmentService
from services.habits.logging_service import LoggingService


class LoggingFlow:
    """Handles habit logging flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.assignment_service = AssignmentService(db)
        self.logging_service = LoggingService(db)
    
    def continue_log_habits(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle log habits flow"""
        try:
            task_data = task.get('task_data', {})
            habits = task_data.get('habits', [])
            current_index = task_data.get('current_habit_index', 0)
            logged_values = task_data.get('logged_values', {})
            
            # Validate and store current value
            if current_index > 0:
                current_habit = habits[current_index - 1]
                habit_id = current_habit['habit_id']
                
                try:
                    value = float(message.strip())
                    
                    if value < 0:
                        msg = "❌ Value cannot be negative. Please enter a valid number."
                        self.whatsapp.send_message(phone, msg)
                        return {'success': True, 'response': msg, 'handler': 'log_habits_invalid'}
                    
                    # Log the habit
                    success, log_msg, log_data = self.logging_service.log_habit(
                        client_id, habit_id, value
                    )
                    
                    if not success:
                        error_msg = f"❌ Failed to log habit: {log_msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        return {'success': True, 'response': error_msg, 'handler': 'log_habits_failed'}
                    
                    logged_values[habit_id] = value
                    task_data['logged_values'] = logged_values
                    
                except ValueError:
                    msg = "❌ Please enter a valid number."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'log_habits_invalid'}
            
            # Check if all habits logged
            if current_index >= len(habits):
                # Calculate and show summary
                success, msg, progress_list = self.logging_service.calculate_daily_progress(client_id)
                
                if success and progress_list:
                    summary_msg = "✅ *All Habits Logged!*\n\n📊 *Today's Progress:*\n\n"
                    
                    for progress in progress_list:
                        summary_msg += f"*{progress['habit_name']}*\n"
                        summary_msg += f"   Completed: {progress['completed']}/{progress['target']} {progress['unit']}\n"
                        summary_msg += f"   Progress: {progress['percentage']}%\n"
                        
                        if progress['percentage'] >= 100:
                            summary_msg += "   🎉 Target achieved!\n"
                        elif progress['percentage'] >= 75:
                            summary_msg += "   💪 Almost there!\n"
                        elif progress['percentage'] >= 50:
                            summary_msg += "   👍 Good progress!\n"
                        
                        summary_msg += "\n"
                    
                    summary_msg += "💡 You can log again later if needed!"
                    
                    self.whatsapp.send_message(phone, summary_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': summary_msg, 'handler': 'log_habits_complete'}
                else:
                    simple_msg = "✅ All habits logged successfully!"
                    self.whatsapp.send_message(phone, simple_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': simple_msg, 'handler': 'log_habits_complete'}
            
            # Ask for next habit
            next_habit = habits[current_index]
            habit_msg = (
                f"*{current_index + 1}/{len(habits)}: {next_habit['habit_name']}*\n\n"
                f"Target: {next_habit['target_value']} {next_habit['unit']}\n\n"
                f"How much did you complete?\n"
                f"(Enter a number)"
            )
            self.whatsapp.send_message(phone, habit_msg)
            
            task_data['current_habit_index'] = current_index + 1
            self.task_service.update_task(task['id'], 'client', task_data)
            
            return {'success': True, 'response': habit_msg, 'handler': 'log_habits_continue'}
            
        except Exception as e:
            log_error(f"Error in log habits flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error logging habits', 'handler': 'log_habits_error'}