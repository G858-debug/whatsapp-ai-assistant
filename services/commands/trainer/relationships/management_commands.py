"""
Trainer Relationship Management Commands
Handles client viewing and removal
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_trainees(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Handle /view-trainees command - Always use dashboard for simplicity"""
    try:
        from services.relationships import RelationshipService
        
        rel_service = RelationshipService(db)
        clients = rel_service.get_trainer_clients(trainer_id, status='active')
        
        if not clients:
            msg = (
                "📋 *Your Clients*\n\n"
                "You don't have any clients yet.\n\n"
                "Use /invite-trainee to invite an existing client\n"
                "or /create-trainee to create a new client account."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_trainees_empty'}
        
        # Always use dashboard for simplicity
        from services.commands.dashboard import generate_dashboard_link
        
        dashboard_result = generate_dashboard_link(phone, trainer_id, 'trainer', db, whatsapp, 'view_clients')
        
        if dashboard_result['success']:
            return dashboard_result
        
        # Fallback message if dashboard fails
        msg = (
            f"📋 *Your Clients* ({len(clients)})\n\n"
            f"You have {len(clients)} active clients.\n\n"
            f"Use /dashboard-clients to view them in a web interface with search and filter options."
        )
        whatsapp.send_message(phone, msg)
        return {'success': True, 'response': msg, 'handler': 'view_trainees_fallback'}
            
        
    except Exception as e:
        log_error(f"Error viewing trainees: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your clients. Please try again.",
            'handler': 'view_trainees_error'
        }


def handle_remove_trainee(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /remove-trainee command - Dashboard link with ID request"""
    try:
        # Create task for removal flow - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='remove_trainee',
            task_data={
                'step': 'ask_client_id',
                'trainer_id': trainer_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainee_task_error'}
        
        # Generate dashboard link for browsing clients
        from services.dashboard import DashboardTokenManager
        import os
        
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(trainer_id, 'trainer', 'remove_client')
        
        dashboard_url = ""
        if token:
            base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
            dashboard_url = f"{base_url}/dashboard/{trainer_id}/{token}"
        
        # Ask for client ID with dashboard link
        msg = (
            "🗑️ *Remove Client*\n\n"
            "Please provide the Client ID you want to remove.\n\n"
        )
        
        if dashboard_url:
            msg += (
                f"💡 *Browse your clients here:*\n"
                f"🔗 {dashboard_url}\n\n"
                f"📋 *Steps:* Find the client → Copy their ID → Return here with the ID\n\n"
            )
        else:
            msg += "💡 *Tip:* Use /view-trainees to see your client list first\n\n"
        
        msg += (
            "⚠️ *Warning:* This will remove them from your client list and delete all habit assignments.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'remove_trainee_started'
        }
        
    except Exception as e:
        log_error(f"Error in remove trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'remove_trainee_error'
        }