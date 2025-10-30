"""
Client Relationship Search Commands
Handles trainer search and viewing
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_search_trainers(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /search-trainer command"""
    try:
        # Create search_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='search_trainer',
            task_data={'step': 'ask_search_term'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the search. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'search_trainer_task_error'}
        
        # Ask for search term
        msg = (
            "🔍 *Search for Trainers*\n\n"
            "Please enter the trainer's name you want to search for.\n\n"
            "💡 I'll show you up to 5 matching trainers.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'search_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in search trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'search_trainer_error'
        }


def handle_view_trainers(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Handle /view-trainers command - Always use dashboard for simplicity"""
    try:
        from services.relationships import RelationshipService
        
        rel_service = RelationshipService(db)
        trainers = rel_service.get_client_trainers(client_id, status='active')
        
        if not trainers:
            msg = (
                "📋 *Your Trainers*\n\n"
                "You don't have any trainers yet.\n\n"
                "Use /search-trainer to find trainers\n"
                "or /invite-trainer to invite a specific trainer."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_trainers_empty'}
        
        # Always use dashboard for simplicity
        from services.commands.dashboard import generate_dashboard_link
        
        dashboard_result = generate_dashboard_link(phone, client_id, 'client', db, whatsapp, 'view_trainers')
        
        if dashboard_result['success']:
            return dashboard_result
        
        # Fallback message if dashboard fails
        msg = (
            f"📋 *Your Trainers* ({len(trainers)})\n\n"
            f"You have {len(trainers)} active trainers.\n\n"
            f"Use /dashboard-trainers to view them in a web interface with search and filter options."
        )
        whatsapp.send_message(phone, msg)
        return {'success': True, 'response': msg, 'handler': 'view_trainers_fallback'}
           
        
    except Exception as e:
        log_error(f"Error viewing trainers: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your trainers. Please try again.",
            'handler': 'view_trainers_error'
        }