"""
Trainer Habit Editing Flow
Handles trainer editing and deleting existing habits
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.habits.habit_service import HabitService
import json


class EditingFlow:
    """Handles habit editing and deletion flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.habit_service = HabitService(db)
    
    def continue_edit_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle edit habit flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_habit_id')
            
            if step == 'ask_habit_id':
                # User provided habit_id
                habit_id = message.strip().upper()
                
                # Get habit details
                success, msg, habit = self.habit_service.get_habit_by_id(habit_id)
                
                if not success or not habit:
                    error_msg = f"❌ Habit ID '{habit_id}' not found. Please check and try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'edit_habit_not_found'}
                
                # Verify ownership
                if habit.get('trainer_id') != trainer_id:
                    error_msg = "❌ You don't have permission to edit this habit."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'edit_habit_no_permission'}
                
                # Show current habit info
                info_msg = (
                    f"✏️ *Edit Habit*\n\n"
                    f"*Current Details:*\n"
                    f"• Name: {habit.get('habit_name')}\n"
                    f"• Description: {habit.get('description') or 'None'}\n"
                    f"• Target: {habit.get('target_value')} {habit.get('unit')}\n"
                    f"• Frequency: {habit.get('frequency')}\n\n"
                    f"I'll ask you about each field. Type 'skip' to keep current value.\n\n"
                    f"Let's start! 👇"
                )
                self.whatsapp.send_message(phone, info_msg)
                
                # Load fields and start editing
                with open('config/habit_creation_inputs.json', 'r') as f:
                    config = json.load(f)
                    task_data['fields'] = config['fields']
                
                task_data['habit_id'] = habit_id
                task_data['habit'] = habit
                task_data['current_field_index'] = 0
                task_data['updates'] = {}
                task_data['step'] = 'editing'
                
                # Ask first field
                first_field = task_data['fields'][0]
                prompt = f"*{first_field['label']}*\n\nCurrent: {habit.get(first_field['name'])}\n\n{first_field['prompt']}\n\nType 'skip' to keep current value."
                self.whatsapp.send_message(phone, prompt)
                
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': prompt, 'handler': 'edit_habit_started'}
            
            elif step == 'editing':
                fields = task_data['fields']
                current_index = task_data.get('current_field_index', 0)
                updates = task_data.get('updates', {})
                habit = task_data.get('habit', {})
                
                # Process current answer
                current_field = fields[current_index]
                field_name = current_field['name']
                
                if message.strip().lower() != 'skip':
                    # Validate and store update
                    if current_field['type'] == 'number':
                        try:
                            updates[field_name] = float(message.strip())
                        except ValueError:
                            msg = "❌ Please enter a valid number or 'skip'."
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'edit_habit_invalid'}
                    elif current_field['type'] == 'choice':
                        options = [opt['value'] for opt in current_field.get('options', [])]
                        if message.strip().lower() not in options:
                            msg = f"❌ Please choose from: {', '.join(options)} or 'skip'"
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'edit_habit_invalid'}
                        updates[field_name] = message.strip().lower()
                    else:
                        updates[field_name] = message.strip()
                
                task_data['updates'] = updates
                current_index += 1
                task_data['current_field_index'] = current_index
                
                # Check if done
                if current_index >= len(fields):
                    # Apply updates
                    if not updates:
                        msg = "ℹ️ No changes made. Habit remains unchanged."
                        self.whatsapp.send_message(phone, msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': msg, 'handler': 'edit_habit_no_changes'}
                    
                    success, msg = self.habit_service.update_habit(
                        task_data['habit_id'], trainer_id, updates
                    )
                    
                    if success:
                        response_msg = f"✅ Habit updated successfully!\n\n*Updated fields:*\n"
                        for key, value in updates.items():
                            response_msg += f"• {key}: {value}\n"
                        self.whatsapp.send_message(phone, response_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': response_msg, 'handler': 'edit_habit_success'}
                    else:
                        error_msg = f"❌ Failed to update habit: {msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': error_msg, 'handler': 'edit_habit_failed'}
                
                # Ask next field
                next_field = fields[current_index]
                prompt = f"*{next_field['label']}*\n\nCurrent: {habit.get(next_field['name'])}\n\n{next_field['prompt']}\n\nType 'skip' to keep current value."
                self.whatsapp.send_message(phone, prompt)
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': prompt, 'handler': 'edit_habit_continue'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'edit_habit'}
            
        except Exception as e:
            log_error(f"Error in edit habit flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while editing the habit.\n\n"
                "The task has been cancelled. Please try again with /edit-habit"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'edit_habit_error'}   
 
    def continue_delete_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle delete habit flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_habit_id')
            
            if step == 'ask_habit_id':
                # User provided habit_id
                habit_id = message.strip().upper()
                
                # Get habit details
                success, msg, habit = self.habit_service.get_habit_by_id(habit_id)
                
                if not success or not habit:
                    error_msg = f"❌ Habit ID '{habit_id}' not found. Please check and try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'delete_habit_not_found'}
                
                # Verify ownership
                if habit.get('trainer_id') != trainer_id:
                    error_msg = "❌ You don't have permission to delete this habit."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'delete_habit_no_permission'}
                
                # Get assignment count
                assignment_count = self.habit_service.get_habit_assignment_count(habit_id)
                
                # Ask confirmation
                confirm_msg = (
                    f"⚠️ *Confirm Deletion*\n\n"
                    f"*Habit:* {habit.get('habit_name')}\n"
                    f"*ID:* {habit_id}\n"
                    f"*Assigned to:* {assignment_count} client(s)\n\n"
                    f"This will:\n"
                    f"• Remove the habit from all assigned clients\n"
                    f"• Delete all habit logs\n"
                    f"• This action cannot be undone\n\n"
                    f"Reply *YES* to confirm deletion, or *NO* to cancel."
                )
                self.whatsapp.send_message(phone, confirm_msg)
                
                task_data['habit_id'] = habit_id
                task_data['step'] = 'confirm'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': confirm_msg, 'handler': 'delete_habit_confirm'}
            
            elif step == 'confirm':
                response = message.strip().lower()
                
                if response == 'yes':
                    # Delete habit
                    success, msg = self.habit_service.delete_habit(task_data['habit_id'], trainer_id)
                    
                    if success:
                        response_msg = "✅ Habit deleted successfully!"
                        self.whatsapp.send_message(phone, response_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': response_msg, 'handler': 'delete_habit_success'}
                    else:
                        error_msg = f"❌ Failed to delete habit: {msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': error_msg, 'handler': 'delete_habit_failed'}
                
                elif response == 'no':
                    msg = "✅ Deletion cancelled. Habit remains unchanged."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'delete_habit_cancelled'}
                
                else:
                    msg = "Please reply *YES* to confirm or *NO* to cancel."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'delete_habit_invalid_response'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'delete_habit'}
            
        except Exception as e:
            log_error(f"Error in delete habit flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while deleting the habit.\n\n"
                "The task has been cancelled. Please try again with /delete-habit"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'delete_habit_error'}