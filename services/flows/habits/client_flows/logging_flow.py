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
            waiting_for_habit_id = task_data.get('waiting_for_habit_id', False)
            waiting_for_value = task_data.get('waiting_for_value', False)
            current_habit_id = task_data.get('current_habit_id')
            logged_values = task_data.get('logged_values', {})
            
            # Step 1: Handle habit ID selection
            if waiting_for_habit_id:
                habit_id = message.strip().upper()
                
                # Find the habit in the list
                selected_habit = None
                for habit in habits:
                    if habit['habit_id'] == habit_id:
                        selected_habit = habit
                        break
                
                if not selected_habit:
                    # Invalid habit ID
                    valid_ids = [h['habit_id'] for h in habits]
                    error_msg = (
                        f"❌ Invalid habit ID: `{habit_id}`\n\n"
                        f"📋 *Your valid habit IDs:*\n"
                    )
                    for habit in habits:
                        error_msg += f"• `{habit['habit_id']}` - {habit['habit_name']}\n"
                    
                    error_msg += f"\n💡 Please send a valid habit ID or type /stop to cancel."
                    
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'log_habits_invalid_id'}
                
                # Valid habit ID - ask for value
                value_msg = (
                    f"✅ *Selected: {selected_habit['habit_name']}*\n\n"
                    f"🎯 Target: {selected_habit['target_value']} {selected_habit['unit']}\n\n"
                    f"📝 How much did you complete today?\n"
                    f"(Enter a number)"
                )
                
                # Update task to wait for value
                task_data['waiting_for_habit_id'] = False
                task_data['waiting_for_value'] = True
                task_data['current_habit_id'] = habit_id
                task_data['selected_habit'] = selected_habit
                self.task_service.update_task(task['id'], 'client', task_data)
                
                self.whatsapp.send_message(phone, value_msg)
                return {'success': True, 'response': value_msg, 'handler': 'log_habits_waiting_for_value'}
            
            # Step 2: Handle value input
            elif waiting_for_value:
                selected_habit = task_data.get('selected_habit')
                habit_id = current_habit_id
                
                try:
                    value = float(message.strip())
                    
                    if value < 0:
                        msg = "❌ Value cannot be negative. Please enter a valid number."
                        self.whatsapp.send_message(phone, msg)
                        return {'success': True, 'response': msg, 'handler': 'log_habits_invalid_value'}
                    
                    # Log the habit
                    success, log_msg, log_data = self.logging_service.log_habit(
                        client_id, habit_id, value
                    )
                    
                    if not success:
                        error_msg = f"❌ Failed to log habit: {log_msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        return {'success': True, 'response': error_msg, 'handler': 'log_habits_failed'}
                    
                    # Success message
                    success_msg = (
                        f"✅ *Habit Logged Successfully!*\n\n"
                        f"📊 *{selected_habit['habit_name']}*\n"
                        f"   Logged: {value} {selected_habit['unit']}\n"
                        f"   Target: {selected_habit['target_value']} {selected_habit['unit']}\n"
                        f"   Progress: {min(100, (value / selected_habit['target_value']) * 100):.1f}%\n\n"
                        f"🎉 Great job! Keep up the good work!\n\n"
                        f"💡 Want to log another habit? Use /log-habits again!"
                    )
                    
                    self.whatsapp.send_message(phone, success_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': success_msg, 'handler': 'log_habits_success'}
                    
                except ValueError:
                    msg = "❌ Please enter a valid number."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'log_habits_invalid_value'}
            
            # If we get here, something went wrong
            else:
                error_msg = "❌ Something went wrong. Please try /log-habits again."
                self.whatsapp.send_message(phone, error_msg)
                self.task_service.complete_task(task['id'], 'client')
                return {'success': False, 'response': error_msg, 'handler': 'log_habits_error'}
            
        except Exception as e:
            log_error(f"Error in log habits flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error logging habits', 'handler': 'log_habits_error'}