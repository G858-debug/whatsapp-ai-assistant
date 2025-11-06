"""
Client Habit Logging Commands
Handles logging habit completions
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_log_habits(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /log-habits command"""
    try:
        # Get assigned habits
        assignments = db.table('trainee_habit_assignments')\
            .select('*, fitness_habits(*)')\
            .eq('client_id', client_id)\
            .eq('is_active', True)\
            .execute()
        
        if not assignments.data:
            msg = (
                "📝 *Log Habits*\n\n"
                "You don't have any habits assigned yet.\n\n"
                "Ask your trainer to assign some habits first!"
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'log_habits_no_habits'}
        
        # Prepare habits data for the flow
        habits = []
        for assignment in assignments.data:
            habit = assignment.get('fitness_habits')
            if habit:
                habits.append({
                    'habit_id': habit.get('habit_id'),
                    'habit_name': habit.get('habit_name'),
                    'target_value': habit.get('target_value'),
                    'unit': habit.get('unit')
                })
        
        # Create log_habits task with habits data (start from index 1 since first question will be asked)
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='log_habits',
            task_data={
                'habits': habits,
                'current_habit_index': 1,
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
        
        # Send intro message with first habit question
        intro_msg = (
            f"📝 *Log Your Habits*\n\n"
            f"I'll help you log progress for your {len(habits)} habits.\n\n"
            f"💡 *Tip:* You can type /stop at any time to cancel.\n\n"
            f"Let's start! 👇\n\n"
            f"*1/{len(habits)}: {habits[0]['habit_name']}*\n\n"
            f"Target: {habits[0]['target_value']} {habits[0]['unit']}\n\n"
            f"How much did you complete?\n"
            f"(Enter a number)"
        )
        whatsapp.send_message(phone, intro_msg)
        
        return {
            'success': True,
            'response': intro_msg,
            'handler': 'log_habits_started'
        }
        
    except Exception as e:
        log_error(f"Error in log habits command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'log_habits_error'
        }