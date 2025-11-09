"""
Trainer Dashboard Commands
Handles trainer dashboard generation and management
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_trainer_main_dashboard(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Handle /trainer-dashboard command"""
    try:
        # Generate trainer dashboard link
        from services.commands.dashboard import generate_trainer_main_dashboard
        dashboard_result = generate_trainer_main_dashboard(phone, trainer_id, db, whatsapp)
        
        return dashboard_result
        
    except Exception as e:
        log_error(f"Error in trainer dashboard command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'trainer_dashboard_error'
        }


def handle_client_progress_dashboard(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /client-progress command"""
    try:
        # Create client_progress task - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='client_progress',
            task_data={
                'step': 'ask_client_id',
                'trainer_id': trainer_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'client_progress_task_error'}
        
        # Generate trainees dashboard link
        from services.commands.dashboard import generate_dashboard_link
        dashboard_result = generate_dashboard_link(phone, trainer_id, 'trainer', db, whatsapp, 'view_clients')
        
        # Ask for client ID with dashboard link
        msg = (
            "📊 *Client Progress Dashboard - Step 1*\n\n"
            "Please provide the client ID whose progress you want to view.\n\n"
            "💡 *Tip:* Use the dashboard link above to browse your clients and copy their ID\n\n"
            "Type /stop to cancel."
        )
        
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'client_progress_started'
        }
        
    except Exception as e:
        log_error(f"Error in client progress command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'client_progress_error'
        }