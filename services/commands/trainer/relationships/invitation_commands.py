"""
Trainer Relationship Invitation Commands
Handles client invitation and creation
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_invite_client(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /invite-trainee command"""
    try:
        # Create invite_trainee task - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='invite_trainee',
            task_data={
                'step': 'ask_client_id',
                'trainer_id': trainer_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the invitation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'invite_trainee_task_error'}
        
        # Ask for client ID or phone number
        msg = (
            "👥 *Invite Existing Client*\n\n"
            "Please provide the client ID or phone number you want to invite.\n\n"
            "The client must already be registered in the system.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'invite_trainee_started'
        }
        
    except Exception as e:
        log_error(f"Error in invite trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'invite_trainee_error'
        }


def handle_create_client(phone: str, trainer_id: str, db, whatsapp, reg_service, task_service) -> Dict:
    """Handle /create-trainee command - now asks to create or link"""
    try:
        # Create task to ask for choice - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='create_trainee',
            task_data={
                'step': 'ask_create_or_link',
                'trainer_id': trainer_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'create_trainee_task_error'}
        
        # Ask if they want to create new or link existing
        msg = (
            "👥 *Add Client*\n\n"
            "How would you like to add a client?\n\n"
            "1️⃣ *Create New* - Create a new client account and send them an invitation to accept\n\n"
            "2️⃣ *Link Existing* - Link with a client who's already registered (you'll need their Client ID or phone number)\n\n"
            "💡 *Tip:* Type /stop to cancel\n\n"
            "Reply with *1* or *2*"
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'create_trainee_started'
        }
        
    except Exception as e:
        log_error(f"Error in create trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'create_trainee_error'
        }