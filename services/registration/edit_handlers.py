"""Handle registration edits and corrections"""
from typing import Dict
from utils.logger import log_info

class EditHandlers:
    """Handle edits during registration"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def handle_edit_request(self, phone: str, field_to_edit: str) -> Dict:
        """Handle request to edit a registration field"""
        # Get current registration state
        state = self.db.table('registration_states').select('*').eq(
            'phone_number', phone
        ).eq('completed', False).single().execute()
        
        if not state.data:
            return {
                'success': False,
                'message': "😅 No active registration found. Would you like to start fresh?"
            }
        
        field_prompts = {
            'name': "Sure! What's your correct name? 😊",
            'email': "No problem! What's the right email address? 📧",
            'business_name': "Let's fix that! What's your business name?",
            'pricing': "What's your correct rate per session? 💰"
        }
        
        if field_to_edit in field_prompts:
            return {
                'success': True,
                'message': field_prompts[field_to_edit],
                'editing': field_to_edit
            }
        
        return {
            'success': False,
            'message': "I can help you edit your name, email, business name, or pricing. Which one?"
        }