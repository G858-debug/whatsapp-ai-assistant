"""
Profile Edit Handler
Handles profile editing flow logic
"""
from typing import Dict, List
from utils.logger import log_info, log_error


class ProfileEditHandler:
    """Handles profile editing flows"""
    
    def __init__(self, db, whatsapp, reg_service, validator, message_builder, task_manager):
        self.db = db
        self.whatsapp = whatsapp
        self.reg = reg_service
        self.validator = validator
        self.message_builder = message_builder
        self.task_manager = task_manager
    
    def continue_edit_profile(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue profile editing flow"""
        try:
            step = self.task_manager.get_task_data(task, 'step', 'editing_fields')
            
            # Get all fields
            fields = self.reg.get_registration_fields(role)
            
            # Step 1: Handle field selection
            if step == 'selecting_fields':
                return self._handle_field_selection(phone, message, role, user_id, task, fields)
            
            # Step 2: Handle field editing
            return self._handle_field_editing(phone, message, role, user_id, task, fields)
                
        except Exception as e:
            log_error(f"Error continuing profile edit: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "profile editing", 
                "/edit-profile"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'edit_profile_continue_error'
            }
    
    def _handle_field_selection(self, phone: str, message: str, role: str, user_id: str, task: Dict, fields: List[Dict]) -> Dict:
        """Handle field selection step"""
        try:
            msg_lower = message.lower().strip()
            
            # Parse field selection
            selected_indices = []
            
            if msg_lower == 'all':
                # Select all fields
                selected_indices = list(range(len(fields)))
            else:
                # Parse comma-separated numbers
                try:
                    parts = [p.strip() for p in message.split(',')]
                    for part in parts:
                        num = int(part)
                        if 1 <= num <= len(fields):
                            selected_indices.append(num - 1)  # Convert to 0-based index
                        else:
                            raise ValueError(f"Number {num} is out of range")
                except ValueError as e:
                    # Invalid input
                    msg = (
                        f"❌ Invalid selection: {str(e)}\n\n"
                        f"Please enter numbers between 1 and {len(fields)}, separated by commas.\n"
                        f"Example: 1,3,5 or type 'all' to edit all fields."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {
                        'success': True,
                        'response': msg,
                        'handler': 'edit_profile_invalid_selection'
                    }
            
            if not selected_indices:
                msg = (
                    "❌ No fields selected.\n\n"
                    "Please enter at least one field number or type /stop to cancel."
                )
                self.whatsapp.send_message(phone, msg)
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'edit_profile_no_selection'
                }
            
            # Remove duplicates and sort
            selected_indices = sorted(list(set(selected_indices)))
            
            # Update task with selected fields
            self.task_manager.update_flow_task(task, role, {
                'step': 'editing_fields',
                'selected_fields': selected_indices,
                'current_field_index': 0,
                'updates': {}
            })
            
            # Send first selected field
            return self._send_next_selected_field(phone, role, user_id, fields, selected_indices, 0, task)
            
        except Exception as e:
            log_error(f"Error handling field selection: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "field selection",
                "/edit-profile"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'edit_profile_selection_error'
            }
    
    def _handle_field_editing(self, phone: str, message: str, role: str, user_id: str, task: Dict, fields: List[Dict]) -> Dict:
        """Handle field editing step"""
        try:
            selected_fields = self.task_manager.get_task_data(task, 'selected_fields', [])
            current_index = self.task_manager.get_task_data(task, 'current_field_index', 0)
            updates = self.task_manager.get_task_data(task, 'updates', {})
            
            if current_index >= len(selected_fields):
                # All selected fields processed
                return self._apply_profile_updates(phone, role, user_id, updates, task)
            
            # Get current field from selected fields
            field_index = selected_fields[current_index]
            current_field = fields[field_index]
            
            # Validate the new value
            is_valid, error_msg = self.validator.validate_field_value(current_field, message)
            
            if not is_valid:
                # Send error and ask again
                error_response = self.message_builder.build_validation_error_message(
                    error_msg, current_field['prompt']
                )
                self.whatsapp.send_message(phone, error_response)
                
                return {
                    'success': True,
                    'response': error_response,
                    'handler': 'edit_profile_validation_error'
                }
            
            # Parse and store the update
            parsed_value = self.validator.parse_field_value(current_field, message)
            updates[current_field['name']] = parsed_value
            
            # Move to next selected field
            current_index += 1
            
            # Update task
            self.task_manager.update_flow_task(task, role, {
                'step': 'editing_fields',
                'selected_fields': selected_fields,
                'current_field_index': current_index,
                'updates': updates
            })
            
            # Send next selected field
            return self._send_next_selected_field(phone, role, user_id, fields, selected_fields, current_index, task)
            
        except Exception as e:
            log_error(f"Error handling field editing: {str(e)}")
            return {
                'success': False,
                'response': 'Error during field editing.',
                'handler': 'edit_profile_field_error'
            }
    
    def _send_next_selected_field(self, phone: str, role: str, user_id: str, fields: List[Dict], 
                                 selected_indices: List[int], current_index: int, task: Dict) -> Dict:
        """Send next selected field for editing"""
        try:
            if current_index >= len(selected_indices):
                # All selected fields processed
                updates = self.task_manager.get_task_data(task, 'updates', {})
                return self._apply_profile_updates(phone, role, user_id, updates, task)
            
            field_index = selected_indices[current_index]
            field = fields[field_index]
            
            # Get current value from database
            current_value = self._get_current_field_value(role, user_id, field['name'])
            
            # Show progress and field prompt
            progress_msg = f"✅ Field {current_index + 1} of {len(selected_indices)}\n\n"
            
            field_msg = (
                f"{progress_msg}"
                f"*{field['label']}*\n"
                f"Current: {current_value}\n\n"
                f"{field['prompt']}"
            )
            
            self.whatsapp.send_message(phone, field_msg)
            
            return {
                'success': True,
                'response': field_msg,
                'handler': 'edit_profile_next_field'
            }
            
        except Exception as e:
            log_error(f"Error sending next selected field: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message
            error_msg = self.message_builder.build_error_message(
                "profile editing",
                "/edit-profile"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'edit_profile_next_field_error'
            }
    
    def _get_current_field_value(self, role: str, user_id: str, field_name: str) -> str:
        """Get current field value from database"""
        try:
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            result = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            if result.data:
                # Map config field name to database column name
                db_column = self.reg.map_field_to_db_column(field_name, role)
                field_value = result.data[0].get(db_column)
                
                if field_value:
                    if isinstance(field_value, list):
                        return ', '.join(str(v) for v in field_value)
                    elif isinstance(field_value, str) and field_value.startswith('['):
                        # Handle string representation of list
                        import ast
                        try:
                            field_list = ast.literal_eval(field_value)
                            if isinstance(field_list, list):
                                return ', '.join(str(v) for v in field_list)
                        except:
                            pass
                    return str(field_value)
            
            return "Not set"
            
        except Exception as e:
            log_error(f"Error getting current field value: {str(e)}")
            return "Not set"
    
    def _apply_profile_updates(self, phone: str, role: str, user_id: str, updates: Dict, task: Dict) -> Dict:
        """Apply profile updates to database"""
        try:
            if not updates:
                # No updates made
                msg = (
                    "No changes were made to your profile.\n\n"
                    "Click the button below to see your current information."
                )
                
                # Send message with View Profile button
                buttons = [{'id': '/view-profile', 'title': '👤 View Profile'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
                # Complete task
                self.task_manager.complete_flow_task(task, role)
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'edit_profile_no_changes'
                }
            
            # Map config field names to database column names
            mapped_updates = {}
            for field_name, value in updates.items():
                db_column = self.reg.map_field_to_db_column(field_name, role)
                mapped_updates[db_column] = value
                
                # Handle duplicate fields for trainers to maintain consistency
                if role == 'trainer':
                    if field_name == 'city':
                        # Also update location field
                        mapped_updates['location'] = value
                    elif field_name == 'location':
                        # Also update city field (reverse mapping)
                        mapped_updates['city'] = value
                    elif field_name == 'experience_years':
                        # Also update years_experience field (convert to number)
                        mapped_updates['years_experience'] = self._parse_experience_to_number(value)
                    elif field_name == 'years_experience':
                        # This shouldn't happen in normal flow, but handle it for completeness
                        # Try to reverse map the number back to text
                        mapped_updates['experience_years'] = self._number_to_experience_text(value)
            
            # Apply updates to database
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            # Add updated_at timestamp
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            mapped_updates['updated_at'] = datetime.now(sa_tz).isoformat()
            
            result = self.db.table(table).update(mapped_updates).eq(id_column, user_id).execute()
            
            if result.data:
                # Success
                update_count = len([k for k in updates.keys() if k != 'updated_at'])
                
                msg = self.message_builder.build_completion_message(
                    "Profile Update",
                    f"I've updated {update_count} field{'s' if update_count > 1 else ''}."
                )
                
                # Send message with View Profile button
                buttons = [{'id': '/view-profile', 'title': '👤 View Profile'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
                # Complete task
                self.task_manager.complete_flow_task(task, role)
                
                log_info(f"Profile updated for {phone}: {list(updates.keys())}")
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'edit_profile_success'
                }
            else:
                # Failed
                msg = self.message_builder.build_error_message(
                    "profile update",
                    "Please try again"
                )
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task_manager.stop_flow_task(task, role)
                
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'edit_profile_failed'
                }
                
        except Exception as e:
            log_error(f"Error applying profile updates: {str(e)}")
            
            # Stop the task
            self.task_manager.stop_flow_task(task, role)
            
            # Send error message to user
            error_msg = self.message_builder.build_error_message(
                "profile update",
                "Please try again later"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {
                'success': False,
                'response': error_msg,
                'handler': 'edit_profile_apply_error'
            }
    
    def _parse_experience_to_number(self, experience_text: str) -> int:
        """Convert experience text to number for years_experience field"""
        if not experience_text:
            return 0
        
        experience_map = {
            '0-1 years': 1,
            '2-3 years': 3,
            '4-5 years': 5,
            '6-10 years': 8,
            '10+ years': 12
        }
        
        return experience_map.get(experience_text, 0)
    
    def _number_to_experience_text(self, years: int) -> str:
        """Convert years number back to experience text"""
        if not years or years == 0:
            return '0-1 years'
        
        # Reverse mapping from number to text
        if years <= 1:
            return '0-1 years'
        elif years <= 3:
            return '2-3 years'
        elif years <= 5:
            return '4-5 years'
        elif years <= 10:
            return '6-10 years'
        else:
            return '10+ years'