"""
Client Relationship Invitation Commands
Handles trainer invitation and removal
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_invite_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /invite-trainer command"""
    try:
        # Create invite_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='invite_trainer',
            task_data={'step': 'ask_trainer_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the invitation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'invite_trainer_task_error'}
        
        # Ask for trainer ID
        msg = (
            "👥 *Invite Trainer*\n\n"
            "Please provide the trainer ID you want to invite.\n\n"
            "💡 Use /search-trainer to find trainers first.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'invite_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in invite trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'invite_trainer_error'
        }


def handle_remove_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /remove-trainer command"""
    try:
        # Create remove_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='remove_trainer',
            task_data={'step': 'ask_trainer_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainer_task_error'}
        
        # Ask for trainer ID
        msg = (
            "🗑️ *Remove Trainer*\n\n"
            "Please provide the trainer ID you want to remove.\n\n"
            "⚠️ This will remove them from your trainer list and delete all habit assignments from them.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'remove_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in remove trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'remove_trainer_error'
        }