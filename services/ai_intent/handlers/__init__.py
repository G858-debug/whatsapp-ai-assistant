"""
AI Intent Handlers Package
Contains intent-specific handlers for different user roles
"""

from .trainer_intent_handler import TrainerIntentHandler
from .client_intent_handler import ClientIntentHandler
from .common_intent_handler import CommonIntentHandler

__all__ = [
    'TrainerIntentHandler',
    'ClientIntentHandler',
    'CommonIntentHandler'
]