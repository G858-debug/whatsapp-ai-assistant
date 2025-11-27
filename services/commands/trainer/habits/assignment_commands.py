"""
Trainer Habit Assignment Commands
Handles habit assignment and client habit management
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_assign_habits(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /assign-habit command"""
    try:
        # Create assign_habit task (use phone for task identification)
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='assign_habit',
            task_data={'step': 'ask_habit_id', 'trainer_id': trainer_id}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the assignment process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'assign_habit_task_error'}
        
        # Generate habits dashboard link
        from services.commands.dashboard import generate_trainer_habits_dashboard
        dashboard_result = generate_trainer_habits_dashboard(phone, trainer_id, db, whatsapp)
        
        # Ask for habit ID with dashboard link
        msg = (
            "📌 *Assign Habit to Clients - Step 1*\n\n"
            "Please provide the habit ID you want to assign.\n\n"
        )
        
        if dashboard_result.get('success'):
            msg += (
                "💡 *View your habits above* ⬆️ to find the habit ID\n\n"
                "📋 *Steps:* Find the habit → Copy its ID → Return here with the ID\n\n"
            )
        else:
            msg += "💡 Use /view-habits to see your habits and their IDs.\n\n"
        
        msg += "Type /stop to cancel."
        
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'assign_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in assign habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'assign_habit_error'
        }


def handle_view_client_habits(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Handle /view-habits command - Always use dashboard for simplicity"""
    try:
        from services.habits.habit_service import HabitService
        
        habit_service = HabitService(db)
        success, msg, habits = habit_service.get_trainer_habits(trainer_id, active_only=True)
        
        if not success:
            error_msg = "❌ I couldn't load your habits. Please try again."
            whatsapp.send_message(phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'view_habits_error'}
        
        if not habits:
            msg = (
                "🎯 *Your Habits*\n\n"
                "You haven't created any habits yet.\n\n"
                "Use /create-habit to create your first habit!"
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_habits_empty'}
        
        # Always use dashboard for simplicity
        from services.commands.dashboard import generate_trainer_habits_dashboard
        
        dashboard_result = generate_trainer_habits_dashboard(phone, trainer_id, db, whatsapp)
        
        if dashboard_result['success']:
            return dashboard_result
        
        # Fallback message if dashboard fails
        msg = (
            f"🎯 *Your Habits* ({len(habits)})\n\n"
            f"You have {len(habits)} habits.\n\n"
            f"Use /dashboard-habits to view them in a web interface with search and filter options."
        )
        whatsapp.send_message(phone, msg)
        return {'success': True, 'response': msg, 'handler': 'view_habits_fallback'}
        
    except Exception as e:
        log_error(f"Error viewing habits: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your habits. Please try again.",
            'handler': 'view_habits_error'
        }