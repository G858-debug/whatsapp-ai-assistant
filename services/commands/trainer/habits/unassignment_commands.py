"""
Trainer Habit Unassignment Commands
Handles habit unassignment from clients
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_unassign_habit(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /unassign-habit command"""
    try:
        # Create unassign_habit task (use phone for task identification)
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='unassign_habit',
            task_data={'step': 'ask_client_id', 'trainer_id': trainer_id}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the unassignment process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'unassign_habit_task_error'}
        
        # Generate trainees dashboard link
        from services.commands.dashboard import generate_dashboard_link
        dashboard_result = generate_dashboard_link(phone, trainer_id, 'trainer', db, whatsapp, 'view_clients')
        
        # Ask for client ID with dashboard link
        msg = (
            "🗑️ *Unassign Habit - Step 1*\n\n"
            "Please provide the trainee ID whose habit you want to unassign.\n\n"
        )
        
        if dashboard_result.get('success'):
            msg += (
                "💡 *View your trainees above* ⬆️ to find the trainee ID\n\n"
                "📋 *Steps:* Find the trainee → Copy their ID → Return here with the ID\n\n"
            )
        else:
            msg += "💡 Use /view-trainees to see your trainees and their IDs.\n\n"
        
        msg += "Type /stop to cancel."
        
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'unassign_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in unassign habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'unassign_habit_error'
        }