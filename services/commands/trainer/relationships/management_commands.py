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
    """Handle /remove-trainee command - Guide to dashboard first"""
    try:
        from services.commands.dashboard import generate_dashboard_link
        
        # Generate dashboard link for browsing clients
        dashboard_result = generate_dashboard_link(phone, trainer_id, 'trainer', db, whatsapp, 'remove_client')
        
        if dashboard_result['success']:
            # Add additional instructions for removal
            additional_msg = (
                "\n\n🗑️ *To Remove a Client:*\n"
                "1. Browse your clients using the link above\n"
                "2. Find the client you want to remove\n"
                "3. Copy their Client ID\n"
                "4. Come back to WhatsApp and type: `/remove-trainee [CLIENT_ID]`\n\n"
                "⚠️ *Warning:* This will remove them from your list and delete all habit assignments.\n\n"
                "Type /stop to cancel anytime."
            )
            
            # Send the additional instructions
            whatsapp.send_message(phone, additional_msg)
            
            return {
                'success': True,
                'response': dashboard_result['response'] + additional_msg,
                'handler': 'remove_trainee_dashboard_sent'
            }
        
        # Fallback to direct ID request if dashboard fails
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='remove_trainee',
            task_data={'step': 'ask_client_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainee_task_error'}
        
        # Ask for client ID directly
        msg = (
            "🗑️ *Remove Client*\n\n"
            "Please provide the client ID you want to remove.\n\n"
            "💡 *Tip:* Use /view-trainees to see your client list and get their IDs.\n\n"
            "⚠️ This will remove them from your client list and delete all habit assignments.\n\n"
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