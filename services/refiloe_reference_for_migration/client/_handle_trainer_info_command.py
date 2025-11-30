"""
 Handle Trainer Info Command
Handle /trainer command - show client's trainer info
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_trainer_info_command(self, phone: str, user_data: dict) -> Dict:
    """Handle /trainer command - show client's trainer info"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Get trainer info from client data
        trainer_info = user_data.get('trainers') if user_data else None
        
        if not trainer_info:
            response = (
                "❌ No trainer assigned yet.\n\n"
                "🔍 *Find a Trainer:*\n"
                "• Say 'I need a trainer'\n"
                "• Browse available trainers in your area\n\n"
                "💬 *Have a specific trainer?*\n"
                "Ask them for their WhatsApp number and message them directly!"
            )
        else:
            trainer_name = trainer_info.get('name', 'Unknown')
            business_name = trainer_info.get('business_name', 'Not provided')
            specialization = trainer_info.get('specialization', 'General Fitness')
            
            response = (
                f"👨‍💼 *Your Trainer: {trainer_name}*\n\n"
                f"🏢 Business: {business_name}\n"
                f"🎯 Specialization: {specialization}\n\n"
                f"📱 *Contact:*\n"
                f"• Message them directly for sessions\n"
                f"• Ask about scheduling and availability\n\n"
                f"💪 *Need Help?*\n"
                f"Just ask me about workouts, nutrition, or fitness goals!"
            )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling trainer info command: {str(e)}")
        return {'success': False, 'error': str(e)}
