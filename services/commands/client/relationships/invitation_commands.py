"""
Client Relationship Invitation Commands
Handles trainer invitation and removal
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_invite_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /invite-trainer command with trainer browse dashboard"""
    try:
        # Create invite_trainer task - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='invite_trainer',
            task_data={
                'step': 'ask_trainer_id',
                'client_id': client_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the invitation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'invite_trainer_task_error'}
        
        # Generate trainer browse dashboard
        from services.commands.dashboard import generate_trainer_browse_dashboard
        dashboard_result = generate_trainer_browse_dashboard(phone, client_id, db, whatsapp)
        
        # Send invitation instructions
        msg = (
            "👥 *Invite Trainer*\n\n"
            "Please provide the Trainer ID you want to invite.\n\n"
            "💡 *Tip:* Use the dashboard link above to browse all available trainers and copy their ID\n\n"
            "You can also provide a phone number if you know it.\n\n"
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
    """Handle /remove-trainer command - Dashboard link with ID request"""
    try:
        # Create task for removal flow - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='remove_trainer',
            task_data={
                'step': 'ask_trainer_id',
                'client_id': client_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainer_task_error'}
        
        # Generate dashboard link for browsing trainers
        from services.dashboard import DashboardTokenManager
        import os
        
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(client_id, 'client', 'remove_trainer')
        
        dashboard_url = ""
        if token:
            base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
            dashboard_url = f"{base_url}/dashboard/{client_id}/{token}"
        
        # Ask for trainer ID with dashboard link
        msg = (
            "🗑️ *Remove Trainer*\n\n"
            "Please provide the Trainer ID you want to remove.\n\n"
        )
        
        if dashboard_url:
            msg += (
                f"💡 *Browse your trainers here:*\n"
                f"🔗 {dashboard_url}\n\n"
                f"📋 *Steps:* Find the trainer → Copy their ID → Return here with the ID\n\n"
            )
        else:
            msg += "💡 *Tip:* Use /view-trainers to see your trainer list first\n\n"
        
        msg += (
            "⚠️ *Warning:* This will remove them from your trainer list and delete all habit assignments from them.\n\n"
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