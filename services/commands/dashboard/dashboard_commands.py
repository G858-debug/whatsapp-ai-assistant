"""
Dashboard Commands
Handles dashboard link generation and integration with existing commands
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.dashboard import DashboardTokenManager
import os


def generate_dashboard_link(phone: str, user_id: str, role: str, db, whatsapp, purpose: str = 'relationships') -> Dict:
    """Generate dashboard link and send to user"""
    try:
        # Generate secure token
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(user_id, role, purpose)
        
        if not token:
            return {
                'success': False,
                'response': "❌ Could not generate dashboard link. Please try again.",
                'handler': 'dashboard_link_error'
            }
        
        # Get base URL from environment or use default
        base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
        dashboard_url = f"{base_url}/dashboard/{user_id}/{token}"
        
        # Determine what they're viewing
        viewing_type = 'clients' if role == 'trainer' else 'trainers'
        
        # Send dashboard link
        remove_command = '/remove-trainee' if role == 'trainer' else '/remove-trainer'
        
        # Customize message based on purpose
        if purpose == 'view_clients' or purpose == 'view_trainers':
            msg = (
                f"🌐 *{viewing_type.title()} Dashboard*\n\n"
                f"Use this link to search, filter, and browse your {viewing_type}:\n\n"
                f"🔗 {dashboard_url}\n\n"
                f"✨ *Perfect for:*\n"
                f"• Finding specific {viewing_type[:-1]} quickly\n"
                f"• Getting IDs for other commands\n"
                f"• Viewing detailed information\n"
                f"• Exporting your list\n\n"
                f"🔒 *Security:* Link expires in 1 hour"
            )
        elif purpose == 'remove_client' or purpose == 'remove_trainer':
            target_type = 'client' if purpose == 'remove_client' else 'trainer'
            msg = (
                f"🗑️ *Remove {target_type.title()} - Step 1*\n\n"
                f"First, browse your {viewing_type} to find who you want to remove:\n\n"
                f"🔗 {dashboard_url}\n\n"
                f"📋 *What to do:*\n"
                f"• Search or browse to find the {target_type}\n"
                f"• Copy their ID (click the copy button)\n"
                f"• Return to WhatsApp with the ID\n\n"
                f"🔒 *Security:* Link expires in 1 hour"
            )
        else:
            msg = (
                f"🌐 *Web Dashboard*\n\n"
                f"View and manage your {viewing_type} in a beautiful web interface:\n\n"
                f"🔗 {dashboard_url}\n\n"
                f"✨ *Features:*\n"
                f"• Search and filter {viewing_type}\n"
                f"• Sort by name, date, etc.\n"
                f"• Copy IDs for quick actions\n"
                f"• Export to CSV\n"
                f"• Mobile-friendly design\n\n"
                f"🗑️ *To Remove:* Copy ID from dashboard, then use `{remove_command}` command\n\n"
                f"🔒 *Security:* Link expires in 1 hour\n\n"
                f"💡 *Tip:* Bookmark the link for quick access!"
            )
        
        whatsapp.send_message(phone, msg)
        
        log_info(f"Dashboard link sent to {role} {user_id}")
        
        return {
            'success': True,
            'response': msg,
            'handler': 'dashboard_link_sent',
            'dashboard_url': dashboard_url
        }
        
    except Exception as e:
        log_error(f"Error generating dashboard link: {str(e)}")
        return {
            'success': False,
            'response': "❌ Could not generate dashboard link. Please try again.",
            'handler': 'dashboard_link_error'
        }


def generate_trainer_browse_dashboard(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Generate dashboard link for browsing ALL trainers on the platform"""
    try:
        # Generate secure token for browsing trainers
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(client_id, 'client', 'browse_trainers')
        
        if not token:
            return {
                'success': False,
                'response': "❌ Could not generate trainer browse dashboard. Please try again.",
                'handler': 'browse_dashboard_error'
            }
        
        # Get base URL from environment or use default
        base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
        dashboard_url = f"{base_url}/dashboard/{client_id}/{token}"
        
        msg = (
            f"🔍 *Browse All Trainers*\n\n"
            f"Discover trainers on our platform:\n\n"
            f"🔗 {dashboard_url}\n\n"
            f"✨ *Features:*\n"
            f"• Browse ALL available trainers\n"
            f"• Search by name, city, specialization\n"
            f"• Filter by price, experience, availability\n"
            f"• See detailed trainer profiles\n"
            f"• Copy Trainer ID to invite them\n"
            f"• Mobile-friendly interface\n\n"
            f"💡 *To Invite:* Copy Trainer ID from dashboard, then return to WhatsApp\n\n"
            f"🔒 *Security:* Link expires in 1 hour"
        )
        
        whatsapp.send_message(phone, msg)
        
        log_info(f"Trainer browse dashboard sent to client {client_id}")
        
        return {
            'success': True,
            'response': msg,
            'handler': 'browse_dashboard_sent',
            'dashboard_url': dashboard_url
        }
        
    except Exception as e:
        log_error(f"Error generating trainer browse dashboard: {str(e)}")
        return {
            'success': False,
            'response': "❌ Could not generate trainer browse dashboard. Please try again.",
            'handler': 'browse_dashboard_error'
        }


