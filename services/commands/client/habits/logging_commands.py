"""
Client Habit Logging Commands
Handles habit logging and viewing
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_my_habits(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Handle /view-my-habits command"""
    try:
        from services.habits.assignment_service import AssignmentService
        
        assignment_service = AssignmentService(db)
        success, msg, habits = assignment_service.get_client_habits(client_id, active_only=True)
        
        if not success:
            error_msg = "❌ I couldn't load your habits. Please try again."
            whatsapp.send_message(phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'view_my_habits_error'}
        
        if not habits:
            msg = (
                "🎯 *Your Habits*\n\n"
                "You don't have any habits assigned yet.\n\n"
                "Your trainer will assign habits for you to track."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_my_habits_empty'}
            
        # Always use dashboard for simplicity
        from services.commands.dashboard import generate_client_habits_dashboard
        
        dashboard_result = generate_client_habits_dashboard(phone, client_id, db, whatsapp)
        
        if dashboard_result['success']:
            return dashboard_result
        
        # Fallback message if dashboard fails        
        response_msg = f"🎯 *Your Habits* ({len(habits)})\n\n"
        
        for i, habit in enumerate(habits, 1):
            response_msg += f"*{i}. {habit.get('habit_name')}*\n"
            response_msg += f"   ID: `{habit.get('habit_id')}`\n"
            response_msg += f"   Target: {habit.get('target_value')} {habit.get('unit')} per {habit.get('frequency', 'day')}\n"
            
            if habit.get('description'):
                desc = habit['description'][:60] + '...' if len(habit['description']) > 60 else habit['description']
                response_msg += f"   Description: {desc}\n"
            
            assigned_date = habit.get('assigned_date', '')[:10] if habit.get('assigned_date') else 'N/A'
            response_msg += f"   Assigned: {assigned_date}\n\n"
        
        response_msg += "💡 Use /log-habits to log your progress!"
        
        whatsapp.send_message(phone, response_msg)
        return {'success': True, 'response': response_msg, 'handler': 'view_my_habits_success'}
        
    except Exception as e:
        log_error(f"Error viewing client habits: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your habits. Please try again.",
            'handler': 'view_my_habits_error'
        }

def handle_log_habits(phone: str, client_id: str, db, whatsapp, task_service, habit_id: str = None) -> Dict:
    """Handle /log-habits command with optional habit ID"""
    try:
        from services.habits.assignment_service import AssignmentService
        
        # Check if client has any habits assigned
        assignment_service = AssignmentService(db)
        success, msg, habits = assignment_service.get_client_habits(client_id, active_only=True)
        
        if not success or not habits:
            error_msg = (
                "🎯 *Log Habits*\n\n"
                "You don't have any habits assigned yet.\n\n"
                "Your trainer will assign habits for you to track."
            )
            whatsapp.send_message(phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'log_habits_no_habits'}

        # If specific habit ID provided, handle single habit logging directly
        if habit_id:
            return handle_single_habit_logging(phone, client_id, habit_id, habits, db, whatsapp, task_service)

        # Create log_habits task waiting for habit ID selection
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='log_habits',
            task_data={
                'habits': [{'habit_id': h.get('habit_id'), 'habit_name': h.get('habit_name'), 
                           'target_value': h.get('target_value'), 'unit': h.get('unit')} 
                          for h in habits],
                'waiting_for_habit_id': True,
                'logged_values': {}
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the logging process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'log_habits_task_error'}
        
        # Generate client habits dashboard link for reference
        from services.commands.dashboard import generate_client_habits_dashboard
        dashboard_result = generate_client_habits_dashboard(phone, client_id, db, whatsapp)
        
        # Send intro message asking for habit ID
        intro_msg = (
            f"📝 *Log Your Habits*\n\n"
            f"I've sent you a dashboard link above with all your {len(habits)} habits and their IDs.\n\n"
            f"📋 *Next Step:*\n"
            f"Please send me the *Habit ID* of the habit you want to log.\n\n"
            f"💡 *Example:* If you want to log water intake, send: `HABWAT`\n\n"
            f"🔍 *Tip:* Click on any Habit ID in the dashboard to copy it!\n\n"
            f"⏹️ Type /stop to cancel anytime."
        )
        whatsapp.send_message(phone, intro_msg)
        
        return {
            'success': True,
            'response': intro_msg,
            'handler': 'log_habits_waiting_for_habit_id'
        }
        
    except Exception as e:
        log_error(f"Error in log habits command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'log_habits_error'
        }


def handle_single_habit_logging(phone: str, client_id: str, habit_id: str, habits: list, db, whatsapp, task_service) -> Dict:
    """Handle logging for a specific habit ID"""
    try:
        # Find the habit in the list
        selected_habit = None
        for habit in habits:
            if habit.get('habit_id') == habit_id.upper():
                selected_habit = habit
                break
        
        if not selected_habit:
            # Invalid habit ID
            error_msg = (
                f"❌ Invalid habit ID: `{habit_id}`\n\n"
                f"📋 *Your valid habit IDs:*\n"
            )
            for habit in habits:
                error_msg += f"• `{habit.get('habit_id')}` - {habit.get('habit_name')}\n"
            
            error_msg += f"\n💡 Use /log-habits to see the dashboard and select a habit."
            
            whatsapp.send_message(phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'log_habits_invalid_id'}
        
        # Create task for single habit logging
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='log_habits',
            task_data={
                'habits': [{'habit_id': selected_habit.get('habit_id'), 'habit_name': selected_habit.get('habit_name'), 
                           'target_value': selected_habit.get('target_value'), 'unit': selected_habit.get('unit')}],
                'waiting_for_habit_id': False,
                'waiting_for_value': True,
                'current_habit_id': selected_habit.get('habit_id'),
                'selected_habit': selected_habit,
                'logged_values': {}
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the logging process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'log_habits_task_error'}
        
        # Ask for value directly
        value_msg = (
            f"✅ *Selected: {selected_habit.get('habit_name')}*\n\n"
            f"🎯 Target: {selected_habit.get('target_value')} {selected_habit.get('unit')}\n\n"
            f"📝 How much did you complete today?\n"
            f"(Enter a number)"
        )
        
        whatsapp.send_message(phone, value_msg)
        return {
            'success': True,
            'response': value_msg,
            'handler': 'log_habits_waiting_for_value'
        }
        
    except Exception as e:
        log_error(f"Error in single habit logging: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'log_habits_error'
        }