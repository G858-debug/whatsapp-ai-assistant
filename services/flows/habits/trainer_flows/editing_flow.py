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
                # User provided habit_id (case-insensitive search)
                habit_id_input = message.strip()
                
                # Find habit by case-insensitive search
                habit_result = self.db.table('fitness_habits').select('*').ilike('habit_id', habit_id_input).eq('trainer_id', trainer_id).execute()
                
                if not habit_result.data:
                    error_msg = f"❌ Habit ID '{habit_id_input}' not found. Please check and try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'edit_habit_not_found'}
                
                habit = habit_result.data[0]
                habit_id = habit.get('habit_id')  # Use the actual habit_id from database
                
                # Show current habit info and ask what to edit
                info_msg = (
                    f"✏️ *Edit Habit*\n\n"
                    f"*Current Details:*\n"
                    f"• Name: {habit.get('habit_name')}\n"
                    f"• Description: {habit.get('description') or 'None'}\n"
                    f"• Target: {habit.get('target_value')} {habit.get('unit')}\n"
                    f"• Frequency: {habit.get('frequency')}\n\n"
                    f"What would you like to edit?\n\n"
                    f"*Options:*\n"
                    f"1️⃣ *Name* - Change habit name\n"
                    f"2️⃣ *Description* - Update description\n"
                    f"3️⃣ *Target* - Change target value\n"
                    f"4️⃣ *Unit* - Change unit of measurement\n"
                    f"5️⃣ *Frequency* - Change frequency\n"
                    f"6️⃣ *All* - Edit all fields\n\n"
                    f"💡 *Examples:*\n"
                    f"• Single: `1` (edit name only)\n"
                    f"• Multiple: `1,3,2` (edit name, target, description)\n"
                    f"• All: `6` (edit everything)\n\n"
                    f"Type /stop to cancel."
                )
                self.whatsapp.send_message(phone, info_msg)
                
                # Load fields for later use
                with open('config/habit_creation_inputs.json', 'r') as f:
                    config = json.load(f)
                    task_data['fields'] = config['fields']
                
                task_data['habit_id'] = habit_id
                task_data['habit'] = habit
                task_data['updates'] = {}
                task_data['step'] = 'choose_field'
                
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': info_msg, 'handler': 'edit_habit_choose_field'}
            
            elif step == 'choose_field':
                # User chose what to edit
                choice = message.strip()
                fields = task_data['fields']
                habit = task_data.get('habit', {})
                
                field_map = {
                    '1': 0,  # Name
                    '2': 1,  # Description  
                    '3': 2,  # Target
                    '4': 3,  # Unit
                    '5': 4,  # Frequency
                    '6': [0, 1, 2, 3, 4]  # All
                }
                
                # Handle multiple selections like "1,3,2" or single selection
                if choice == '6':
                    # All fields
                    fields_to_edit = [0, 1, 2, 3, 4]
                else:
                    # Parse multiple selections (comma or space separated)
                    selected_numbers = []
                    for num in choice.replace(',', ' ').split():
                        num = num.strip()
                        if num in ['1', '2', '3', '4', '5']:
                            selected_numbers.append(num)
                    
                    if not selected_numbers:
                        msg = "❌ Please choose valid options (1-6). You can select multiple like: 1,3,2 or type /stop to cancel."
                        self.whatsapp.send_message(phone, msg)
                        return {'success': True, 'response': msg, 'handler': 'edit_habit_invalid_choice'}
                    
                    # Convert to field indices and preserve order
                    fields_to_edit = [field_map[num] for num in selected_numbers]
                
                # Set fields to edit
                task_data['fields_to_edit'] = fields_to_edit
                task_data['current_field_index'] = 0
                task_data['step'] = 'editing'
                
                # Ask first field
                field_index = task_data['fields_to_edit'][0]
                current_field = fields[field_index]
                prompt = f"*{current_field['label']}*\n\nCurrent: {habit.get(current_field['name'])}\n\n{current_field['prompt']}\n\nType 'skip' to keep current value."
                self.whatsapp.send_message(phone, prompt)
                
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': prompt, 'handler': 'edit_habit_started'}
            
            elif step == 'editing':
                fields = task_data['fields']
                fields_to_edit = task_data.get('fields_to_edit', [])
                current_index = task_data.get('current_field_index', 0)
                updates = task_data.get('updates', {})
                habit = task_data.get('habit', {})
                
                # Process current answer
                field_index = fields_to_edit[current_index]
                current_field = fields[field_index]
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
                
                # Check if done with selected fields
                if current_index >= len(fields_to_edit):
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
                next_field_index = fields_to_edit[current_index]
                next_field = fields[next_field_index]
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
                # User provided habit_id (case-insensitive search)
                habit_id_input = message.strip()
                
                # Find habit by case-insensitive search
                habit_result = self.db.table('fitness_habits').select('*').ilike('habit_id', habit_id_input).eq('trainer_id', trainer_id).execute()
                
                if not habit_result.data:
                    error_msg = f"❌ Habit ID '{habit_id_input}' not found. Please check and try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'delete_habit_not_found'}
                
                habit = habit_result.data[0]
                habit_id = habit.get('habit_id')  # Use the actual habit_id from database
                
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