"""
Trainer Habit Reporting Commands
Handles progress viewing and report generation
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_habit_progress(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /view-trainee-progress command"""
    try:
        # Create view_trainee_progress task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='view_trainee_progress',
            task_data={'step': 'ask_client_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'view_trainee_progress_task_error'}
        
        # Generate trainees dashboard link
        from services.commands.dashboard import generate_dashboard_link
        dashboard_result = generate_dashboard_link(phone, trainer_id, 'trainer', db, whatsapp, 'view_clients')
        
        # Ask for client ID with dashboard link
        msg = (
            "📊 *View Client Progress - Step 1*\n\n"
            "Please provide the client ID whose progress you want to view.\n\n"
        )
        
        if dashboard_result.get('success'):
            msg += (
                "💡 *View your clients above* ⬆️ to find the client ID\n\n"
                "📋 *Steps:* Find the client → Copy their ID → Return here with the ID\n\n"
            )
        else:
            msg += "💡 Use /view-trainees to see your clients and their IDs.\n\n"
        
        msg += "Type /stop to cancel."
        
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'view_trainee_progress_started'
        }
        
    except Exception as e:
        log_error(f"Error in view trainee progress command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'view_trainee_progress_error'
        }


def handle_export_habit_data(phone: str, trainer_id: str, db, whatsapp, task_service, report_type: str = None) -> Dict:
    """Handle /trainee-weekly-report and /trainee-monthly-report commands"""
    try:
        # Determine report type from command if not provided
        if not report_type:
            report_type = 'weekly'  # default
        
        # Create trainee_report task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='trainee_report',
            task_data={
                'step': 'ask_client_id',
                'report_type': report_type
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the report generation. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'trainee_report_task_error'}
        
        # Ask for client ID
        report_label = "Weekly" if report_type == 'weekly' else "Monthly"
        msg = (
            f"📈 *Generate {report_label} Report*\n\n"
            f"Please provide the client ID for the {report_label.lower()} report.\n\n"
            "💡 Use /view-trainees to see your clients and their IDs.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'trainee_report_started'
        }
        
    except Exception as e:
        log_error(f"Error in trainee report command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'trainee_report_error'
        }