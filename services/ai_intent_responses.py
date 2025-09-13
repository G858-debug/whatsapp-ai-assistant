"""AI response generation for intent handling"""
import random
from typing import Dict, List
from utils.logger import log_info

class AIResponseGenerator:
    """Generate contextual responses based on intent"""
    
    def __init__(self):
        # Casual conversation responses
        self.casual_responses = {
            'status_check': [
                "Yes {name}, I'm here! 😊 Just chilling in the cloud, ready when you need me.",
                "I'm always here for you, {name}! 24/7, rain or shine ☀️",
                "Yep, still here {name}! Not going anywhere 😄",
                "Present and accounted for! What's on your mind, {name}?"
            ],
            'casual_chat': [
                "I'm doing great, {name}! Just here helping trainers and clients stay fit. How are things with you?",
                "All good on my end! How's your day going, {name}?",
                "Can't complain - living the AI dream! 😄 How are you doing?",
                "I'm well, thanks for asking! How's the fitness world treating you?"
            ],
            'thanks': [
                "You're welcome, {name}! Always happy to help 😊",
                "My pleasure! That's what I'm here for 💪",
                "Anytime, {name}! 🙌",
                "No worries at all! Glad I could help."
            ],
            'farewell': [
                "Chat soon, {name}! Have an awesome day! 👋",
                "Later, {name}! Stay strong! 💪",
                "Bye {name}! Catch you later 😊",
                "See you soon! Don't be a stranger!"
            ],
            'greeting': [
                "Hey {name}! 👋 How can I help you today?",
                "Hi {name}! Good to hear from you 😊 What can I do for you?",
                "Hello {name}! How's it going? What brings you here today?",
                "Hey there {name}! 🙌 What's on your fitness agenda?"
            ]
        }
        
        # Positive sentiment responses
        self.positive_responses = [
            "I'm doing well",
            "I'm good",
            "doing good",
            "great thanks",
            "all good",
            "can't complain",
            "not bad"
        ]
        
        # Helpful responses after positive sentiment
        self.helpful_responses = [
            "That's great to hear, {name}! 😊 Is there anything I can help you with today?",
            "Glad you're doing well! What can I do for you today, {name}?",
            "Awesome! 💪 How can I assist you today?",
            "Good to hear! Is there something specific you'd like help with?",
            "That's wonderful! What brings you to chat with me today?"
        ]
    
    def generate_response(self, intent_data: Dict, sender_type: str, 
                         sender_data: Dict) -> str:
        """Generate a contextual response"""
        intent = intent_data.get('primary_intent')
        name = sender_data.get('name', 'there')
        tone = intent_data.get('conversation_tone', 'friendly')
        response_type = intent_data.get('suggested_response_type', 'conversational')
        
        # Check for casual responses
        if intent in self.casual_responses:
            return random.choice(self.casual_responses[intent]).format(name=name)
        
        # Check for positive sentiment
        message_lower = intent_data.get('extracted_data', {}).get('original_message', '').lower()
        if self._is_positive_sentiment(message_lower):
            return random.choice(self.helpful_responses).format(name=name)
        
        # Generate contextual response
        if response_type == 'conversational':
            return self._generate_conversational_response(intent, name, sender_type)
        else:
            return self._generate_task_response(intent, name, sender_type)
    
    def _is_positive_sentiment(self, message: str) -> bool:
        """Check if message has positive sentiment"""
        return any(phrase in message for phrase in self.positive_responses)
    
    def _generate_conversational_response(self, intent: str, name: str, 
                                         sender_type: str) -> str:
        """Generate conversational response"""
        if intent == 'unclear':
            clarifications = [
                f"I didn't quite catch that, {name}. Could you rephrase that for me?",
                f"Hmm, not sure I understood that correctly. What would you like help with?",
                f"Sorry {name}, I'm a bit confused. What can I help you with today?"
            ]
            return random.choice(clarifications)
        
        elif intent == 'general_question':
            pivots = [
                f"That's interesting, {name}! By the way, is there anything specific I can help you with today?",
                f"Cool! So {name}, what can I assist you with? Bookings, workouts, or something else?",
                f"Nice! How can I make your fitness journey easier today?",
                f"Got it! What would you like to work on today - scheduling, habits, or something else?"
            ]
            return random.choice(pivots)
        
        else:
            return f"I see! So {name}, what can I help you with today? I can assist with bookings, workouts, habits, and more!"
    
    def _generate_task_response(self, intent: str, name: str, 
                               sender_type: str) -> str:
        """Generate task-oriented response"""
        if sender_type == 'trainer':
            return f"Let me help you with that, {name}. Are you looking to manage clients, check your schedule, or something else?"
        else:
            return f"Let me help you with that, {name}. Would you like to book a session, check your progress, or something else?"