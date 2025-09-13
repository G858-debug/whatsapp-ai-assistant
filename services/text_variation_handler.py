"""Handler for text variations, typos, and local terms"""
from typing import Optional, List, Dict
import re
from difflib import SequenceMatcher
from utils.logger import log_info, log_warning

class TextVariationHandler:
    """Handles text variations, typos, and local South African terms"""
    
    def __init__(self):
        # Yes variations (including SA terms)
        self.yes_variations = [
            'yes', 'y', 'yeah', 'yep', 'ya', 'yah', 'yup', 'sure', 'ok', 'okay',
            'confirm', 'correct', 'right', 'affirmative', 'definitely', 'absolutely',
            'ja', 'jy', 'yebo', 'sharp', 'sho', 'hundred', '100', 'cool', 'kiff',
            'lekker', 'aweh', 'awe', '✅', '👍', '👌', 'good', 'great', 'perfect',
            'thats right', "that's right", 'thats correct', "that's correct",
            'all good', 'its good', "it's good", 'looks good', 'go ahead'
        ]
        
        # No variations (including SA terms)
        self.no_variations = [
            'no', 'n', 'nope', 'nah', 'negative', 'incorrect', 'wrong', 'cancel',
            'stop', 'exit', 'quit', 'nee', 'aikona', 'hayi', 'never', '❌', '👎',
            'not right', 'thats wrong', "that's wrong", 'mistake', 'error',
            'dont want', "don't want", 'not interested', 'no thanks', 'no thank you'
        ]
        
        # Edit variations
        self.edit_variations = [
            'edit', 'change', 'modify', 'update', 'fix', 'correct', 'alter',
            'revise', 'adjust', 'amend', 'redo', 'back', 'go back', 'previous',
            'mistake', 'wrong', 'incorrect', 'not right', 'let me change',
            'want to change', 'need to change', 'can i change', 'can i edit'
        ]
        
        # Registration intent variations
        self.trainer_variations = [
            'trainer', 'coach', 'instructor', 'fitness professional', 'pt',
            'personal trainer', 'i train', 'i coach', 'im a trainer',
            "i'm a trainer", 'fitness coach', 'gym instructor'
        ]
        
        self.client_variations = [
            'client', 'looking for trainer', 'need trainer', 'want trainer',
            'find trainer', 'get fit', 'need help', 'looking for pt',
            'need coach', 'want to train', 'fitness help', 'gym help',
            'looking for coach', 'need personal trainer'
        ]
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase and remove extra spaces
        text = text.lower().strip()
        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s']", '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def fuzzy_match(self, text: str, variations: List[str], threshold: float = 0.8) -> bool:
        """Check if text fuzzy matches any variation"""
        normalized = self.normalize_text(text)
        
        for variation in variations:
            # Direct match
            if variation in normalized or normalized in variation:
                return True
            
            # Fuzzy match using SequenceMatcher
            similarity = SequenceMatcher(None, normalized, variation).ratio()
            if similarity >= threshold:
                return True
            
            # Word-level match
            words = normalized.split()
            var_words = variation.split()
            if any(word in var_words for word in words):
                if len(words) <= 3:  # Short responses
                    return True
        
        return False
    
    def understand_confirmation_response(self, text: str) -> str:
        """Understand user's response to confirmation prompt"""
        # Check for yes
        if self.fuzzy_match(text, self.yes_variations):
            return 'yes'
        
        # Check for no
        if self.fuzzy_match(text, self.no_variations):
            return 'no'
        
        # Check for edit
        if self.fuzzy_match(text, self.edit_variations):
            return 'edit'
        
        # Check for specific field mentions
        normalized = self.normalize_text(text)
        field_keywords = {
            'name': ['name', 'my name'],
            'email': ['email', 'mail', 'address'],
            'phone': ['phone', 'number', 'whatsapp'],
            'business': ['business', 'company', 'gym'],
            'location': ['location', 'area', 'where'],
            'price': ['price', 'rate', 'cost', 'fee'],
            'goals': ['goals', 'objectives', 'aims'],
            'emergency': ['emergency', 'contact']
        }
        
        for field, keywords in field_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                return 'edit'
        
        return 'unclear'
    
    def normalize_registration_intent(self, text: str) -> Optional[str]:
        """Determine if user wants to register as trainer or client"""
        # Check for trainer intent
        if self.fuzzy_match(text, self.trainer_variations, threshold=0.7):
            return 'trainer'
        
        # Check for client intent
        if self.fuzzy_match(text, self.client_variations, threshold=0.7):
            return 'client'
        
        # Check for button responses
        normalized = self.normalize_text(text)
        if any(word in normalized for word in ['trainer', 'coach', 'pt']):
            return 'trainer'
        if any(word in normalized for word in ['client', 'find', 'looking', 'need']):
            return 'client'
        
        return None
    
    def extract_field_from_edit_request(self, text: str) -> Optional[str]:
        """Extract which field user wants to edit from their message"""
        normalized = self.normalize_text(text)
        
        # Field mappings
        field_patterns = {
            'name': r'\b(name|full name|my name)\b',
            'email': r'\b(email|mail|email address)\b',
            'phone': r'\b(phone|number|whatsapp|cell)\b',
            'business': r'\b(business|company|gym|studio)\b',
            'location': r'\b(location|area|address|where)\b',
            'price': r'\b(price|rate|cost|fee|charge)\b',
            'specialties': r'\b(specialt|skill|expertise|focus)\b',
            'goals': r'\b(goal|objective|aim|target)\b',
            'emergency': r'\b(emergency|contact person|emergency contact)\b',
            'fitness_level': r'\b(fitness level|level|experience)\b'
        }
        
        for field, pattern in field_patterns.items():
            if re.search(pattern, normalized):
                return field
        
        return None
    
    def is_skip_response(self, text: str) -> bool:
        """Check if user wants to skip a field"""
        skip_variations = [
            'skip', 'none', 'na', 'n/a', 'not applicable', 'dont have',
            "don't have", 'nothing', 'leave blank', 'blank', 'empty',
            'pass', 'next', 'no comment', '-', '--', 'nil'
        ]
        
        return self.fuzzy_match(text, skip_variations, threshold=0.85)
    
    def is_help_request(self, text: str) -> bool:
        """Check if user is asking for help"""
        help_variations = [
            'help', 'what', 'how', 'explain', 'dont understand',
            "don't understand", 'confused', 'not sure', 'what do you mean',
            'what should i', 'example', 'like what', 'such as', '?'
        ]
        
        return self.fuzzy_match(text, help_variations, threshold=0.7)
    
    def clean_price_input(self, text: str) -> Optional[float]:
        """Extract and clean price from various formats"""
        # Remove currency symbols and text
        text = re.sub(r'[Rr](?:and)?s?\.?', '', text)
        text = re.sub(r'per\s+(session|hour|class)', '', text, flags=re.IGNORECASE)
        
        # Find numbers (including decimals)
        numbers = re.findall(r'\d+(?:\.\d{2})?', text)
        
        if numbers:
            try:
                price = float(numbers[0])
                # Sanity check
                if 0 < price < 10000:
                    return price
            except ValueError:
                pass
        
        return None
    
    def clean_phone_input(self, text: str) -> Optional[str]:
        """Clean and validate phone number input"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', text)
        
        # Handle different formats
        if len(digits) == 10 and digits.startswith('0'):
            # Local format: 0821234567
            return '27' + digits[1:]
        elif len(digits) == 11 and digits.startswith('27'):
            # International format: 27821234567
            return digits
        elif len(digits) == 9:
            # Missing leading 0: 821234567
            return '27' + digits
        
        return None
    
    def spell_check_common_words(self, text: str) -> str:
        """Fix common spelling mistakes in fitness context"""
        corrections = {
            'wieght': 'weight',
            'weigth': 'weight',
            'strenght': 'strength',
            'cardoi': 'cardio',
            'yogha': 'yoga',
            'pillates': 'pilates',
            'crosssfit': 'crossfit',
            'nutrtion': 'nutrition',
            'protien': 'protein',
            'suppliments': 'supplements'
        }
        
        normalized = text.lower()
        for wrong, correct in corrections.items():
            normalized = normalized.replace(wrong, correct)
        
        return normalized