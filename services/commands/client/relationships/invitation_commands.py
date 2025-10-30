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
        
        # Ask for trainer ID or phone number
        msg = (
            "👥 *Invite Trainer*\n\n"
            "Please provide the trainer ID or phone number you want to invite.\n\n"
            "Use /search-trainer to find trainers first.\n\n"
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
    """Handle /remove-trainer command - Guide to dashboard first"""
    try:
        from services.commands.dashboard import generate_dashboard_link
        
        # Generate dashboard link for browsing trainers
        dashboard_result = generate_dashboard_link(phone, client_id, 'client', db, whatsapp, 'remove_trainer')
        
        if dashboard_result['success']:
            # Add additional instructions for removal
            additional_msg = (
                "\n\n🗑️ *To Remove a Trainer:*\n"
                "1. Browse your trainers using the link above\n"
                "2. Find the trainer you want to remove\n"
                "3. Copy their Trainer ID\n"
                "4. Come back to WhatsApp and type: `/remove-trainer [TRAINER_ID]`\n\n"
                "⚠️ *Warning:* This will remove them from your list and delete all habit assignments from them.\n\n"
                "Type /stop to cancel anytime."
            )
            
            # Send the additional instructions
            whatsapp.send_message(phone, additional_msg)
            
            return {
                'success': True,
                'response': dashboard_result['response'] + additional_msg,
                'handler': 'remove_trainer_dashboard_sent'
            }
        
        # Fallback to direct ID request if dashboard fails
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
        
        # Ask for trainer ID directly
        msg = (
            "🗑️ *Remove Trainer*\n\n"
            "Please provide the trainer ID you want to remove.\n\n"
            "💡 *Tip:* Use /view-trainers to see your trainer list and get their IDs.\n\n"
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