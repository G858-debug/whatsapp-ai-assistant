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
        
        # Display all habits (no CSV needed for clients)
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


def handle_log_habits(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /log-habits command"""
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
        
        # Create log_habits task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='log_habits',
            task_data={
                'current_habit_index': 0,
                'habits': [{'habit_id': h.get('habit_id'), 'habit_name': h.get('habit_name'), 
                           'target_value': h.get('target_value'), 'unit': h.get('unit')} 
                          for h in habits],
                'logged_values': {}
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the logging process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'log_habits_task_error'}
        
        # Send intro message
        intro_msg = (
            f"📝 *Log Your Habits*\n\n"
            f"I'll ask you about each of your {len(habits)} habits.\n\n"
            f"💡 *Tip:* You can log multiple times per day!\n\n"
            f"Type /stop to cancel.\n\n"
            f"Let's start! 👇"
        )
        whatsapp.send_message(phone, intro_msg)
        
        # Ask for first habit
        first_habit = habits[0]
        habit_msg = (
            f"*1/{len(habits)}: {first_habit.get('habit_name')}*\n\n"
            f"Target: {first_habit.get('target_value')} {first_habit.get('unit')}\n\n"
            f"How much did you complete?\n"
            f"(Enter a number)"
        )
        whatsapp.send_message(phone, habit_msg)
        
        return {
            'success': True,
            'response': habit_msg,
            'handler': 'log_habits_started'
        }
        
    except Exception as e:
        log_error(f"Error in log habits command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'log_habits_error'
        }