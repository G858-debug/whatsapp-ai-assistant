<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5402 -->
<!-- Max Tokens: 32000 -->
## ANALYSIS

Looking at Step 3 completion and the current task, I need to continue with Step 4 to finalize the registration system integration. The main issues to address are:

1. Fix the method name mismatch in the registration handlers (using underscore prefix for public methods)
2. Ensure the RefiloeService properly integrates with the new registration system
3. Add missing imports and fix any integration issues
4. Create the registration_state.py and edit_handlers.py files that are imported but don't exist

## CHANGES NEEDED

### NEW FILE: services/registration/registration_state.py
```python
"""Registration state management for multi-step flows"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class RegistrationStateManager:
    """Manages registration session state"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_session(self, phone: str, user_type: str, initial_step: str = 'name') -> str:
        """Create a new registration session"""
        try:
            # Expire any existing sessions for this phone
            self.db.table('registration_sessions').update({
                'status': 'expired'
            }).eq('phone', phone).eq('status', 'active').execute()
            
            # Create new session
            result = self.db.table('registration_sessions').insert({
                'phone': phone,
                'user_type': user_type,
                'status': 'active',
                'step': initial_step,
                'data': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
            return result.data[0]['id'] if result.data else None
            
        except Exception as e:
            log_error(f"Error creating registration session: {str(e)}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get registration session by ID"""
        try:
            result = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting session: {str(e)}")
            return None
    
    def update_session(self, session_id: str, step: str = None, 
                      data_update: Dict = None) -> bool:
        """Update registration session"""
        try:
            update_data = {
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if step:
                update_data['step'] = step
            
            if data_update:
                # Get current data
                session = self.get_session(session_id)
                if session:
                    current_data = session.get('data', {})
                    current_data.update(data_update)
                    update_data['data'] = current_data
            
            result = self.db.table('registration_sessions').update(
                update_data
            ).eq('id', session_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating session: {str(e)}")
            return False
    
    def complete_session(self, session_id: str) -> bool:
        """Mark session as completed"""
        try:
            result = self.db.table('registration_sessions').update({
                'status': 'completed',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error completing session: {str(e)}")
            return False
    
    def expire_old_sessions(self):
        """Expire sessions older than 24 hours"""
        try:
            cutoff = datetime.now(self.sa_tz) - timedelta(hours=24)
            
            self.db.table('registration_sessions').update({
                'status': 'expired'
            }).eq('status', 'active').lt(
                'updated_at', cutoff.isoformat()
            ).execute()
            
            log_info("Expired old registration sessions")
            
        except Exception as e:
            log_error(f"Error expiring sessions: {str(e)}")
```

### NEW FILE: services/registration/edit_handlers.py
```python
"""Handlers for editing registration data"""
from typing import Dict, Optional
from utils.logger import log_error, log_info

class EditHandlers:
    """Handle editing of registration information"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
    
    def handle_edit_request(self, session_id: str, field_to_edit: str) -> Dict:
        """Handle request to edit a specific field"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session not found'
                }
            
            # Map edit keywords to fields
            field_map = {
                'name': 'name',
                'email': 'email',
                'phone': 'phone',
                'business': 'business_name',
                'location': 'location',
                'specialization': 'specialization',
                'price': 'pricing',
                'trainer': 'trainer_choice'
            }
            
            # Find which field to edit
            field = None
            for key, value in field_map.items():
                if key in field_to_edit.lower():
                    field = value
                    break
            
            if not field:
                return {
                    'success': False,
                    'message': "I'm not sure which field you want to edit. You can edit: name, email, phone, business name, location, specialization, or price."
                }
            
            # Update session to go back to that step
            step_map = {
                'name': 'name',
                'email': 'email',
                'phone': 'phone',
                'business_name': 'business',
                'location': 'location',
                'specialization': 'specialization',
                'pricing': 'pricing',
                'trainer_choice': 'trainer_selection'
            }
            
            new_step = step_map.get(field, 'name')
            
            # Update session step
            self.db.table('registration_sessions').update({
                'step': new_step
            }).eq('id', session_id).execute()
            
            # Get prompt for the field
            prompts = {
                'name': "What's your full name?",
                'email': "What's your email address?",
                'phone': "What's your phone number?",
                'business_name': "What's your business name? (or 'skip' if you don't have one)",
                'location': "Where are you located? (area/suburb)",
                'specialization': "What's your training specialization?",
                'pricing': "What's your rate per session? (e.g., R350)",
                'trainer_choice': "Would you like me to find trainers in your area? Reply YES or NO"
            }
            
            return {
                'success': True,
                'message': f"Let's update that. {prompts.get(field, 'Please provide the new value:')}"
            }
            
        except Exception as e:
            log_error(f"Error handling edit request: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing edit request'
            }
    
    def validate_edit(self, field: str, value: str) -> Dict:
        """Validate edited field value"""
        try:
            if field == 'email':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                if not validator.validate_email(value):
                    return {
                        'valid': False,
                        'message': 'Please provide a valid email address'
                    }
            
            elif field == 'phone':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                formatted = validator.format_phone_number(value)
                if not formatted:
                    return {
                        'valid': False,
                        'message': 'Please provide a valid South African phone number'
                    }
                return {
                    'valid': True,
                    'formatted_value': formatted
                }
            
            elif field == 'pricing':
                from services.helpers.validation_helpers import ValidationHelpers
                validator = ValidationHelpers()
                price = validator.extract_price(value)
                if not price:
                    return {
                        'valid': False,
                        'message': 'Please provide a valid price (e.g., R350)'
                    }
                return {
                    'valid': True,
                    'formatted_value': price
                }
            
            return {'valid': True}
            
        except Exception as e:
            log_error(f"Error validating edit: {str(e)}")
            return {
                'valid': False,
                'message': 'Error validating input'
            }
```

