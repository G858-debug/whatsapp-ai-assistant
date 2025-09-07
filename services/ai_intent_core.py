"""Core AI intent detection functionality"""
import json
import anthropic
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning

class AIIntentCore:
    """Core AI intent detection"""
    
    def __init__(self, config):
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        if config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"
            log_info("AI Intent Handler initialized with Claude")
        else:
            self.client = None
            log_warning("No Anthropic API key - falling back to keyword matching")
    
    def understand_message(self, message: str, sender_type: str,
                          sender_data: Dict, conversation_history: List[str] = None) -> Dict:
        """Main entry point - understands any message using AI"""
        
        if not self.client:
            log_info(f"Using fallback intent detection for: {message[:50]}")
            return self._fallback_intent_detection(message, sender_type)
        
        try:
            context = self._build_context(sender_type, sender_data)
            prompt = self._create_intent_prompt(message, sender_type, context, conversation_history)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            intent_data = self._parse_ai_response(response.content[0].text)
            validated_intent = self._validate_intent(intent_data, sender_data, sender_type)
            
            log_info(f"AI Intent detected: {validated_intent.get('primary_intent')} "
                    f"with confidence {validated_intent.get('confidence')}")
            
            return validated_intent
            
        except Exception as e:
            log_error(f"AI intent understanding failed: {str(e)}", exc_info=True)
            return self._fallback_intent_detection(message, sender_type)
    
    def _build_context(self, sender_type: str, sender_data: Dict) -> Dict:
        """Build context based on sender type"""
        if sender_type == 'trainer':
            return {
                'name': sender_data.get('name', 'Trainer'),
                'id': sender_data.get('id'),
                'whatsapp': sender_data.get('whatsapp'),
                'business_name': sender_data.get('business_name'),
                'active_clients': sender_data.get('active_clients', 0)
            }
        else:
            return {
                'name': sender_data.get('name', 'Client'),
                'id': sender_data.get('id'),
                'whatsapp': sender_data.get('whatsapp'),
                'trainer_name': sender_data.get('trainer_name', 'your trainer'),
                'sessions_remaining': sender_data.get('sessions_remaining', 0)
            }
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse the AI's JSON response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI response: {e}")
            return {
                'primary_intent': 'unclear',
                'confidence': 0.3,
                'extracted_data': {},
                'sentiment': 'neutral',
                'suggested_response_type': 'conversational'
            }
    
    def _validate_intent(self, intent_data: Dict, sender_data: Dict, sender_type: str) -> Dict:
        """Validate and enrich the AI's intent understanding"""
        intent_data.setdefault('primary_intent', 'general_question')
        intent_data.setdefault('confidence', 0.5)
        intent_data.setdefault('extracted_data', {})
        intent_data.setdefault('requires_confirmation', False)
        intent_data.setdefault('suggested_response_type', 'conversational')
        intent_data.setdefault('conversation_tone', 'friendly')
        return intent_data
    
    def _fallback_intent_detection(self, message: str, sender_type: str) -> Dict:
        """Basic keyword-based intent detection when AI is unavailable"""
        message_lower = message.lower()
        
        casual_keywords = {
            'status_check': ['are you there', 'you there', 'still there'],
            'greeting': ['hi', 'hello', 'hey', 'howzit', 'sawubona'],
            'thanks': ['thanks', 'thank you', 'appreciate'],
            'farewell': ['bye', 'goodbye', 'see you'],
            'casual_chat': ['how are you', 'what\'s up'],
        }
        
        for intent, keywords in casual_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return {
                        'primary_intent': intent,
                        'secondary_intents': [],
                        'confidence': 0.8,
                        'extracted_data': {},
                        'sentiment': 'friendly',
                        'requires_confirmation': False,
                        'suggested_response_type': 'conversational',
                        'conversation_tone': 'casual',
                        'is_follow_up': False
                    }
        
        return {
            'primary_intent': 'general_question',
            'secondary_intents': [],
            'confidence': 0.3,
            'extracted_data': {},
            'sentiment': 'neutral',
            'requires_confirmation': False,
            'suggested_response_type': 'task',
            'conversation_tone': 'friendly',
            'is_follow_up': False
        }

    def _create_intent_prompt(self, message: str, sender_type: str, 
                             context: Dict, history: List[str]) -> str:
        """Create prompt for Claude"""
        return f"""Analyze this WhatsApp message to Refiloe, an AI assistant for personal trainers.

SENDER: {sender_type} ({context.get('name', 'Unknown')})
MESSAGE: "{message}"

Return ONLY valid JSON with primary_intent, confidence, extracted_data, sentiment, and suggested_response_type."""