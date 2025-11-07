"""
Main AI Intent Handler
Coordinates intent detection and response generation
"""
from typing import Dict, List
import pytz
from utils.logger import log_info, log_error
from config import Config

from .core.context_builder import ContextBuilder
from .core.intent_detector import IntentDetector
from .core.response_generator import ResponseGenerator
from .utils.fallback_responses import FallbackResponseHandler


class AIIntentHandler:
    """Main AI Intent Handler - coordinates all AI intent processing"""
    
    def __init__(self, db_or_config, whatsapp_or_supabase=None, services_dict_or_task_service=None):
        """
        Initialize AIIntentHandler with flexible parameters for backward compatibility
        
        Can be called as:
        - AIIntentHandler(db, whatsapp) - Phase 1-3 style
        - AIIntentHandler(db, whatsapp, task_service) - message_router style
        - AIIntentHandler(Config, supabase, services_dict) - app_core.py style
        """
        # Handle different calling conventions (preserve existing API)
        if isinstance(services_dict_or_task_service, dict):
            # Called from app_core.py: (Config, supabase, services_dict)
            self.config = db_or_config
            self.db = whatsapp_or_supabase
            self.whatsapp = services_dict_or_task_service.get('whatsapp') if services_dict_or_task_service else None
            self.services = services_dict_or_task_service
            self.task_service = services_dict_or_task_service.get('task_service') if services_dict_or_task_service else None
        else:
            # Called from message_router: (db, whatsapp, task_service)
            self.db = db_or_config
            self.whatsapp = whatsapp_or_supabase
            self.task_service = services_dict_or_task_service
            self.config = None
            self.services = None
        
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize components
        self.context_builder = ContextBuilder(self.db)
        self.intent_detector = IntentDetector()
        self.response_generator = ResponseGenerator(self.db, self.whatsapp, self.task_service)
        self.fallback_handler = FallbackResponseHandler()
        
        log_info("AI Intent Handler (Phases 1-3) initialized with modular structure")
    
    def handle_intent(self, phone: str, message: str, role: str, user_id: str,
                     recent_tasks: List[Dict], chat_history: List[Dict]) -> Dict:
        """Main entry point - analyze message and respond appropriately"""
        try:
            if not self.intent_detector.is_available():
                # Fallback to simple response
                return self.fallback_handler.get_fallback_response(phone, message, role, self.whatsapp)
            
            # Build context
            context = self.context_builder.build_context(
                phone, role, user_id, recent_tasks, chat_history
            )
            
            # Detect intent
            intent = self.intent_detector.detect_intent(message, role, context)
            
            # Generate response
            return self.response_generator.generate_response(
                phone, message, role, intent, context
            )
            
        except Exception as e:
            log_error(f"Error in AI intent handler: {str(e)}")
            return self.fallback_handler.get_fallback_response(phone, message, role, self.whatsapp)