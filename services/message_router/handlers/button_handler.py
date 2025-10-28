"""
Button Response Handler
Delegates button interactions to specialized handlers
"""
from typing import Dict
from utils.logger import log_info, log_error

from .buttons.button_handler import ButtonHandler as ButtonHandlerImpl


class ButtonHandler:
    """Main button handler that delegates to the implementation"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service):
        self.handler = ButtonHandlerImpl(supabase_client, whatsapp_service, auth_service)
    
    def handle_button_response(self, phone: str, button_id: str) -> Dict:
        """Delegate button response handling to the implementation"""
        return self.handler.handle_button_response(phone, button_id)
