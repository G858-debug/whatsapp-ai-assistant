#!/usr/bin/env python3
"""
WhatsApp Flows Handler for Trainer Onboarding
Handles flow creation, sending, and response processing
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.logger import log_info, log_error, log_warning
from config import Config


class WhatsAppFlowHandler:
    """Handles WhatsApp Flows for trainer onboarding"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.supabase = supabase_client
        self.whatsapp_service = whatsapp_service
        self.flow_data = self._load_flow_data()
        
    def _load_flow_data(self) -> Dict:
        """Load the trainer onboarding flow JSON"""
        try:
            # Get the project root directory (go up one level from services)
            project_root = os.path.dirname(os.path.dirname(__file__))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_onboarding_flow.json')
            with open(flow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Error loading flow data: {str(e)}")
            return {}
    
    def create_flow_message(self, phone_number: str, flow_token: str = None) -> Dict:
        """Create a WhatsApp message with the trainer onboarding flow"""
        try:
            if not flow_token:
                flow_token = f"trainer_onboarding_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "🚀 Trainer Onboarding"
                    },
                    "body": {
                        "text": "Welcome to Refiloe! Let's get you set up as a trainer. This will take about 2 minutes."
                    },
                    "footer": {
                        "text": "Complete your profile setup"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "trainer_onboarding_flow",
                            "flow_cta": "Start Setup",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {}
                            }
                        }
                    }
                }
            }
            
            log_info(f"Created flow message for {phone_number}")
            return message
            
        except Exception as e:
            log_error(f"Error creating flow message: {str(e)}")
            return {}
    

    

    


    def send_trainer_onboarding_flow(self, phone_number: str) -> Dict:
        """Send the trainer onboarding flow to a phone number with automatic fallback"""
        try:
            # Check if user is already a trainer
            existing_trainer = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if existing_trainer.data:
                return {
                    'success': False,
                    'error': 'User is already registered as a trainer',
                    'message': 'You are already registered as a trainer! If you need help, please contact support.'
                }
            
            # Try WhatsApp Flow first
            flow_result = self._attempt_flow_sending(phone_number)
            
            if flow_result.get('success'):
                log_info(f"WhatsApp Flow sent successfully to {phone_number}")
                return flow_result
            
            # AUTOMATIC FALLBACK: Start text-based registration
            log_info(f"WhatsApp Flow failed for {phone_number}, automatically falling back to text registration")
            log_info(f"Flow failure reason: {flow_result.get('error', 'Unknown error')}")
            
            fallback_result = self._start_text_based_registration(phone_number)
            
            if fallback_result.get('success'):
                return {
                    'success': True,
                    'method': 'text_fallback',
                    'message': 'Started text-based registration (WhatsApp Flow not available)',
                    'fallback_reason': flow_result.get('error', 'Flow unavailable')
                }
            else:
                return {
                    'success': False,
                    'error': 'Both flow and text registration failed',
                    'details': {
                        'flow_error': flow_result.get('error'),
                        'fallback_error': fallback_result.get('error')
                    }
                }
                
        except Exception as e:
            log_error(f"Error in trainer onboarding flow with fallback: {str(e)}")
            
            # Last resort fallback
            try:
                fallback_result = self._start_text_based_registration(phone_number)
                if fallback_result.get('success'):
                    return {
                        'success': True,
                        'method': 'emergency_fallback',
                        'message': 'Started text-based registration (emergency fallback)'
                    }
            except Exception as fallback_error:
                log_error(f"Emergency fallback also failed: {str(fallback_error)}")
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_flow_response(self, flow_data: Dict) -> Dict:
        """Process completed trainer onboarding flow"""
        try:
            # Extract phone number from flow data
            phone_number = flow_data.get('phone_number')
            
            if not phone_number:
                log_error("No phone number in flow response data")
                return {
                    'success': False,
                    'error': 'Missing phone number in flow data'
                }
            
            log_info(f"Processing flow response for {phone_number}")
            
            # Extract flow response payload
            flow_response = flow_data.get('flow_response', {})
            
            if not flow_response:
                log_error("No flow_response in flow data")
                return {
                    'success': False,
                    'error': 'Missing flow response data'
                }
            
            # Get flow name and token
            flow_name = flow_response.get('name', 'trainer_onboarding_flow')
            flow_token = flow_response.get('flow_token')
            
            log_info(f"Flow name: {flow_name}, Flow token: {flow_token}")
            
            # Validate flow type
            if flow_name != 'trainer_onboarding_flow':
                return {
                    'success': False,
                    'error': f'Invalid flow type: {flow_name}'
                }
            
            # Extract form data from flow response
            trainer_data = self._extract_trainer_data_from_flow_response(flow_response, phone_number)
            
            if not trainer_data:
                return {
                    'success': False,
                    'error': 'Failed to extract trainer data from flow'
                }
            
            log_info(f"Extracted trainer data: {trainer_data.get('name', 'Unknown')} - {trainer_data.get('email', 'No email')}")
            
            # Validate required fields
            validation_result = self._validate_trainer_data(trainer_data)
            if not validation_result['valid']:
                log_error(f"Trainer data validation failed: {validation_result['errors']}")
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation_result['errors']
                }
            
            # Use existing trainer registration system for consistency
            try:
                from services.registration.trainer_registration import TrainerRegistrationHandler
                
                # Create trainer using existing registration system
                reg_handler = TrainerRegistrationHandler(self.supabase, self.whatsapp_service)
                
                # Complete registration using existing system
                completion_result = reg_handler._complete_registration(phone_number, trainer_data)
                
                if completion_result.get('success'):
                    trainer_id = completion_result.get('trainer_id')
                    
                    log_info(f"Trainer registration completed via flow: {trainer_id}")
                    
                    # Mark any existing registration state as complete
                    try:
                        from services.registration.registration_state import RegistrationStateManager
                        state_manager = RegistrationStateManager(self.supabase)
                        
                        # Mark registration as complete
                        existing_state = state_manager.get_registration_state(phone_number)
                        if existing_state:
                            state_manager.complete_registration(phone_number, 'trainer')
                    except Exception as state_error:
                        log_warning(f"Could not update registration state: {str(state_error)}")
                    
                    return {
                        'success': True,
                        'message': 'Trainer profile created successfully via WhatsApp Flow',
                        'trainer_id': trainer_id,
                        'method': 'whatsapp_flow'
                    }
                else:
                    log_error(f"Registration completion failed: {completion_result.get('message')}")
                    return {
                        'success': False,
                        'error': f'Registration failed: {completion_result.get("message")}'
                    }
                    
            except ImportError as e:
                log_error(f"Could not import registration handler: {str(e)}")
                
                # Fallback: create trainer record directly
                trainer_id = self._create_trainer_record_direct(trainer_data, flow_token)
                
                if trainer_id:
                    return {
                        'success': True,
                        'message': 'Trainer profile created successfully (direct method)',
                        'trainer_id': trainer_id,
                        'method': 'direct_creation'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to create trainer record'
                    }
                
        except Exception as e:
            log_error(f"Error handling flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_trainer_data_from_flow_response(self, flow_response: Dict, phone_number: str) -> Dict:
        """Extract trainer data from WhatsApp flow response"""
        try:
            # Get form data from flow response
            # WhatsApp flows return data in different possible structures
            form_data = {}
            
            # Try different possible data structures
            if 'data' in flow_response:
                form_data = flow_response['data']
            elif 'flow_action_payload' in flow_response:
                form_data = flow_response['flow_action_payload'].get('data', {})
            elif 'response' in flow_response:
                form_data = flow_response['response']
            
            log_info(f"Extracted form data keys: {list(form_data.keys())}")
            
            # Map flow form fields to trainer data structure
            # Based on our trainer_onboarding_flow.json structure
            
            # Basic info (from basic_info screen)
            first_name = form_data.get('first_name', '')
            surname = form_data.get('surname', '')
            full_name = f"{first_name} {surname}".strip() if first_name or surname else ''
            email = form_data.get('email', '')
            city = form_data.get('city', '')
            
            # Business details (from business_details screen)
            business_name = form_data.get('business_name', '')
            specializations = form_data.get('specializations', [])  # Multiple specializations from CheckboxGroup
            experience_years = form_data.get('experience_years', '0-1')
            pricing_per_session = form_data.get('pricing_per_session', 500)
            
            # Availability (from availability screen)
            available_days = form_data.get('available_days', [])  # CheckboxGroup
            preferred_time_slots = form_data.get('preferred_time_slots', '')  # Dropdown
            
            # Preferences (from preferences screen)
            subscription_plan = form_data.get('subscription_plan', 'free')
            
            # Business setup (from business_setup screen)
            services_offered = form_data.get('services_offered', [])  # CheckboxGroup
            
            # Pricing (from pricing_smart screen)
            pricing_flexibility = form_data.get('pricing_flexibility', [])  # CheckboxGroup
            
            # Terms (from terms_agreement screen)
            notification_preferences = form_data.get('notification_preferences', [])  # CheckboxGroup
            marketing_consent = form_data.get('marketing_consent', False)  # OptIn
            terms_accepted = form_data.get('terms_accepted', False)  # OptIn
            additional_notes = form_data.get('additional_notes', '')  # TextArea
            
            # Use the actual first_name and surname from flow
            # first_name and surname are already extracted above
            last_name = surname  # Flow uses 'surname' field
            
            # Ensure pricing is numeric
            try:
                pricing = float(pricing_per_session) if pricing_per_session else 500.0
            except (ValueError, TypeError):
                pricing = 500.0
            
            # Convert experience years to numeric for compatibility
            experience_numeric = 0
            if experience_years:
                if experience_years == '0-1':
                    experience_numeric = 1
                elif experience_years == '2-3':
                    experience_numeric = 2
                elif experience_years == '4-5':
                    experience_numeric = 4
                elif experience_years == '6-10':
                    experience_numeric = 7
                elif experience_years == '10+':
                    experience_numeric = 10
            
            # Handle specializations - convert from IDs to readable text if needed
            final_specialization = self._process_specializations('', specializations)
            
            # Process services offered - convert from IDs to readable text
            processed_services = self._process_services_offered(services_offered)
            
            # Process pricing flexibility - convert from IDs to readable text
            processed_pricing_flexibility = self._process_pricing_flexibility(pricing_flexibility)
            
            # Create trainer data structure compatible with existing registration system
            trainer_data = {
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'email': email.lower() if email else '',
                'city': city,
                'location': city,  # For backward compatibility
                'business_name': business_name,
                'specialization': final_specialization,
                'experience': experience_numeric,  # Numeric for existing system
                'years_experience': experience_numeric,  # For backward compatibility
                'experience_years': experience_years,  # Original for new fields
                'pricing': pricing,  # For existing system
                'pricing_per_session': pricing,  # For new fields
                'available_days': available_days,
                'preferred_time_slots': preferred_time_slots,
                'services_offered': processed_services,
                'pricing_flexibility': processed_pricing_flexibility,
                'subscription_plan': subscription_plan,
                'notification_preferences': notification_preferences,
                'marketing_consent': bool(marketing_consent),
                'terms_accepted': bool(terms_accepted),
                'additional_notes': additional_notes,
                'phone': phone_number,
                'whatsapp': phone_number,
                'registration_method': 'whatsapp_flow',
                'onboarding_method': 'flow'
            }
            
            log_info(f"Mapped trainer data for {full_name}: specialization={final_specialization}, pricing={pricing}")
            
            return trainer_data
            
        except Exception as e:
            log_error(f"Error extracting trainer data from flow response: {str(e)}")
            return {}
    
    def _process_specializations(self, single_spec: str, multi_specs: list) -> str:
        """Convert specialization IDs to readable text and handle multiple specializations"""
        try:
            # Mapping from actual flow IDs to readable text (from trainer_onboarding_flow.json)
            spec_mapping = {
                'personal_training': 'Personal Training',
                'group_fitness': 'Group Fitness',
                'strength_training': 'Strength Training',
                'cardio_fitness': 'Cardio Fitness',
                'yoga_pilates': 'Yoga & Pilates',
                'sports_coaching': 'Sports Coaching',
                'nutrition_coaching': 'Nutrition Coaching',
                'rehabilitation': 'Rehabilitation & Recovery',
                'general_fitness': 'General Fitness'
            }
            
            specializations = []
            
            # Handle single specialization
            if single_spec:
                if single_spec in spec_mapping:
                    specializations.append(spec_mapping[single_spec])
                else:
                    specializations.append(single_spec)  # Use as-is if not in mapping
            
            # Handle multiple specializations
            if multi_specs and isinstance(multi_specs, list):
                for spec in multi_specs:
                    if spec in spec_mapping:
                        specializations.append(spec_mapping[spec])
                    else:
                        specializations.append(spec)
            
            # Return comma-separated readable values
            return ', '.join(specializations) if specializations else 'General Fitness'
            
        except Exception as e:
            log_error(f"Error processing specializations: {str(e)}")
            return single_spec or 'General Fitness'
    
    def _process_services_offered(self, services: list) -> list:
        """Convert service IDs to readable text"""
        try:
            # Mapping from actual flow IDs (from business_setup screen)
            service_mapping = {
                'in_person_training': 'In-Person Training',
                'online_training': 'Online Training',
                'nutrition_planning': 'Nutrition Planning',
                'fitness_assessments': 'Fitness Assessments',
                'group_classes': 'Group Classes'
            }
            
            if not services or not isinstance(services, list):
                return []
            
            processed = []
            for service in services:
                if service in service_mapping:
                    processed.append(service_mapping[service])
                else:
                    processed.append(service)  # Use as-is if not in mapping
            
            return processed
            
        except Exception as e:
            log_error(f"Error processing services offered: {str(e)}")
            return services or []
    
    def _process_pricing_flexibility(self, pricing_options: list) -> list:
        """Convert pricing flexibility IDs to readable text"""
        try:
            # Mapping from actual flow IDs (from pricing_smart screen)
            pricing_mapping = {
                'package_discounts': 'Package Discounts',
                'student_discounts': 'Student Discounts',
                'group_rates': 'Group Session Rates'
            }
            
            if not pricing_options or not isinstance(pricing_options, list):
                return []
            
            processed = []
            for option in pricing_options:
                if option in pricing_mapping:
                    processed.append(pricing_mapping[option])
                else:
                    processed.append(option)  # Use as-is if not in mapping
            
            return processed
            
        except Exception as e:
            log_error(f"Error processing pricing flexibility: {str(e)}")
            return pricing_options or []
    
    def _extract_trainer_data_from_flow(self, action_payload: Dict) -> Dict:
        """Extract trainer data from new flow structure"""
        try:
            # Get phone number from flow token or context
            phone_number = self._get_phone_from_flow_token(action_payload.get('flow_token'))
            
            # Extract data from form responses
            form_data = action_payload.get('data', {})
            
            # Parse name (split first and last name)
            full_name = form_data.get('full_name', '')
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Parse pricing (ensure it's numeric)
            pricing_str = form_data.get('pricing_per_session', '500')
            try:
                pricing = float(pricing_str) if pricing_str else 500.0
            except (ValueError, TypeError):
                pricing = 500.0
            
            # Handle available days (could be string or list)
            available_days = form_data.get('available_days', [])
            if isinstance(available_days, str):
                available_days = [available_days]
            
            # Handle notification preferences (could be string or list)
            notification_prefs = form_data.get('notification_preferences', [])
            if isinstance(notification_prefs, str):
                notification_prefs = [notification_prefs]
            
            trainer_data = {
                'phone': phone_number,
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'email': form_data.get('email', ''),
                'city': form_data.get('city', ''),
                'specialization': form_data.get('specialization', ''),
                'experience_years': form_data.get('experience_years', '0-1'),
                'pricing_per_session': pricing,
                'available_days': available_days,
                'preferred_time_slots': form_data.get('preferred_time_slots', ''),
                'subscription_plan': form_data.get('subscription_plan', 'free'),
                'notification_preferences': notification_prefs,
                'terms_accepted': bool(form_data.get('terms_accepted', False)),
                'marketing_consent': bool(form_data.get('marketing_consent', False)),
                'status': 'active',  # Changed from pending_approval to active
                'created_at': datetime.now().isoformat()
            }
            
            log_info(f"Extracted trainer data: {trainer_data['name']} ({trainer_data['email']})")
            return trainer_data
            
        except Exception as e:
            log_error(f"Error extracting trainer data from flow: {str(e)}")
            return {}
    
    def _extract_trainer_data(self, action_payload: Dict) -> Dict:
        """Legacy method - kept for backward compatibility"""
        return self._extract_trainer_data_from_flow(action_payload)
    
    def _validate_trainer_data(self, trainer_data: Dict) -> Dict:
        """Validate trainer data from flow"""
        errors = []
        
        required_fields = [
            'name', 'email', 'city', 'specialization', 
            'experience_years', 'pricing_per_session',
            'available_days', 'preferred_time_slots',
            'subscription_plan', 'terms_accepted'
        ]
        
        for field in required_fields:
            if not trainer_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate email format
        if trainer_data.get('email') and '@' not in trainer_data['email']:
            errors.append("Invalid email format")
        
        # Validate pricing
        if trainer_data.get('pricing_per_session', 0) < 100:
            errors.append("Pricing must be at least R100")
        
        # Validate terms acceptance
        if not trainer_data.get('terms_accepted'):
            errors.append("Terms and conditions must be accepted")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _create_trainer_record_direct(self, trainer_data: Dict, flow_token: str) -> Optional[str]:
        """Create trainer record directly in database (fallback method)"""
        try:
            from datetime import datetime
            
            # Prepare data for database
            db_data = {
                'name': trainer_data.get('name', ''),
                'first_name': trainer_data.get('first_name', ''),
                'last_name': trainer_data.get('last_name', ''),
                'whatsapp': trainer_data.get('phone', ''),
                'email': trainer_data.get('email', ''),
                'city': trainer_data.get('city', ''),
                'specialization': trainer_data.get('specialization', ''),
                'years_experience': trainer_data.get('experience', 0),
                'pricing_per_session': trainer_data.get('pricing', 500),
                'status': 'active',
                'registration_method': 'whatsapp_flow',
                'flow_token': flow_token,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Add optional fields if available
            if trainer_data.get('available_days'):
                db_data['available_days'] = json.dumps(trainer_data['available_days'])
            if trainer_data.get('preferred_time_slots'):
                db_data['preferred_time_slots'] = trainer_data['preferred_time_slots']
            if trainer_data.get('subscription_plan'):
                db_data['subscription_plan'] = trainer_data['subscription_plan']
            if trainer_data.get('notification_preferences'):
                db_data['notification_preferences'] = json.dumps(trainer_data['notification_preferences'])
            
            # Insert into database
            result = self.supabase.table('trainers').insert(db_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Created trainer record directly: {trainer_id}")
                
                # Send confirmation message
                confirmation_message = self._create_confirmation_message(trainer_data)
                self.whatsapp_service.send_message(trainer_data['phone'], confirmation_message)
                
                return trainer_id
            else:
                log_error("Failed to create trainer record - no data returned")
                return None
                
        except Exception as e:
            log_error(f"Error creating trainer record directly: {str(e)}")
            return None
    
    def _create_trainer_record(self, trainer_data: Dict, flow_token: str) -> Optional[str]:
        """Create trainer record in database"""
        try:
            # Prepare data for database
            db_data = {
                'name': trainer_data['name'],
                'whatsapp': trainer_data['phone'],
                'email': trainer_data['email'],
                'city': trainer_data['city'],
                'specialization': trainer_data['specialization'],
                'experience_years': trainer_data['experience_years'],
                'pricing_per_session': trainer_data['pricing_per_session'],
                'available_days': json.dumps(trainer_data['available_days']),
                'preferred_time_slots': trainer_data['preferred_time_slots'],
                'subscription_plan': trainer_data['subscription_plan'],
                'notification_preferences': json.dumps(trainer_data['notification_preferences']),
                'terms_accepted': trainer_data['terms_accepted'],
                'marketing_consent': trainer_data['marketing_consent'],
                'status': 'pending_approval',
                'flow_token': flow_token,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Insert into database
            result = self.supabase.table('trainers').insert(db_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Created trainer record: {trainer_id}")
                return trainer_id
            else:
                log_error("Failed to create trainer record")
                return None
                
        except Exception as e:
            log_error(f"Error creating trainer record: {str(e)}")
            return None
    
    def _create_confirmation_message(self, trainer_data: Dict) -> str:
        """Create confirmation message for successful registration"""
        return f"""🎉 Welcome to Refiloe, {trainer_data['name']}!

Your trainer profile has been created successfully! Here's what happens next:

✅ **Profile Created**: {trainer_data['specialization']} trainer
✅ **Pricing Set**: R{trainer_data['pricing_per_session']} per session
✅ **Plan Selected**: {trainer_data['subscription_plan'].title()} Plan

📋 **Next Steps**:
1. We'll review your application within 24 hours
2. You'll receive an approval notification
3. Once approved, you can start accepting clients!

💡 **In the meantime**:
- Check your email for a confirmation message
- Review our trainer guidelines
- Set up your availability calendar

Questions? Just reply to this message and I'll help you out!

Welcome to the Refiloe family! 💪"""
    
    def _store_flow_token(self, phone_number: str, flow_token: str):
        """Store flow token for tracking"""
        try:
            self.supabase.table('flow_tokens').insert({
                'phone_number': phone_number,
                'flow_token': flow_token,
                'flow_type': 'trainer_onboarding',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            log_warning(f"Failed to store flow token: {str(e)}")
    
    def _get_phone_from_flow_token(self, flow_token: str) -> Optional[str]:
        """Get phone number from flow token"""
        try:
            result = self.supabase.table('flow_tokens').select('phone_number').eq('flow_token', flow_token).execute()
            if result.data:
                return result.data[0]['phone_number']
        except Exception as e:
            log_error(f"Error getting phone from flow token: {str(e)}")
        return None
    
    def _attempt_flow_sending(self, phone_number: str) -> Dict:
        """Attempt to send WhatsApp Flow (assumes flow is already created in Facebook Console)"""
        try:
            # Create flow message (assumes flow exists in Facebook Console)
            flow_message = self.create_flow_message(phone_number)
            if not flow_message:
                return {
                    'success': False,
                    'error': 'Failed to create flow message',
                    'fallback_required': True
                }
            
            # Send via WhatsApp service
            result = self.whatsapp_service.send_flow_message(flow_message)
            
            if result.get('success'):
                # Store flow token for tracking
                self._store_flow_token(phone_number, flow_message['interactive']['action']['parameters']['flow_token'])
                
                return {
                    'success': True,
                    'message': 'Trainer onboarding flow sent successfully',
                    'flow_token': flow_message['interactive']['action']['parameters']['flow_token']
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send flow message: {result.get("error")}',
                    'fallback_required': True
                }
                
        except Exception as e:
            log_error(f"Error attempting flow sending: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_required': True
            }
    
    def _start_text_based_registration(self, phone_number: str) -> Dict:
        """Start text-based registration as fallback"""
        try:
            from services.registration.trainer_registration import TrainerRegistrationHandler
            from services.registration.registration_state import RegistrationStateManager
            
            # Initialize handlers
            trainer_reg = TrainerRegistrationHandler(self.supabase, self.whatsapp_service)
            state_manager = RegistrationStateManager(self.supabase)
            
            # Check for existing registration state
            existing_state = state_manager.get_registration_state(phone_number)
            
            if existing_state and existing_state.get('user_type') == 'trainer':
                # Resume existing registration
                current_step = existing_state.get('current_step', 0)
                
                if current_step == 0:
                    welcome_message = trainer_reg.start_registration(phone_number)
                else:
                    # Create resume message
                    step_info = trainer_reg.STEPS.get(current_step)
                    if step_info:
                        welcome_message = (
                            f"Welcome back! Let's continue your trainer registration.\n\n"
                            f"📝 *Step {current_step + 1} of 7*\n\n"
                            f"{step_info['prompt'](current_step + 1)}"
                        )
                    else:
                        # Fallback to restart if step is invalid
                        welcome_message = trainer_reg.start_registration(phone_number)
                        current_step = 0
                
                log_info(f"Resuming trainer registration for {phone_number} at step {current_step}")
            else:
                # Start new registration
                welcome_message = trainer_reg.start_registration(phone_number)
                state_manager.create_registration_state(phone_number, 'trainer')
                current_step = 0
                log_info(f"Starting new trainer registration for {phone_number}")
            
            # Send welcome message
            send_result = self.whatsapp_service.send_message(phone_number, welcome_message)
            
            if send_result.get('success', True):  # Assume success if no explicit failure
                return {
                    'success': True,
                    'message': welcome_message,
                    'registration_step': current_step,
                    'method': 'text_based'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send welcome message: {send_result.get("error")}'
                }
                
        except ImportError as e:
            log_error(f"Import error in text-based registration fallback: {str(e)}")
            return {
                'success': False,
                'error': f'Registration modules not available: {str(e)}'
            }
        except Exception as e:
            log_error(f"Error starting text-based registration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_trainer_registration_request(self, phone_number: str) -> Dict:
        """Main entry point for trainer registration - tries flow first, falls back to text"""
        try:
            log_info(f"Processing trainer registration request for {phone_number}")
            
            # Check if user is already registered
            existing_trainer = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if existing_trainer.data:
                trainer_name = existing_trainer.data[0].get('first_name', 'there')
                return {
                    'success': True,
                    'already_registered': True,
                    'message': f"Welcome back, {trainer_name}! You're already registered as a trainer. How can I help you today?"
                }
            
            # Try to send WhatsApp Flow with automatic fallback
            result = self.send_trainer_onboarding_flow(phone_number)
            
            if result.get('success'):
                if result.get('method') == 'text_fallback':
                    # Text registration started successfully
                    return {
                        'success': True,
                        'method': 'text_registration',
                        'message': result.get('message'),
                        'conversation_state_update': {
                            'state': 'REGISTRATION',
                            'context': {
                                'type': 'trainer',
                                'current_step': 0
                            }
                        }
                    }
                else:
                    # WhatsApp Flow sent successfully
                    return {
                        'success': True,
                        'method': 'whatsapp_flow',
                        'message': 'WhatsApp Flow sent! Please complete the registration form.',
                        'flow_token': result.get('flow_token')
                    }
            else:
                # Both methods failed
                return {
                    'success': False,
                    'error': 'Registration system temporarily unavailable',
                    'message': 'Sorry, our registration system is temporarily unavailable. Please try again later or contact support.',
                    'details': result.get('details', result.get('error'))
                }
                
        except Exception as e:
            log_error(f"Error handling trainer registration request: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Something went wrong with registration. Please try again later.'
            }
    

    

    
    def get_flow_status(self, phone_number: str) -> Dict:
        """Get the status of a flow for a phone number"""
        try:
            result = self.supabase.table('flow_tokens').select('*').eq('phone_number', phone_number).eq('flow_type', 'trainer_onboarding').execute()
            
            if result.data:
                flow_token = result.data[0]
                return {
                    'has_active_flow': True,
                    'flow_token': flow_token['flow_token'],
                    'created_at': flow_token['created_at']
                }
            else:
                return {
                    'has_active_flow': False
                }
                
        except Exception as e:
            log_error(f"Error getting flow status: {str(e)}")
            return {
                'has_active_flow': False,
                'error': str(e)
            }
