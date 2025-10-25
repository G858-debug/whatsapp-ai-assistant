"""
Profile Flow Handler - Phase 1
Handles profile editing and account deletion flows
"""
from typing import Dict
from utils.logger import log_info, log_error


class ProfileFlowHandler:
    """Handles profile management conversation flows"""
    
    def __init__(self, db, whatsapp, reg_service, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.reg = reg_service
        self.task = task_service
    
    def continue_edit_profile(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue profile editing flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'editing_fields')
            
            # Get all fields
            fields = self.reg.get_registration_fields(role)
            
            # Step 1: Handle field selection
            if step == 'selecting_fields':
                return self._handle_field_selection(phone, message, role, user_id, task, fields)
            
            # Step 2: Handle field editing
            selected_fields = task_data.get('selected_fields', [])
            current_index = task_data.get('current_field_index', 0)
            updates = task_data.get('updates', {})
            
            if current_index >= len(selected_fields):
                # All selected fields processed
                return self._apply_profile_updates(phone, role, user_id, updates, task)
            
            # Get current field from selected fields
            field_index = selected_fields[current_index]
            current_field = fields[field_index]
            
            # Validate the new value
            is_valid, error_msg = self.reg.validate_field_value(current_field, message)
            
            if not is_valid:
                # Send error and ask again
                error_response = f"❌ {error_msg}\n\nPlease try again."
                self.whatsapp.send_message(phone, error_response)
                
                return {
                    'success': True,
                    'response': error_response,
                    'handler': 'edit_profile_validation_error'
                }
            
            # Parse and store the update
            parsed_value = self.reg.parse_field_value(current_field, message)
            updates[current_field['name']] = parsed_value
            
            # Move to next selected field
            current_index += 1
            
            # Update task
            self.task.update_task(
                task_id=task['id'],
                role=role,
                task_data={
                    'step': 'editing_fields',
                    'selected_fields': selected_fields,
                    'current_field_index': current_index,
                    'updates': updates,
                    'role': role
                }
            )
            
            # Send next selected field
            return self._send_next_selected_field(phone, role, user_id, fields, selected_fields, current_index, task)
                
        except Exception as e:
            log_error(f"Error continuing profile edit: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Type /stop to cancel.",
                'handler': 'edit_profile_continue_error'
            }

    
    def _handle_field_selection(self, phone: str, message: str, role: str, user_id: str, task: Dict, fields: list) -> Dict:
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
            self.task.update_task(
                task_id=task['id'],
                role=role,
                task_data={
                    'step': 'editing_fields',
                    'selected_fields': selected_indices,
                    'current_field_index': 0,
                    'updates': {},
                    'role': role
                }
            )
            
            # Send first selected field
            return self._send_next_selected_field(phone, role, user_id, fields, selected_indices, 0, task)
            
        except Exception as e:
            log_error(f"Error handling field selection: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Please try again.",
                'handler': 'edit_profile_selection_error'
            }
    
    def _send_next_selected_field(self, phone: str, role: str, user_id: str, fields: list, selected_indices: list, current_index: int, task: Dict) -> Dict:
        """Send next selected field for editing"""
        try:
            if current_index >= len(selected_indices):
                # All selected fields processed
                return self._apply_profile_updates(phone, role, user_id, task.get('task_data', {}).get('updates', {}), task)
            
            field_index = selected_indices[current_index]
            field = fields[field_index]
            
            # Get current value from database
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            current_data = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            current_value = "Not set"
            if current_data.data:
                field_value = current_data.data[0].get(field['name'])
                if field_value:
                    if isinstance(field_value, list):
                        current_value = ', '.join(str(v) for v in field_value)
                    else:
                        current_value = str(field_value)
            
            # Show progress
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
            return {
                'success': False,
                'response': "Sorry, I encountered an error.",
                'handler': 'edit_profile_next_field_error'
            }
    
    def _send_next_edit_field(self, phone: str, role: str, user_id: str, fields: list, index: int, task: Dict) -> Dict:
        """Send next field for editing"""
        try:
            next_field = fields[index]
            
            # Get current value from database
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            current_data = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            current_value = "Not set"
            if current_data.data:
                field_value = current_data.data[0].get(next_field['name'])
                if field_value:
                    if isinstance(field_value, list):
                        current_value = ', '.join(str(v) for v in field_value)
                    else:
                        current_value = str(field_value)
            
            # Show progress
            progress_msg = f"✅ Updated! ({index}/{len(fields)})\n\n"
            
            field_msg = (
                f"{progress_msg}"
                f"*{next_field['label']}*\n"
                f"Current: {current_value}\n\n"
                f"{next_field['prompt']}\n\n"
                f"(Type 'skip' to keep current value)"
            )
            
            self.whatsapp.send_message(phone, field_msg)
            
            return {
                'success': True,
                'response': field_msg,
                'handler': 'edit_profile_next_field'
            }
            
        except Exception as e:
            log_error(f"Error sending next edit field: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error.",
                'handler': 'edit_profile_next_field_error'
            }
    
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
                self.task.complete_task(task['id'], role)
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'edit_profile_no_changes'
                }
            
            # Apply updates to database
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            # Add updated_at timestamp
            from datetime import datetime
            import pytz
            sa_tz = pytz.timezone('Africa/Johannesburg')
            updates['updated_at'] = datetime.now(sa_tz).isoformat()
            
            result = self.db.table(table).update(updates).eq(id_column, user_id).execute()
            
            if result.data:
                # Success
                update_count = len([k for k in updates.keys() if k != 'updated_at'])
                
                msg = (
                    f"✅ *Profile Updated!*\n\n"
                    f"I've updated {update_count} field{'s' if update_count > 1 else ''}.\n\n"
                    f"Click the button below to see your updated information."
                )
                
                # Send message with View Profile button
                buttons = [{'id': '/view-profile', 'title': '👤 View Profile'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
                # Complete task
                self.task.complete_task(task['id'], role)
                
                log_info(f"Profile updated for {phone}: {list(updates.keys())}")
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'edit_profile_success'
                }
            else:
                # Failed
                msg = (
                    "❌ Failed to update your profile.\n\n"
                    "Please try again or contact support."
                )
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task.stop_task(task['id'], role)
                
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'edit_profile_failed'
                }
                
        except Exception as e:
            log_error(f"Error applying profile updates: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error updating your profile.",
                'handler': 'edit_profile_apply_error'
            }
    
    def continue_delete_account(self, phone: str, message: str, role: str, user_id: str, task: Dict) -> Dict:
        """Continue account deletion flow"""
        try:
            msg_lower = message.lower().strip()
            
            # Check for cancellation
            if msg_lower in ['cancel', 'no', 'stop']:
                msg = (
                    "✅ Account deletion cancelled.\n\n"
                    "Your account is safe. Type /help to see what you can do."
                )
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task.stop_task(task['id'], role)
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_cancelled'
                }
            
            # Check for confirmation
            if msg_lower == 'yes delete':
                return self._execute_account_deletion(phone, role, user_id, task)
            
            # Invalid response
            msg = (
                "❌ Invalid response.\n\n"
                "Please reply with:\n"
                "• 'YES DELETE' to confirm deletion\n"
                "• 'CANCEL' to cancel"
            )
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'delete_account_invalid_response'
            }
            
        except Exception as e:
            log_error(f"Error continuing account deletion: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error. Type /stop to cancel.",
                'handler': 'delete_account_continue_error'
            }

    
    def _execute_account_deletion(self, phone: str, role: str, user_id: str, task: Dict) -> Dict:
        """Execute account deletion"""
        try:
            log_info(f"Executing account deletion for {phone} ({role})")
            
            # Import auth service
            from services.auth import AuthenticationService
            auth_service = AuthenticationService(self.db)
            
            # Delete role data (this handles all cleanup)
            success = auth_service.delete_user_role(phone, role)
            
            if success:
                # Check if user has other role
                roles = auth_service.get_user_roles(phone)
                other_role = 'client' if role == 'trainer' else 'trainer'
                
                if roles[other_role]:
                    # User still has other role
                    msg = (
                        f"✅ *{role.title()} Account Deleted*\n\n"
                        f"Your {role} account has been permanently deleted.\n\n"
                        f"Your {other_role} account is still active.\n\n"
                        f"Type /help to see what you can do as a {other_role}."
                    )
                else:
                    # User completely deleted
                    msg = (
                        "✅ *Account Deleted*\n\n"
                        "Your account has been permanently deleted.\n\n"
                        "Thank you for using Refiloe. You're welcome back anytime!\n\n"
                        "To register again, just send me a message."
                    )
                
                self.whatsapp.send_message(phone, msg)
                
                # Complete task
                self.task.complete_task(task['id'], role)
                
                log_info(f"Account deletion completed for {phone}")
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'delete_account_success'
                }
            else:
                # Deletion failed
                msg = (
                    "❌ Account deletion failed.\n\n"
                    "Please try again or contact support."
                )
                self.whatsapp.send_message(phone, msg)
                
                # Stop task
                self.task.stop_task(task['id'], role)
                
                return {
                    'success': False,
                    'response': msg,
                    'handler': 'delete_account_failed'
                }
                
        except Exception as e:
            log_error(f"Error executing account deletion: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error deleting your account.",
                'handler': 'delete_account_execute_error'
            }
