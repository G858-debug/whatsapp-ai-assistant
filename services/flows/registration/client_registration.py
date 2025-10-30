"""
Client Registration Handler
Handles client-specific registration flow
"""
from typing import Dict, List
from utils.logger import log_info, log_error


class ClientRegistrationHandler:
    """Handles client registration flow"""
    
    def __init__(self, db, whatsapp, reg_service, validator, message_builder, task_manager):
        self.db = db
        self.whatsapp = whatsapp
        self.reg = reg_service
        self.validator = validator
        self.message_builder = message_builder
        self.task_manager = task_manager
    
    def start_client_registration(self, phone: str, fields: List[Dict], task_id: str) -> Dict:
        """Start client registration flow"""
        try:
            # Send intro message
            intro_msg = (
                "🏃 *Client Registration*\n\n"
                f"Awesome! I'll ask you {len(fields)} questions to set up your fitness profile.\n\n"
                "💡 *Tip:* You can type /stop at any time to cancel.\n\n"
                "Let's get started! 👇"
            )
            self.whatsapp.send_message(phone, intro_msg)
            
            # Send first field prompt
            first_field = fields[0]
            self.whatsapp.send_message(phone, first_field['prompt'])
            
            return {
                'success': True,
                'response': first_field['prompt'],
                'handler': 'client_registration_started'
            }
            
        except Exception as e:
            log_error(f"Error starting client registration: {str(e)}")
            return {
                'success': False,
                'response': "Error starting client registration.",
                'handler': 'client_registration_start_error'
            }
    
    def continue_client_registration(self, phone: str, message: str, task: Dict) -> Dict:
        """Continue client registration flow"""
        try:
            fields = self.task_manager.get_task_data(task, 'fields', [])
            current_index = self.task_manager.get_task_data(task, 'current_field_index', 0)
            collected_data = self.task_manager.get_task_data(task, 'collected_data', {})
            
            # If we have a message to process (user response to a field)
            if message and current_index < len(fields):
                current_field = fields[current_index]
                
                # Validate the input
                is_valid, error_msg = self.validator.validate_field_value(current_field, message)
                
                if not is_valid:
                    error_response = self.message_builder.build_validation_error_message(
                        error_msg, current_field['prompt']
                    )
                    self.whatsapp.send_message(phone, error_response)
                    
                    return {
                        'success': True,
                        'response': error_response,
                        'handler': 'client_registration_validation_error'
                    }
                
                # Parse and store the value
                parsed_value = self.validator.parse_field_value(current_field, message)
                field_name = current_field['name']
                
                # Store in task data
                self.task_manager.store_field_data(task, 'client', field_name, parsed_value)
                collected_data[field_name] = parsed_value
                
                # Move to next field
                current_index += 1
            
            # Update current field index in database
            self.task_manager.update_flow_task(task, 'client', {
                'current_field_index': current_index,
                'collected_data': collected_data
            })
            
            # Check if we have more fields
            if current_index < len(fields):
                # Send next field prompt with progress
                next_field = fields[current_index]
                progress_msg = self.message_builder.build_progress_message(
                    current_index + 1, len(fields), next_field['prompt']
                )
                
                self.whatsapp.send_message(phone, progress_msg)
                
                return {
                    'success': True,
                    'response': progress_msg,
                    'handler': 'client_registration_next_field'
                }
            else:
                # All fields collected - complete registration
                from .completion_handler import RegistrationCompletionHandler
                completion_handler = RegistrationCompletionHandler(
                    self.db, self.whatsapp, None, self.reg, self.message_builder, self.task_manager
                )
                return completion_handler.complete_client_registration(phone, collected_data, task)
                
        except Exception as e:
            log_error(f"Error continuing client registration: {str(e)}")
            return {
                'success': False,
                'response': "Error during client registration.",
                'handler': 'client_registration_continue_error'
            }