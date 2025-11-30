"""
 Handle Edit Profile Command
Handle /edit_profile command - start profile editing process using WhatsApp Flow
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_edit_profile_command(self, phone: str, user_type: str, user_data: dict) -> Dict:
    """Handle /edit_profile command - start profile editing process using WhatsApp Flow"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        if not user_data:
            response = "❌ No profile found. Please register first by saying 'Hi' or using `/registration`."
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Try to send WhatsApp Flow for profile editing
        try:
            flow_result = self._send_profile_edit_flow(phone, user_type, user_data)
            
            if flow_result.get('success'):
                return flow_result
            else:
                # Fallback to instructions if flow fails
                log_warning(f"Profile edit flow failed for {phone}: {flow_result.get('error')}")
                
        except Exception as flow_error:
            log_error(f"Error sending profile edit flow: {str(flow_error)}")
        
        # Fallback: Provide instructions for manual editing
        name = user_data.get('name', 'there')
        
        if user_type == 'trainer':
            response = (
                f"✏️ *Edit Your Trainer Profile*\n\n"
                f"Hi {name}! I'd love to help you update your profile, but the editing flow isn't available right now.\n\n"
                f"📧 *To update your profile:*\n"
                f"• Email us at: support@refiloe.ai\n"
                f"• Include your WhatsApp number: {phone}\n"
                f"• Specify what you'd like to change\n\n"
                f"🔄 *Alternative:*\n"
                f"• Tell me what you'd like to update and I'll help you contact support\n\n"
                f"💡 *Tip:* Type `/profile` to see your current info"
            )
        else:
            response = (
                f"✏️ *Edit Your Client Profile*\n\n"
                f"Hi {name}! I'd love to help you update your profile, but the editing flow isn't available right now.\n\n"
                f"📧 *To update your profile:*\n"
                f"• Email us at: support@refiloe.ai\n"
                f"• Include your WhatsApp number: {phone}\n"
                f"• Specify what you'd like to change\n\n"
                f"🔄 *Alternative:*\n"
                f"• Tell me what you'd like to update and I'll help you contact support\n\n"
                f"💡 *Tip:* Type `/profile` to see your current info"
            )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling edit profile command: {str(e)}")
        return {'success': False, 'error': str(e)}
