"""Validation and enrichment for AI intent detection"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from dateutil import parser
import re
from utils.logger import log_error

class AIIntentValidator:
    """Validate and enrich AI-detected intents"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def validate_intent(self, intent_data: Dict, sender_data: Dict, 
                        sender_type: str) -> Dict:
        """Validate and enrich the AI's intent understanding"""
        # Ensure required fields
        intent_data.setdefault('primary_intent', 'general_question')
        intent_data.setdefault('confidence', 0.5)
        intent_data.setdefault('extracted_data', {})
        intent_data.setdefault('requires_confirmation', False)
        intent_data.setdefault('suggested_response_type', 'conversational')
        intent_data.setdefault('conversation_tone', 'friendly')
        
        # Validate client names if trainer
        if sender_type == 'trainer' and intent_data['extracted_data'].get('client_name'):
            self._validate_client_name(intent_data, sender_data)
        
        # Parse dates/times
        if intent_data['extracted_data'].get('date_time'):
            self._parse_datetime(intent_data)
        
        # Process habit responses
        if intent_data['extracted_data'].get('habit_responses'):
            self._process_habit_responses(intent_data)
        
        return intent_data
    
    def _validate_client_name(self, intent_data: Dict, sender_data: Dict):
        """Validate client name against actual clients"""
        client_name = intent_data['extracted_data']['client_name']
        
        clients = self.db.table('clients').select('id, name').eq(
            'trainer_id', sender_data['id']
        ).execute()
        
        if clients.data:
            matched_client = self._fuzzy_match_client(client_name, clients.data)
            if matched_client:
                intent_data['extracted_data']['client_id'] = matched_client['id']
                intent_data['extracted_data']['client_name'] = matched_client['name']
            else:
                intent_data['extracted_data']['client_name_unmatched'] = client_name
                del intent_data['extracted_data']['client_name']
    
    def _fuzzy_match_client(self, search_name: str, clients: List[Dict]) -> Optional[Dict]:
        """Find best matching client name"""
        search_lower = search_name.lower()
        
        for client in clients:
            client_lower = client['name'].lower()
            # Exact match
            if search_lower == client_lower:
                return client
            # Partial match
            if search_lower in client_lower or client_lower in search_lower:
                return client
            # First name match
            if search_lower.split()[0] == client_lower.split()[0]:
                return client
        
        return None
    
    def _parse_datetime(self, intent_data: Dict):
        """Parse datetime string to SA timezone"""
        time_str = intent_data['extracted_data']['date_time']
        
        try:
            parsed_time = self.parse_datetime(time_str)
            if parsed_time:
                intent_data['extracted_data']['parsed_datetime'] = parsed_time.isoformat()
        except Exception as e:
            log_error(f"Error parsing datetime: {str(e)}")
    
    def parse_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse various datetime formats to SA timezone"""
        try:
            time_lower = time_str.lower()
            now = datetime.now(self.sa_tz)
            
            # Handle relative times
            if 'tomorrow' in time_lower:
                base_date = now + timedelta(days=1)
            elif 'today' in time_lower:
                base_date = now
            elif 'monday' in time_lower:
                days_ahead = 0 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                base_date = now + timedelta(days=days_ahead)
            else:
                # Try direct parsing
                parsed = parser.parse(time_str, fuzzy=True)
                return self.sa_tz.localize(parsed) if parsed.tzinfo is None else parsed
            
            # Extract time
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                meridiem = time_match.group(3)
                
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
        except Exception as e:
            log_error(f"Error parsing datetime '{time_str}': {str(e)}")
            return None
    
    def _process_habit_responses(self, intent_data: Dict):
        """Process habit tracking responses"""
        responses = intent_data['extracted_data']['habit_responses']
        processed = []
        
        for response in responses:
            response_lower = str(response).lower()
            
            # Yes/no responses
            if response_lower in ['yes', '✅', 'done', 'complete', '👍']:
                processed.append({'completed': True, 'value': None})
            elif response_lower in ['no', '❌', 'skip', 'missed', '👎']:
                processed.append({'completed': False, 'value': None})
            # Numeric values
            elif response_lower.replace('.', '').isdigit():
                processed.append({'completed': True, 'value': float(response_lower)})
            # Fractions
            elif '/' in response_lower:
                parts = response_lower.split('/')
                if len(parts) == 2 and parts[0].isdigit():
                    processed.append({'completed': True, 'value': float(parts[0])})
            else:
                # Extract numbers
                numbers = re.findall(r'\d+', response_lower)
                if numbers:
                    processed.append({'completed': True, 'value': float(numbers[0])})
                else:
                    processed.append({'completed': False, 'value': None})
        
        intent_data['extracted_data']['processed_habit_responses'] = processed