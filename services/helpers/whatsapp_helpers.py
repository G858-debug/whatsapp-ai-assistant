"""WhatsApp-specific helper functions"""
from typing import List, Dict

class WhatsAppHelpers:
    """Helper functions for WhatsApp formatting and buttons"""
    
    def format_button_title(self, title: str, max_length: int = 20) -> str:
        """Ensure button title meets WhatsApp's length requirements"""
        if len(title) <= max_length:
            return title
        
        # Truncate and add ellipsis
        return title[:max_length-2] + '..'
    
    def create_button_list(self, buttons_data: List[Dict]) -> List[Dict]:
        """Create properly formatted button list"""
        formatted_buttons = []
        
        for button in buttons_data[:3]:  # WhatsApp allows max 3 buttons
            formatted_buttons.append({
                'type': 'reply',
                'reply': {
                    'id': button.get('id', 'button'),
                    'title': self.format_button_title(button.get('title', 'Option'))
                }
            })
        
        return formatted_buttons
    
    def format_whatsapp_message(self, text: str) -> str:
        """Format text for WhatsApp with proper styling"""
        # Ensure message doesn't exceed WhatsApp's limit
        if len(text) > 1600:
            text = text[:1597] + '...'
        
        return text
    
    def split_long_message(self, text: str, max_length: int = 1600) -> List[str]:
        """Split long message into multiple parts"""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        current = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_length:
                if current:
                    current += '\n\n'
                current += para
            else:
                if current:
                    messages.append(current)
                current = para
        
        if current:
            messages.append(current)
        
        return messages