def generate_trainer_habits_dashboard(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Generate dashboard link for trainer's habits"""
    try:
        # Generate secure token for habits view
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(trainer_id, 'trainer', 'view_habits')
        
        if not token:
            return {
                'success': False,
                'response': "❌ Could not generate habits dashboard. Please try again.",
                'handler': 'habits_dashboard_error'
            }
        
        # Get base URL from environment or use default
        base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
        dashboard_url = f"{base_url}/dashboard/habits/{trainer_id}/{token}"
        
        msg = (
            f"🎯 *My Habits Dashboard*\n\n"
            f"View and manage your created habits:\n\n"
            f"🔗 {dashboard_url}\n\n"
            f"✨ *Features:*\n"
            f"• View all your created habits\n"
            f"• Search and filter habits\n"
            f"• See assignment counts\n"
            f"• Copy Habit IDs for commands\n"
            f"• Sort by name, date, assignments\n"
            f"• Mobile-friendly interface\n\n"
            f"💡 *Perfect for:* Finding habit IDs for /assign-habit command\n\n"
            f"🔒 *Security:* Link expires in 1 hour"
        )
        
        whatsapp.send_message(phone, msg)
        
        log_info(f"Trainer habits dashboard sent to {trainer_id}")
        
        return {
            'success': True,
            'response': msg,
            'handler': 'habits_dashboard_sent',
            'dashboard_url': dashboard_url
        }
        
    except Exception as e:
        log_error(f"Error generating trainer habits dashboard: {str(e)}")
        return {
            'success': False,
            'response': "❌ Could not generate habits dashboard. Please try again.",
            'handler': 'habits_dashboard_error'
        }


def generate_trainee_progress_dashboard(phone: str, trainer_id: str, trainee_id: str, db, whatsapp) -> Dict:
    """Generate dashboard link for trainee progress"""
    try:
        # Generate secure token for progress view
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(trainer_id, 'trainer', 'view_progress')
        
        if not token:
            return {
                'success': False,
                'response': "❌ Could not generate progress dashboard. Please try again.",
                'handler': 'progress_dashboard_error'
            }
        
        # Get trainee name for message
        trainee_result = db.table('clients').select('name').eq('client_id', trainee_id).execute()
        trainee_name = trainee_result.data[0]['name'] if trainee_result.data else trainee_id
        
        # Get base URL from environment or use default
        base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
        dashboard_url = f"{base_url}/dashboard/progress/{trainer_id}/{token}/{trainee_id}"
        
        msg = (
            f"📊 *{trainee_name}'s Progress Dashboard*\n\n"
            f"Track your trainee's habit completion:\n\n"
            f"🔗 {dashboard_url}\n\n"
            f"✨ *Features:*\n"
            f"• Daily and monthly progress views\n"
            f"• Habit completion tracking\n"
            f"• Target vs actual comparison\n"
            f"• Progress percentages and streaks\n"
            f"• Visual progress indicators\n"
            f"• Mobile-friendly interface\n\n"
            f"📈 *Switch between Daily and Monthly views* to see different time periods\n\n"
            f"🔒 *Security:* Link expires in 1 hour"
        )
        
        whatsapp.send_message(phone, msg)
        
        log_info(f"Trainee progress dashboard sent to {trainer_id} for {trainee_id}")
        
        return {
            'success': True,
            'response': msg,
            'handler': 'progress_dashboard_sent',
            'dashboard_url': dashboard_url
        }
        
    except Exception as e:
        log_error(f"Error generating trainee progress dashboard: {str(e)}")
        return {
            'success': False,
            'response': "❌ Could not generate progress dashboard. Please try again.",
            'handler': 'progress_dashboard_error'
        }


def generate_trainee_habits_dashboard(phone: str, trainer_id: str, trainee_id: str, db, whatsapp) -> Dict:
    """Generate dashboard link for trainee's habits assigned by this trainer"""
    try:
        # Generate secure token for habits view
        token_manager = DashboardTokenManager(db)
        token = token_manager.generate_token(trainer_id, 'trainer', 'view_trainee_habits')
        
        if not token:
            return {
                'success': False,
                'response': "❌ Could not generate habits dashboard. Please try again.",
                'handler': 'trainee_habits_dashboard_error'
            }
        
        # Get trainee name for message
        trainee_result = db.table('clients').select('name').eq('client_id', trainee_id).execute()
        trainee_name = trainee_result.data[0]['name'] if trainee_result.data else trainee_id
        
        # Get base URL from environment or use default
        base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
        dashboard_url = f"{base_url}/dashboard/trainee-habits/{trainer_id}/{token}/{trainee_id}"
        
        msg = (
            f"🎯 *{trainee_name}'s Assigned Habits*\n\n"
            f"View habits you've assigned to this trainee:\n\n"
            f"🔗 {dashboard_url}\n\n"
            f"✨ *Features:*\n"
            f"• View only YOUR assigned habits\n"
            f"• Search and filter habits\n"
            f"• Copy habit IDs for unassigning\n"
            f"• See assignment dates\n"
            f"• Mobile-friendly interface\n\n"
            f"💡 *Perfect for:* Finding habit IDs for /unassign-habit command\n\n"
            f"🔒 *Security:* Link expires in 1 hour"
        )
        
        whatsapp.send_message(phone, msg)
        
        log_info(f"Trainee habits dashboard sent to {trainer_id} for {trainee_id}")
        
        return {
            'success': True,
            'response': msg,
            'handler': 'trainee_habits_dashboard_sent',
            'dashboard_url': dashboard_url
        }
        
    except Exception as e:
        log_error(f"Error generating trainee habits dashboard: {str(e)}")
        return {
            'success': False,
            'response': "❌ Could not generate habits dashboard. Please try again.",
            'handler': 'trainee_habits_dashboard_error'
        }