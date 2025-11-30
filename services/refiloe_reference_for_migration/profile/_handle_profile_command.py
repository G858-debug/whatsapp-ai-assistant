"""
 Handle Profile Command
Handle /profile command - show user profile information
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_profile_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
    """Handle /profile command - show user profile information"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        if not user_data:
            response = "❌ No profile found. Please register first by saying 'Hi' or using `/registration`."
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        if user_type == 'trainer':
            # Format trainer profile
            name = user_data.get('name', 'Unknown')
            email = user_data.get('email', 'Not provided')
            business_name = user_data.get('business_name', 'Not provided')
            specialization = user_data.get('specialization', 'Not provided')
            experience = user_data.get('experience_years', user_data.get('years_experience', 'Not provided'))
            city = user_data.get('city', user_data.get('location', 'Not provided'))
            pricing = user_data.get('pricing_per_session', 'Not provided')
            
            response = (
                f"👤 *Your Trainer Profile*\n\n"
                f"📝 *Basic Info:*\n"
                f"• Name: {name}\n"
                f"• Email: {email}\n"
                f"• City: {city}\n"
                f"• Business: {business_name}\n\n"
                f"💼 *Professional Info:*\n"
                f"• Specialization: {specialization}\n"
                f"• Experience: {experience} years\n"
                f"• Rate: R{pricing}/session\n\n"
                f"📱 *Actions:*\n"
                f"• Type `/edit_profile` to update your info\n"
                f"• Type `/clients` to manage clients"
            )
        
        elif user_type == 'client':
            # Format client profile
            name = user_data.get('name', 'Unknown')
            email = user_data.get('email', 'Not provided')
            goals = user_data.get('fitness_goals', 'Not provided')
            trainer_name = user_data.get('trainer_name', 'Not assigned')
            
            response = (
                f"👤 *Your Client Profile*\n\n"
                f"📝 *Basic Info:*\n"
                f"• Name: {name}\n"
                f"• Email: {email}\n"
                f"• Fitness Goals: {goals}\n"
                f"• Trainer: {trainer_name}\n\n"
                f"📱 *Actions:*\n"
                f"• Type `/edit_profile` to update your info\n"
                f"• Type `/trainer` to view trainer details"
            )
        
        # Enhance profile with habit information
        enhanced_response = self._enhance_profile_with_habits(phone, user_type, user_data, response)
        
        whatsapp_service.send_message(phone, enhanced_response)
        return {'success': True, 'response': enhanced_response}
        
    except Exception as e:
        log_error(f"Error handling profile command: {str(e)}")
        return {'success': False, 'error': str(e)}
