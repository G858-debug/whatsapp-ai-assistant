"""
Dashboard Commands
Handles dashboard link generation and integration with existing commands
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.dashboard import DashboardTokenManager
import os


def generate_dashboard_link(user_id: str, role: str, db, whatsapp, purpose: str = 'relationships') -> Dict:
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
        msg = (
            f"🌐 *Web Dashboard*\n\n"
            f"View and manage your {viewing_type} in a beautiful web interface:\n\n"
            f"🔗 {dashboard_url}\n\n"
            f"✨ *Features:*\n"
            f"• Search and filter {viewing_type}\n"
            f"• Sort by name, date, etc.\n"
            f"• Copy IDs for quick actions\n"
            f"• Remove {viewing_type} with confirmation\n"
            f"• Export to CSV\n"
            f"• Mobile-friendly design\n\n"
            f"🔒 *Security:* Link expires in 1 hour\n\n"
            f"💡 *Tip:* Bookmark the link for quick access!"
        )
        
        whatsapp.send_message(user_id.replace('trainer_', '').replace('client_', ''), msg)
        
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