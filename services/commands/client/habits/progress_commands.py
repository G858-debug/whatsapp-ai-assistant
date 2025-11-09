"""
Client Habit Progress Commands
Handles progress viewing and reporting
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_progress(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /view-progress command"""
    try:
        # Create view_progress task - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='view_progress',
            task_data={
                'step': 'ask_view_type',
                'client_id': client_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'view_progress_task_error'}
        
        # Ask for view type first
        msg = (
            "📊 *View Your Progress*\n\n"
            "How would you like to view your progress?\n\n"
            "*Choose View Type:*\n"
            "• Type '1' or 'daily' for Daily Progress\n"
            "• Type '2' or 'monthly' for Monthly Progress\n\n"
            "📅 *Daily View:* See progress for a specific date\n"
            "📈 *Monthly View:* See progress for an entire month\n\n"
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
        # Create weekly_report task - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='weekly_report',
            task_data={
                'step': 'ask_week',
                'client_id': client_id
            }
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
        # Create monthly_report task - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='monthly_report',
            task_data={
                'step': 'ask_month',
                'client_id': client_id
            }
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