### EDIT: services/refiloe.py

**Change 1:** Fix the method call name
Location: Lines 86-90 (in _handle_registration_flow method)
```python
# REMOVE (lines 86-90):
            if current_step == 'confirmation':
                if user_type == 'trainer':
                    return self.trainer_registration._confirm_trainer_registration(
                        session_id, input_text
                    )

# ADD:
            if current_step == 'confirmation':
                if user_type == 'trainer':
                    return self.trainer_registration.confirm_trainer_registration(
                        session_id, input_text
                    )
```

**Change 2:** Fix client confirmation method call
Location: Lines 91-93
```python
# REMOVE (lines 91-93):
                else:
                    return self.client_registration._confirm_client_registration(
                        session_id, input_text

# ADD:
                else:
                    return self.client_registration.confirm_client_registration(
                        session_id, input_text
```

**Change 3:** Add missing imports
Location: Lines 5-10 (after existing imports)
```python
# REMOVE (lines 5-10):
from services.ai_intent_handler import AIIntentHandler
from services.whatsapp import WhatsAppService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitTrackingService
from services.payment_commands import PaymentCommandHandler
from services.gamification import ChallengeManager

# ADD:
from services.ai_intent_handler import AIIntentHandler
from services.whatsapp import WhatsAppService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitTrackingService
from services.payment_commands import PaymentCommandHandler
from services.gamification import ChallengeManager
from services.registration import (
    TrainerRegistrationHandler,
    ClientRegistrationHandler,
    RegistrationStateManager,
    EditHandlers
)
```

**Change 4:** Fix initialization with proper config parameter
Location: Lines 30-34 (in __init__ method)
```python
# REMOVE (lines 30-34):
        # Initialize registration handlers
        self.trainer_registration = TrainerRegistrationHandler(supabase_client, config)
        self.client_registration = ClientRegistrationHandler(supabase_client, config)
        self.registration_state = RegistrationStateManager(supabase_client, config)
        self.edit_handler = EditHandlers(supabase_client, config)

# ADD:
        # Initialize registration handlers
        self.trainer_registration = TrainerRegistrationHandler(supabase_client, whatsapp_service, ai_handler)
        self.client_registration = ClientRegistrationHandler(supabase_client, whatsapp_service, ai_handler)
        self.registration_state = RegistrationStateManager(supabase_client, config)
        self.edit_handler = EditHandlers(supabase_client, config)
```

### EDIT: app_core.py

**Change 1:** Fix the RefiloeService initialization
Location: Line 38 (remove duplicate)
```python
# REMOVE (line 38):
    refiloe_service = RefiloeService(supabase)

# ADD:
    # Line already correctly initialized at line 31
```

**Change 2:** Pass correct parameters to RefiloeService
Location: Line 31
```python
# REMOVE (line 31):
    refiloe_service = RefiloeService(supabase)

# ADD:
    refiloe_service = RefiloeService(supabase, whatsapp_service, ai_handler)
```

## SUMMARY

In Step 4, I've:
1. Created the missing `registration_state.py` file with RegistrationStateManager class
2. Created the missing `edit_handlers.py` file with EditHandlers class  
3. Fixed method name mismatches in RefiloeService (removed underscore prefix)
4. Added proper imports for registration modules
5. Fixed initialization parameters for registration handlers
6. Removed duplicate RefiloeService initialization in app_core.py

The registration system is now fully integrated and ready to handle both trainer and client registrations through WhatsApp with proper multi-step flows, editing capabilities, and session management.