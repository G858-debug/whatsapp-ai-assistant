"""
Trainer Habit Flow Handlers - Phase 3
Handles multi-step flows for trainer habit management
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.habit_service import HabitService
from services.habits.assignment_service import AssignmentService
from services.habits.logging_service import LoggingService
from services.habits.report_service import ReportService
from services.relationships.relationship_service import RelationshipService
import json
import os
import tempfile


class TrainerHabitFlows:
    """Handles trainer habit flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.habit_service = HabitService(db)
        self.assignment_service = AssignmentService(db)
        self.logging_service = LoggingService(db)
        self.report_service = ReportService(db)
        self.relationship_service = RelationshipService(db)
    
    def continue_create_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle create habit flow"""
        try:
            task_data = task.get('task_data', {})
            collected_data = task_data.get('collected_data', {})
            
            # Load habit creation fields if not loaded
            if not task_data.get('fields'):
                with open('config/habit_creation_inputs.json', 'r') as f:
                    config = json.load(f)
                    task_data['fields'] = config['fields']
                    task_data['current_field_index'] = 0
            
            fields = task_data['fields']
            current_index = task_data.get('current_field_index', 0)
            
            # Validate and store current answer
            if current_index > 0:
                current_field = fields[current_index - 1]
                field_name = current_field['name']
                
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
                
                task_data['collected_data'] = collected_data
                task_data['current_field_index'] = current_index
            
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
            
            # Send prompt with options if it's a choice field
            if next_field['type'] == 'choice':
                prompt = next_field['prompt'] + "\n\n"
                for opt in next_field.get('options', []):
                    prompt += f"• *{opt['label']}* - {opt['description']}\n"
                prompt += f"\nReply with: {', '.join([opt['value'] for opt in next_field['options']])}"
            else:
                prompt = next_field['prompt']
            
            self.whatsapp.send_message(phone, prompt)
            task_data['current_field_index'] = current_index + 1
            self.task_service.update_task(task['id'], 'trainer', task_data)
            
            return {'success': True, 'response': prompt, 'handler': 'create_habit_continue'}
            
        except Exception as e:
            log_error(f"Error in create habit flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error creating habit', 'handler': 'create_habit_error'}
    
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
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error editing habit', 'handler': 'edit_habit_error'}
    
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
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error deleting habit', 'handler': 'delete_habit_error'}

    def continue_assign_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle assign habit flow"""
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
                    return {'success': True, 'response': error_msg, 'handler': 'assign_habit_not_found'}
                
                # Verify ownership
                if habit.get('trainer_id') != trainer_id:
                    error_msg = "❌ You don't have permission to assign this habit."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'assign_habit_no_permission'}
                
                # Show habit details
                info_msg = (
                    f"📌 *Assign Habit*\n\n"
                    f"*Habit:* {habit.get('habit_name')}\n"
                    f"*Target:* {habit.get('target_value')} {habit.get('unit')}\n"
                    f"*Frequency:* {habit.get('frequency')}\n\n"
                    f"Now, provide the client ID(s) to assign this habit.\n\n"
                    f"💡 You can provide:\n"
                    f"• Single ID: CLI123\n"
                    f"• Multiple IDs: CLI123, CLI456, CLI789\n\n"
                    f"Use /view-trainees to see your clients."
                )
                self.whatsapp.send_message(phone, info_msg)
                
                task_data['habit_id'] = habit_id
                task_data['habit'] = habit
                task_data['step'] = 'ask_client_ids'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': info_msg, 'handler': 'assign_habit_ask_clients'}
            
            elif step == 'ask_client_ids':
                # Parse client IDs
                client_ids_raw = message.strip().upper()
                client_ids = [cid.strip() for cid in client_ids_raw.replace(',', ' ').split()]
                
                if not client_ids:
                    msg = "❌ Please provide at least one client ID."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'assign_habit_no_ids'}
                
                # Verify clients are in trainer's list
                valid_clients = []
                invalid_clients = []
                
                for client_id in client_ids:
                    if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                        valid_clients.append(client_id)
                    else:
                        invalid_clients.append(client_id)
                
                if not valid_clients:
                    msg = "❌ None of the provided client IDs are in your client list."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'assign_habit_no_valid_clients'}
                
                # Assign habit
                success, msg, results = self.assignment_service.assign_habit(
                    task_data['habit_id'], valid_clients, trainer_id
                )
                
                # Build response
                response_msg = f"📌 *Assignment Results*\n\n"
                
                if results['assigned']:
                    response_msg += f"✅ Assigned to {len(results['assigned'])} client(s)\n"
                
                if results['already_assigned']:
                    response_msg += f"ℹ️ {len(results['already_assigned'])} already had this habit\n"
                
                if invalid_clients:
                    response_msg += f"❌ {len(invalid_clients)} not in your client list\n"
                
                response_msg += f"\n*Habit:* {task_data['habit'].get('habit_name')}"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'trainer')
                return {'success': True, 'response': response_msg, 'handler': 'assign_habit_complete'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'assign_habit'}
            
        except Exception as e:
            log_error(f"Error in assign habit flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error assigning habit', 'handler': 'assign_habit_error'}
    
    def continue_view_trainee_progress(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle view trainee progress flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id
                client_id = message.strip().upper()
                
                # Verify client is in trainer's list
                if not self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    error_msg = f"❌ Client ID '{client_id}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'view_trainee_progress_not_found'}
                
                # Ask for date
                date_msg = (
                    f"📊 *View Client Progress*\n\n"
                    f"Which date would you like to see?\n\n"
                    f"*Options:*\n"
                    f"• Type 'today' for today's progress\n"
                    f"• Type 'yesterday' for yesterday\n"
                    f"• Or enter a date (YYYY-MM-DD format)\n\n"
                    f"Example: 2024-01-15"
                )
                self.whatsapp.send_message(phone, date_msg)
                
                task_data['client_id'] = client_id
                task_data['step'] = 'ask_date'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': date_msg, 'handler': 'view_trainee_progress_ask_date'}
            
            elif step == 'ask_date':
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
                    return {'success': True, 'response': msg, 'handler': 'view_trainee_progress_invalid_date'}
                
                # Get progress
                success, msg, progress_list = self.logging_service.calculate_daily_progress(
                    task_data['client_id'], target_date
                )
                
                if not success:
                    error_msg = f"❌ Error calculating progress: {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'view_trainee_progress_error'}
                
                if not progress_list:
                    no_data_msg = f"📊 No progress data for {target_date.strftime('%Y-%m-%d')}"
                    self.whatsapp.send_message(phone, no_data_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': no_data_msg, 'handler': 'view_trainee_progress_no_data'}
                
                # Format progress
                response_msg = f"📊 *Client Progress*\n\n"
                response_msg += f"*Date:* {target_date.strftime('%Y-%m-%d')}\n"
                response_msg += f"*Client ID:* {task_data['client_id']}\n\n"
                
                for i, progress in enumerate(progress_list, 1):
                    response_msg += f"*{i}. {progress['habit_name']}*\n"
                    response_msg += f"   Target: {progress['target']} {progress['unit']}\n"
                    response_msg += f"   Completed: {progress['completed']} {progress['unit']}\n"
                    response_msg += f"   Due: {progress['due']} {progress['unit']}\n"
                    response_msg += f"   Progress: {progress['percentage']}%\n"
                    response_msg += f"   Logs: {progress['log_count']}\n\n"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'trainer')
                return {'success': True, 'response': response_msg, 'handler': 'view_trainee_progress_success'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'view_trainee_progress'}
            
        except Exception as e:
            log_error(f"Error in view trainee progress flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error viewing progress', 'handler': 'view_trainee_progress_error'}
    
    def continue_trainee_report(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle trainee report flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            report_type = task_data.get('report_type', 'weekly')
            
            if step == 'ask_client_id':
                # User provided client_id
                client_id = message.strip().upper()
                
                # Verify client is in trainer's list
                if not self.relationship_service.check_relationship_exists(trainer_id, client_id):
                    error_msg = f"❌ Client ID '{client_id}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'trainee_report_not_found'}
                
                # Ask for period
                if report_type == 'weekly':
                    period_msg = (
                        f"📈 *Weekly Report*\n\n"
                        f"Which week would you like to see?\n\n"
                        f"*Options:*\n"
                        f"• Type 'this week' for current week\n"
                        f"• Type 'last week' for previous week\n"
                        f"• Or enter week start date (YYYY-MM-DD)\n\n"
                        f"Example: 2024-01-15"
                    )
                else:
                    period_msg = (
                        f"📈 *Monthly Report*\n\n"
                        f"Which month would you like to see?\n\n"
                        f"*Options:*\n"
                        f"• Type 'this month' for current month\n"
                        f"• Type 'last month' for previous month\n"
                        f"• Or enter month and year (MM-YYYY)\n\n"
                        f"Example: 01-2024 for January 2024"
                    )
                
                self.whatsapp.send_message(phone, period_msg)
                
                task_data['client_id'] = client_id
                task_data['step'] = 'ask_period'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': period_msg, 'handler': 'trainee_report_ask_period'}
            
            elif step == 'ask_period':
                period_input = message.strip().lower()
                
                try:
                    if report_type == 'weekly':
                        # Parse week
                        if period_input == 'this week':
                            week_start = date.today() - timedelta(days=date.today().weekday())
                        elif period_input == 'last week':
                            week_start = date.today() - timedelta(days=date.today().weekday() + 7)
                        else:
                            week_start = datetime.strptime(message.strip(), '%Y-%m-%d').date()
                        
                        # Generate report
                        success, msg, csv_content = self.report_service.generate_trainer_report(
                            trainer_id, task_data['client_id'], week_start, week_start + timedelta(days=6)
                        )
                        
                        report_name = f"weekly_report_{task_data['client_id']}_{week_start.strftime('%Y%m%d')}.csv"
                    
                    else:  # monthly
                        # Parse month
                        if period_input == 'this month':
                            target_month = date.today().month
                            target_year = date.today().year
                        elif period_input == 'last month':
                            last_month = date.today().replace(day=1) - timedelta(days=1)
                            target_month = last_month.month
                            target_year = last_month.year
                        else:
                            parts = message.strip().split('-')
                            target_month = int(parts[0])
                            target_year = int(parts[1])
                        
                        # Generate report
                        from calendar import monthrange
                        month_start = date(target_year, target_month, 1)
                        last_day = monthrange(target_year, target_month)[1]
                        month_end = date(target_year, target_month, last_day)
                        
                        success, msg, csv_content = self.report_service.generate_trainer_report(
                            trainer_id, task_data['client_id'], month_start, month_end
                        )
                        
                        report_name = f"monthly_report_{task_data['client_id']}_{target_year}{target_month:02d}.csv"
                
                except (ValueError, IndexError):
                    msg = "❌ Invalid format. Please follow the examples provided."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'trainee_report_invalid_period'}
                
                if not success or not csv_content:
                    error_msg = f"❌ {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'trainee_report_failed'}
                
                # Save and send CSV
                try:
                    from services.helpers.supabase_storage import SupabaseStorageHelper
                    
                    temp_dir = tempfile.gettempdir()
                    filepath = os.path.join(temp_dir, report_name)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    storage_helper = SupabaseStorageHelper(self.db)
                    public_url = storage_helper.upload_csv(filepath, report_name)
                    
                    if public_url:
                        result = self.whatsapp.send_document(
                            phone, public_url, filename=report_name,
                            caption=f"📈 {report_type.capitalize()} Report for {task_data['client_id']}"
                        )
                        
                        if result.get('success'):
                            response_msg = "✅ Report generated and sent!"
                            self.whatsapp.send_message(phone, response_msg)
                            
                            try:
                                os.remove(filepath)
                            except:
                                pass
                            
                            self.task_service.complete_task(task['id'], 'trainer')
                            return {'success': True, 'response': response_msg, 'handler': 'trainee_report_sent'}
                    
                    raise Exception("Failed to send report")
                
                except Exception as e:
                    log_error(f"Error sending report: {str(e)}")
                    error_msg = "❌ Failed to send report. Please try again."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'trainee_report_send_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'trainee_report'}
            
        except Exception as e:
            log_error(f"Error in trainee report flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'trainer')
            return {'success': False, 'response': 'Error generating report', 'handler': 'trainee_report_error'}
