"""
Client Habit Commands - Phase 3
Handles client commands for habit tracking and progress viewing
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


def handle_view_progress(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /view-progress command"""
    try:
        # Create view_progress task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='view_progress',
            task_data={'step': 'ask_date'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'view_progress_task_error'}
        
        # Ask for date
        msg = (
            "📊 *View Your Progress*\n\n"
            "Which date would you like to see?\n\n"
            "*Options:*\n"
            "• Type 'today' for today's progress\n"
            "• Type 'yesterday' for yesterday\n"
            "• Or enter a date (YYYY-MM-DD format)\n\n"
            "Example: 2024-01-15\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'view_progress_started'
        }
        
    except Exception as e:
        log_error(f"Error in view progress command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'view_progress_error'
        }


def handle_weekly_report(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /weekly-report command"""
    try:
        # Create weekly_report task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='weekly_report',
            task_data={'step': 'ask_week'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the report generation. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'weekly_report_task_error'}
        
        # Ask for week
        msg = (
            "📈 *Weekly Progress Report*\n\n"
            "Which week would you like to see?\n\n"
            "*Options:*\n"
            "• Type 'this week' for current week\n"
            "• Type 'last week' for previous week\n"
            "• Or enter week start date (YYYY-MM-DD)\n\n"
            "Example: 2024-01-15\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'weekly_report_started'
        }
        
    except Exception as e:
        log_error(f"Error in weekly report command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'weekly_report_error'
        }


def handle_monthly_report(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /monthly-report command"""
    try:
        # Create monthly_report task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='monthly_report',
            task_data={'step': 'ask_month'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the report generation. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'monthly_report_task_error'}
        
        # Ask for month
        msg = (
            "📈 *Monthly Progress Report*\n\n"
            "Which month would you like to see?\n\n"
            "*Options:*\n"
            "• Type 'this month' for current month\n"
            "• Type 'last month' for previous month\n"
            "• Or enter month and year (MM-YYYY)\n\n"
            "Example: 01-2024 for January 2024\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'monthly_report_started'
        }
        
    except Exception as e:
        log_error(f"Error in monthly report command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'monthly_report_error'
        }
