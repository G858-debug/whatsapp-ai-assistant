"""
Client Habit Viewing Commands
Handles viewing client's assigned habits
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_my_habits(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Handle /view-my-habits command - Always use dashboard for simplicity"""
    try:
        # Get assigned habits count
        assignments = db.table('trainee_habit_assignments')\
            .select('*, fitness_habits(*)')\
            .eq('client_id', client_id)\
            .eq('is_active', True)\
            .execute()
        
        if not assignments.data:
            msg = (
                "🎯 *Your Habits*\n\n"
                "You don't have any habits assigned yet.\n\n"
                "Ask your trainer to assign some habits to get started!"
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_my_habits_empty'}
        
        # Always use dashboard for simplicity
        from services.commands.dashboard import generate_client_habits_dashboard
        
        dashboard_result = generate_client_habits_dashboard(phone, client_id, db, whatsapp)
        
        if dashboard_result['success']:
            return dashboard_result
        
        # Fallback message if dashboard fails
        msg = (
            f"🎯 *Your Habits* ({len(assignments.data)})\n\n"
            f"You have {len(assignments.data)} habits assigned.\n\n"
            f"Use /dashboard-habits to view them in a web interface with search and filter options."
        )
        whatsapp.send_message(phone, msg)
        return {'success': True, 'response': msg, 'handler': 'view_my_habits_fallback'}
        
    except Exception as e:
        log_error(f"Error viewing client habits: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your habits. Please try again.",
            'handler': 'view_my_habits_error'
        }