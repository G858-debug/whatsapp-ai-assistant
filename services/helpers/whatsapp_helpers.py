"""WhatsApp-specific helper functions"""
from typing import Dict, List, Optional
import re
from utils.logger import log_info, log_error

class WhatsAppHelpers:
    """Helper functions for WhatsApp formatting and parsing"""
    
    @staticmethod
    def format_bold(text: str) -> str:
        """Format text as bold for WhatsApp"""
        return f"*{text}*"
    
    @staticmethod
    def format_italic(text: str) -> str:
        """Format text as italic for WhatsApp"""
        return f"_{text}_"
    
    @staticmethod
    def format_strikethrough(text: str) -> str:
        """Format text as strikethrough for WhatsApp"""
        return f"~{text}~"
    
    @staticmethod
    def format_monospace(text: str) -> str:
        """Format text as monospace for WhatsApp"""
        return f"```{text}```"
    
    @staticmethod
    def create_menu(title: str, options: List[Dict[str, str]]) -> str:
        """Create a formatted menu for WhatsApp"""
        menu = f"*{title}*\n\n"
        for i, option in enumerate(options, 1):
            menu += f"{i}. {option.get('label', '')}\n"
            if option.get('description'):
                menu += f"   _{option['description']}_\n"
        return menu
    
    @staticmethod
    def parse_phone_number(phone: str) -> str:
        """Parse and format South African phone number"""
        # Remove all non-digits
        phone = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if phone.startswith('27'):
            return phone  # Already in international format
        elif phone.startswith('0'):
            return '27' + phone[1:]  # Convert from local format
        else:
            return '27' + phone  # Assume it's missing country code
    
    @staticmethod
    def truncate_message(message: str, max_length: int = 1600) -> str:
        """Truncate message to WhatsApp's character limit"""
        if len(message) <= max_length:
            return message
        
        # Find a good break point
        truncated = message[:max_length - 20]
        
        # Try to break at a sentence
        last_period = truncated.rfind('.')
        if last_period > max_length - 200:
            truncated = truncated[:last_period + 1]
        else:
            # Break at last space
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]
        
        return truncated + "\n\n[Message truncated]"
    
    @staticmethod
    def extract_command(message: str) -> Optional[str]:
        """Extract command from message"""
        message_lower = message.lower().strip()
        
        # Common commands
        commands = [
            'help', 'register', 'book', 'cancel', 'schedule',
            'add client', 'send workout', 'my progress', 'log',
            'payment', 'settings', 'profile', 'stats'
        ]
        
        for command in commands:
            if message_lower.startswith(command):
                return command
        
        return None