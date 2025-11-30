"""
 Handle Client Invitations Command
Handle /invitations command - show client's trainer invitations
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_client_invitations_command(self, phone: str, user_data: dict) -> Dict:
    """Handle /invitations command - show client's trainer invitations"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Get pending invitations for this client
        pending_invitations = self.db.table('client_invitations').select('*').eq('client_phone', phone).eq('status', 'pending').execute()
        
        if not pending_invitations.data:
            response = (
                "📧 *No Pending Invitations*\n\n"
                "You don't have any pending trainer invitations at the moment.\n\n"
                "💡 *To connect with trainers:*\n"
                "• Use `/find_trainer` to search for trainers\n"
                "• Ask friends for trainer recommendations\n"
                "• If you know a trainer's email, say 'trainer [email]'\n\n"
                "Ready to start your fitness journey? 💪"
            )
        else:
            invitation_count = len(pending_invitations.data)
            
            response = f"📧 *Trainer Invitations ({invitation_count})*\n\n"
            
            for i, invitation in enumerate(pending_invitations.data, 1):
                trainer_id = invitation['trainer_id']
                invitation_token = invitation['invitation_token']
                invited_date = invitation['created_at'][:10]
                expires_date = invitation['expires_at'][:10]
                custom_message = invitation.get('message', '')
                
                # Get trainer info
                trainer_result = self.db.table('trainers').select('name, business_name, email').eq('id', trainer_id).execute()
                
                if trainer_result.data:
                    trainer_info = trainer_result.data[0]
                    trainer_name = trainer_info.get('name', 'Unknown Trainer')
                    business_name = trainer_info.get('business_name', f"{trainer_name}'s Training")
                    trainer_email = trainer_info.get('email', '')
                    
                    response += f"{i}. 🏋️ **{business_name}**\n"
                    response += f"   👨‍💼 Trainer: {trainer_name}\n"
                    response += f"   📧 Email: {trainer_email}\n"
                    response += f"   📅 Invited: {invited_date}\n"
                    response += f"   ⏰ Expires: {expires_date}\n"
                    
                    if custom_message:
                        response += f"   💬 Message: \"{custom_message}\"\n"
                    
                    response += f"   ✅ `/accept_invitation {invitation_token[:8]}`\n"
                    response += f"   ❌ `/decline_invitation {invitation_token[:8]}`\n\n"
            
            response += "💡 *Quick Actions:*\n"
            response += "• Reply with the accept/decline commands above\n"
            response += "• Or just say 'accept [trainer name]' or 'decline [trainer name]'"
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        log_error(f"Error handling client invitations command: {str(e)}")
        return {'success': False, 'error': str(e)}
