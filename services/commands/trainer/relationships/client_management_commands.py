"""
Trainer Client Management Commands
Handles adding clients via different input methods
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_add_client_command(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /add-client command - presents two clickable options for adding clients"""
    try:
        # Create task to track the add client flow - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='add_client_choice',
            task_data={
                'step': 'choose_input_method',
                'trainer_id': trainer_id
            }
        )

        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'add_client_task_error'}

        # Prepare message with friendly Refiloe tone
        msg = (
            "👥 *Add New Client*\n\n"
            "How would you like to add them?"
        )

        # Create interactive buttons
        buttons = [
            {'id': 'add_client_type', 'title': 'Type Details'},
            {'id': 'add_client_share', 'title': 'Share Contact'}
        ]

        # Send message with clickable buttons
        whatsapp.send_button_message(phone, msg, buttons)

        log_info(f"Add client command started for trainer {trainer_id} at {phone}")

        return {
            'success': True,
            'response': msg,
            'handler': 'add_client_started'
        }

    except Exception as e:
        log_error(f"Error in add client command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'add_client_error'
        }
