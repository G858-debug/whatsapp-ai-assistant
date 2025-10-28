"""
Intent Detector
Handles AI-powered intent detection using Claude
"""
from typing import Dict
import json
import re
from utils.logger import log_info, log_error
from .ai_client import AIClient
from ..utils.prompt_builder import PromptBuilder


class IntentDetector:
    """Handles AI intent detection"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.prompt_builder = PromptBuilder()
    
    def is_available(self) -> bool:
        """Check if intent detection is available"""
        return self.ai_client.is_available()
    
    def detect_intent(self, message: str, role: str, context: Dict) -> Dict:
        """Detect user intent using AI"""
        try:
            if not self.ai_client.is_available():
                return self._get_default_intent()
            
            # Build prompt
            prompt = self.prompt_builder.build_intent_prompt(message, role, context)
            
            # Call Claude API
            response_text = self.ai_client.send_message(prompt)
            
            # Parse response
            intent = self._parse_intent_response(response_text)
            
            log_info(f"AI detected intent: {intent.get('intent')} (confidence: {intent.get('confidence')})")
            
            return intent
            
        except Exception as e:
            log_error(f"Error detecting intent: {str(e)}")
            return self._get_default_intent()
    
    def _parse_intent_response(self, response_text: str) -> Dict:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI response: {e}")
            return self._get_default_intent()
    
    def _get_default_intent(self) -> Dict:
        """Get default intent when AI is unavailable"""
        return {
            'intent': 'general_conversation',
            'confidence': 0.3,
            'needs_action': False,
            'suggested_command': None,
            'user_sentiment': 'neutral'
        }