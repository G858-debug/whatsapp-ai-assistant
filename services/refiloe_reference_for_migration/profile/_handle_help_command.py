"""
 Handle Help Command
Handle /help command - show available commands and features
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_help_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
    """Handle /help command - show available commands and features"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        name = user_data.get('name', 'there') if user_data else 'there'
        
        if user_type == 'trainer':
            response = (
                f"👋 Hi {name}! Here's what you can do:\n\n"
                "🔧 *Profile Commands:*\n"
                "• `/profile` - View your trainer profile\n"
                "• `/edit_profile` - Update your profile info\n\n"
                "👥 *Client Management:*\n"
                "• `/clients` - View and manage your clients\n"
                "• `/add_client` - Add a new client\n\n"
                "💬 *General:*\n"
                "• Just chat with me for AI assistance\n"
                "• Ask about fitness, training, or business help\n\n"
                "🔄 *Role Switching:*\n"
                "• Use 'Switch Role' button if you're also a client\n\n"
                "Need help with anything specific? Just ask! 😊"
            )
        elif user_type == 'client':
            trainer_name = user_data.get('trainer_name', 'your trainer') if user_data else 'your trainer'
            response = (
                f"👋 Hi {name}! Here's what you can do:\n\n"
                "🔧 *Profile Commands:*\n"
                "• `/profile` - View your client profile\n"
                "• `/edit_profile` - Update your profile info\n"
                "• `/trainer` - View {trainer_name}'s info\n\n"
                "�  *Find Trainers:*\n"
                "• `/find_trainer` - Get help finding trainers\n"
                "• `/request_trainer [email/phone]` - Request specific trainer\n"
                "• `/add_trainer [email/phone]` - Add trainer directly\n"
                "• `/invitations` - View trainer invitations\n\n"
                "💬 *General:*\n"
                "• Just chat with me for fitness guidance\n"
                "• Ask about workouts, nutrition, or goals\n"
                "• Say 'trainer john@email.com' to find trainers\n\n"
                "🔄 *Role Switching:*\n"
                "• Use 'Switch Role' button if you're also a trainer\n\n"
                "Need help with your fitness journey? Just ask! 💪"
            )
        else:
            response = (
                "👋 Welcome to Refiloe! Here's how to get started:\n\n"
                "🚀 *Getting Started:*\n"
                "• `/registration` - Register as a trainer or client\n"
                "• Just say 'Hi' to start the registration process\n\n"
                "💬 *General:*\n"
                "• Chat with me for fitness and training advice\n"
                "• Ask questions about health and wellness\n\n"
                "Ready to transform your fitness journey? Let's go! 🏃‍♀️"
            )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling help command: {str(e)}")
        return {'success': False, 'error': str(e)}
