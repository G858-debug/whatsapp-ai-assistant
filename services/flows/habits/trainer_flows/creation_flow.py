"""
Trainer Habit Creation Flow
Handles trainer creating new habits
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.habits.habit_service import HabitService
import json


class CreationFlow:
    """Handles habit creation flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.habit_service = HabitService(db)
    
    def continue_create_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create habit flow"""
        try:
            task_data = task.get('task_data', {})
            collected_data = task_data.get('collected_data', {})
            
            # Fields should already be loaded from command handler
            fields = task_data.get('fields', [])
            current_index = task_data.get('current_field_index', 0)
            first_question_sent = task_data.get('first_question_sent', False)
            
            # If fields are missing, load them (fallback)
            if not fields:
                with open('config/habit_creation_inputs.json', 'r') as f:
                    config = json.load(f)
                    fields = config['fields']
                    task_data['fields'] = fields
            
            # Debug logging
            log_info(f"Flow state - current_index: {current_index}, first_question_sent: {first_question_sent}, collected_data: {collected_data}")
            
            # Determine which field we're processing the answer for
            processing_field_index = None
            
            if first_question_sent and current_index == 0:
                # We sent the first question in the command, now processing its answer
                processing_field_index = 0
                task_data['first_question_sent'] = False  # Clear the flag
            elif current_index > 0:
                # We're processing an answer to a previously asked question
                processing_field_index = current_index - 1
            
            # Process the user's answer if we have a field to process
            if processing_field_index is not None:
                current_field = fields[processing_field_index]
                field_name = current_field['name']
                
                # Debug logging
                log_info(f"Processing answer for field {processing_field_index}: {field_name} (type: {current_field['type']}) with value: '{message}'")
                
                # Handle optional fields
                if not current_field.get('required') and message.strip().lower() in ['skip', 'no', 'none']:
                    collected_data[field_name] = None
                else:
                    # Validate based on field type
                    if current_field['type'] == 'number':
                        try:
                            value = float(message.strip())
                            validation = current_field.get('validation', {})
                            if 'min' in validation and value < validation['min']:
                                msg = f"❌ Value must be at least {validation['min']}. Please try again."
                                self.whatsapp.send_message(phone, msg)
                                return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                            if 'max' in validation and value > validation['max']:
                                msg = f"❌ Value must be at most {validation['max']}. Please try again."
                                self.whatsapp.send_message(phone, msg)
                                return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                            collected_data[field_name] = value
                        except ValueError:
                            msg = "❌ Please enter a valid number."
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                    
                    elif current_field['type'] == 'choice':
                        # Handle choice field
                        options = [opt['value'] for opt in current_field.get('options', [])]
                        if message.strip().lower() not in options:
                            msg = f"❌ Please choose from: {', '.join(options)}"
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                        collected_data[field_name] = message.strip().lower()
                    
                    else:
                        # Text field
                        validation = current_field.get('validation', {})
                        if 'min_length' in validation and len(message.strip()) < validation['min_length']:
                            msg = f"❌ Must be at least {validation['min_length']} characters."
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                        if 'max_length' in validation and len(message.strip()) > validation['max_length']:
                            msg = f"❌ Must be at most {validation['max_length']} characters."
                            self.whatsapp.send_message(phone, msg)
                            return {'success': True, 'response': msg, 'handler': 'create_habit_invalid'}
                        collected_data[field_name] = message.strip()
                
                # Store the collected data
                task_data['collected_data'] = collected_data
                
                # Move to next field (increment current_index to point to next field to ask)
                current_index = processing_field_index + 1
                task_data['current_field_index'] = current_index
                
                # Debug logging
                log_info(f"Stored answer for {field_name}. Next field index will be: {current_index}")
            
            # Check if we have all fields
            if current_index >= len(fields):
                # Create the habit
                success, msg, habit_id = self.habit_service.create_habit(trainer_id, collected_data)
                
                if success:
                    response_msg = (
                        f"✅ *Habit Created Successfully!*\n\n"
                        f"*Habit ID:* `{habit_id}`\n"
                        f"*Name:* {collected_data.get('habit_name')}\n"
                        f"*Target:* {collected_data.get('target_value')} {collected_data.get('unit')}\n"
                        f"*Frequency:* {collected_data.get('frequency')}\n\n"
                        f"💡 Use /assign-habit to assign this habit to your clients!"
                    )
                    self.whatsapp.send_message(phone, response_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': response_msg, 'handler': 'create_habit_success'}
                else:
                    error_msg = f"❌ Failed to create habit: {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'create_habit_failed'}
            
            # Ask next question
            next_field = fields[current_index]
            
            # Debug logging
            log_info(f"Asking question for field index {current_index}: {next_field['name']} (type: {next_field['type']})")
            
            # Send prompt with options if it's a choice field
            if next_field['type'] == 'choice':
                prompt = next_field['prompt'] + "\n\n"
                for opt in next_field.get('options', []):
                    prompt += f"• *{opt['label']}* - {opt['description']}\n"
                prompt += f"\nReply with: {', '.join([opt['value'] for opt in next_field['options']])}"
            else:
                prompt = next_field['prompt']
            
            self.whatsapp.send_message(phone, prompt)
            # Update task with current state
            self.task_service.update_task(task['id'], 'trainer', task_data)
            
            return {'success': True, 'response': prompt, 'handler': 'create_habit_continue'}
            
        except Exception as e:
            log_error(f"Error in create habit flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while creating the habit.\n\n"
                "The task has been cancelled. Please try again with /create-habit"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'create_habit_error'}