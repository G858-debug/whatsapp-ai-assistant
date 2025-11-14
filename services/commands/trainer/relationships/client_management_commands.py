"""
Trainer Client Management Commands
Handles adding clients via different input methods
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_add_client_command(phone: str, trainer_id: str, db, whatsapp, task_service, timeout_service=None) -> Dict:
    """Handle /add-client command - presents two clickable options for adding clients"""
    try:
        # Check if there's a resumable abandoned task
        if timeout_service:
            abandoned_task = timeout_service.get_resumable_task(
                phone=phone,
                role='trainer',
                task_type='add_client_choice'
            )

            if abandoned_task:
                return _offer_resume(phone, trainer_id, db, whatsapp, task_service, timeout_service, abandoned_task)

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

        # Check for abandoned tasks with pre-collected client information
        if timeout_service:
            abandoned_typing_task = timeout_service.get_resumable_task(
                phone=phone,
                role='trainer',
                task_type='add_client_typing'
            )

            if abandoned_typing_task:
                # Extract pre-collected data from abandoned task
                abandoned_task_data = abandoned_typing_task.get('task_data', {}).get('task_data', {})
                collected_data = abandoned_task_data.get('collected_data', {})

                # Check if there's any useful pre-collected data
                pre_collected = {}
                if collected_data.get('name'):
                    pre_collected['name'] = collected_data['name']
                if collected_data.get('phone'):
                    pre_collected['phone'] = collected_data['phone']
                if collected_data.get('email'):
                    pre_collected['email'] = collected_data['email']

                # Store pre-collected data in the new task if any was found
                if pre_collected:
                    task_service.update_task(
                        task_id=task_id,
                        updates={
                            'task_data.pre_collected_data': pre_collected
                        }
                    )
                    log_info(f"Stored pre-collected data from abandoned task for trainer {trainer_id}: {list(pre_collected.keys())}")

                    # Mark the abandoned task as superseded
                    timeout_service.cancel_timeout(abandoned_typing_task['id'])

        # Get trainer's name from database
        trainer_name = None
        try:
            trainer = db.trainers.find_one(
                {'trainer_id': trainer_id},
                {'name': 1, 'first_name': 1}
            )
            if trainer:
                trainer_name = trainer.get('name') or trainer.get('first_name')
        except Exception as e:
            log_error(f"Error fetching trainer name: {str(e)}")

        # Prepare message with friendly Refiloe tone
        # Use trainer_name if available, otherwise default to "there"
        if not trainer_name:
            trainer_name = "there"

        msg = (
            f"Perfect! Let's add your new client, {trainer_name}! 💪\n\n"
            "Would you like to:\n"
            "1️⃣ Type in their contact details manually\n"
            "2️⃣ Share their contact from your phone"
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


def _offer_resume(phone: str, trainer_id: str, db, whatsapp, task_service, timeout_service, abandoned_task: Dict) -> Dict:
    """Offer to resume an abandoned add-client task"""
    try:
        # Get client name from abandoned task data if available
        task_data = abandoned_task.get('task_data', {}).get('task_data', {})
        collected_data = task_data.get('collected_data', {})
        client_name = collected_data.get('name', 'your client')

        msg = (
            f"🔄 *Resume Previous Session?*\n\n"
            f"You were adding {client_name}.\n\n"
            f"Would you like to:"
        )

        buttons = [
            {'id': 'resume_add_client', 'title': f'Resume {client_name}'},
            {'id': 'start_fresh_add_client', 'title': 'Start Fresh'}
        ]

        whatsapp.send_button_message(phone, msg, buttons)

        log_info(f"Offered resume to trainer {trainer_id} for abandoned task {abandoned_task['id']}")

        return {
            'success': True,
            'response': msg,
            'handler': 'add_client_resume_offered'
        }

    except Exception as e:
        log_error(f"Error offering resume: {str(e)}")
        # Fall back to normal flow
        return handle_add_client_command(phone, trainer_id, db, whatsapp, task_service, timeout_service=None)
