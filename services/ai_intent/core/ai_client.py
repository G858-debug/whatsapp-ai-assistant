"""
AI Client Manager
Manages Claude API client and interactions
"""
import anthropic
from config import Config
from utils.logger import log_info, log_error


class AIClient:
    """Manages Claude AI client"""
    
    def __init__(self):
        self.client = None
        self.model = "claude-sonnet-4-20250514"
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Claude client"""
        try:
            if Config.ANTHROPIC_API_KEY:
                self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
                log_info("Claude AI client initialized successfully")
            else:
                log_error("No Anthropic API key - AI client disabled")
        except Exception as e:
            log_error(f"Error initializing AI client: {str(e)}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if AI client is available"""
        return self.client is not None
    
    def send_message(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """Send message to Claude and get response"""
        try:
            if not self.client:
                raise Exception("AI client not available")
            
            response = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.content[0].text
            
        except Exception as e:
            log_error(f"Error sending message to AI: {str(e)}")
            raise