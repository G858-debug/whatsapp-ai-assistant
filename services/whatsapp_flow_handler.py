#!/usr/bin/env python3
"""
WhatsApp Flows Handler for Trainer Onboarding
Handles flow creation, sending, and response processing
"""

import json
import os
import requests
from datetime import datetime, timedelta
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
                    "body": {
                        "text": "Let's set up your trainer profile! 💪"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": "775047838492907",
                            "flow_cta": "Get Started",
                            "flow_action": "data_exchange"
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
            
            # Route to appropriate handler based on flow type
            if flow_name in ['trainer_onboarding_flow', 'flow']:
                return self._handle_trainer_onboarding_response(flow_response, phone_number, flow_token)
            elif flow_name == 'trainer_profile_edit_flow':
                return self._handle_trainer_profile_edit_response(flow_response, phone_number, flow_token)
            elif flow_name == 'client_profile_edit_flow':
                return self._handle_client_profile_edit_response(flow_response, phone_number, flow_token)
            elif flow_name == 'trainer_add_client_flow':
                return self._handle_trainer_add_client_response(flow_response, phone_number, flow_token)
            elif flow_name == 'client_onboarding_flow':
                return self._handle_client_onboarding_response(flow_response, phone_number, flow_token)
            elif flow_name in ['trainer_habit_setup_flow', 'client_habit_logging_flow', 'habit_progress_flow']:
                return self.handle_habit_flow_response(flow_data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown flow type: {flow_name}'
                }
                
        except Exception as e:
            log_error(f"Error handling flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_trainer_onboarding_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer onboarding flow response"""
        try:
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
            log_error(f"Error handling trainer onboarding response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_trainer_profile_edit_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer profile edit flow response"""
        try:
            # Extract form data from flow response
            update_data = self._extract_profile_edit_data_from_flow_response(flow_response, phone_number, 'trainer')
            
            if not update_data:
                return {
                    'success': False,
                    'error': 'No update data provided'
                }
            
            # Update trainer profile with only the changed fields
            result = self._update_trainer_profile(phone_number, update_data)
            
            if result.get('success'):
                # Send confirmation message
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                
                updated_fields = list(update_data.keys())
                fields_text = ', '.join(updated_fields)
                
                response = (
                    f"✅ *Profile Updated Successfully!*\n\n"
                    f"Updated fields: {fields_text}\n\n"
                    f"📱 *Next Steps:*\n"
                    f"• Type `/profile` to view your updated profile\n"
                    f"• Continue using Refiloe as normal\n\n"
                    f"Thanks for keeping your profile up to date! 🎉"
                )
                
                whatsapp_service.send_message(phone_number, response)
                
                return {
                    'success': True,
                    'message': 'Trainer profile updated successfully',
                    'updated_fields': updated_fields
                }
            else:
                return result
                
        except Exception as e:
            log_error(f"Error handling trainer profile edit response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_client_profile_edit_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle client profile edit flow response"""
        try:
            # Extract form data from flow response
            update_data = self._extract_profile_edit_data_from_flow_response(flow_response, phone_number, 'client')
            
            if not update_data:
                return {
                    'success': False,
                    'error': 'No update data provided'
                }
            
            # Update client profile with only the changed fields
            result = self._update_client_profile(phone_number, update_data)
            
            if result.get('success'):
                # Send confirmation message
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                
                updated_fields = list(update_data.keys())
                fields_text = ', '.join(updated_fields)
                
                response = (
                    f"✅ *Profile Updated Successfully!*\n\n"
                    f"Updated fields: {fields_text}\n\n"
                    f"📱 *Next Steps:*\n"
                    f"• Type `/profile` to view your updated profile\n"
                    f"• Continue your fitness journey with Refiloe\n\n"
                    f"Thanks for keeping your profile up to date! 🎉"
                )
                
                whatsapp_service.send_message(phone_number, response)
                
                return {
                    'success': True,
                    'message': 'Client profile updated successfully',
                    'updated_fields': updated_fields
                }
            else:
                return result
                
        except Exception as e:
            log_error(f"Error handling client profile edit response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_profile_edit_data_from_flow_response(self, flow_response: Dict, phone_number: str, user_type: str) -> Dict:
        """Extract profile edit data from WhatsApp flow response"""
        try:
            # Get form data from flow response
            form_data = {}
            
            # Try different possible data structures
            if 'data' in flow_response:
                form_data = flow_response['data']
            elif 'flow_action_payload' in flow_response:
                form_data = flow_response['flow_action_payload'].get('data', {})
            elif 'response' in flow_response:
                form_data = flow_response['response']
            
            log_info(f"Extracted profile edit form data keys: {list(form_data.keys())}")
            
            # Only include fields that have values (user wants to update)
            update_data = {}
            
            if user_type == 'trainer':
                # Process trainer-specific fields
                if form_data.get('first_name'):
                    update_data['first_name'] = form_data['first_name']
                if form_data.get('surname'):
                    update_data['last_name'] = form_data['surname']
                if form_data.get('email'):
                    update_data['email'] = form_data['email'].lower()
                if form_data.get('city'):
                    update_data['city'] = form_data['city']
                if form_data.get('business_name'):
                    update_data['business_name'] = form_data['business_name']
                if form_data.get('specializations'):
                    update_data['specialization'] = self._process_specializations('', form_data['specializations'])
                if form_data.get('experience_years') and form_data['experience_years'] != '':
                    update_data['experience_years'] = form_data['experience_years']
                    # Also update numeric field
                    exp_map = {'0-1': 1, '2-3': 2, '4-5': 4, '6-10': 7, '10+': 10}
                    update_data['years_experience'] = exp_map.get(form_data['experience_years'], 0)
                if form_data.get('pricing_per_session'):
                    try:
                        update_data['pricing_per_session'] = float(form_data['pricing_per_session'])
                    except (ValueError, TypeError):
                        pass
                if form_data.get('available_days'):
                    update_data['available_days'] = form_data['available_days']
                if form_data.get('preferred_time_slots') and form_data['preferred_time_slots'] != '':
                    update_data['preferred_time_slots'] = form_data['preferred_time_slots']
                if form_data.get('subscription_plan') and form_data['subscription_plan'] != '':
                    update_data['subscription_plan'] = form_data['subscription_plan']
                if form_data.get('notification_preferences'):
                    update_data['notification_preferences'] = form_data['notification_preferences']
                if form_data.get('marketing_consent') is not None:
                    update_data['marketing_consent'] = bool(form_data['marketing_consent'])
                if form_data.get('services_offered'):
                    update_data['services_offered'] = self._process_services_offered(form_data['services_offered'])
                if form_data.get('pricing_flexibility'):
                    update_data['pricing_flexibility'] = self._process_pricing_flexibility(form_data['pricing_flexibility'])
                if form_data.get('additional_notes'):
                    update_data['additional_notes'] = form_data['additional_notes']
                    
            elif user_type == 'client':
                # Process client-specific fields
                if form_data.get('name'):
                    update_data['name'] = form_data['name']
                if form_data.get('email'):
                    update_data['email'] = form_data['email'].lower()
                if form_data.get('fitness_goals'):
                    update_data['fitness_goals'] = form_data['fitness_goals']
                if form_data.get('availability'):
                    update_data['availability'] = form_data['availability']
                if form_data.get('notification_preferences'):
                    update_data['notification_preferences'] = form_data['notification_preferences']
                if form_data.get('marketing_consent') is not None:
                    update_data['marketing_consent'] = bool(form_data['marketing_consent'])
            
            # Update timestamp
            if update_data:
                from datetime import datetime
                update_data['updated_at'] = datetime.now().isoformat()
            
            log_info(f"Profile edit data for {phone_number} ({user_type}): {list(update_data.keys())}")
            
            return update_data
            
        except Exception as e:
            log_error(f"Error extracting profile edit data: {str(e)}")
            return {}
    
    def _update_trainer_profile(self, phone_number: str, update_data: Dict) -> Dict:
        """Update trainer profile with provided data"""
        try:
            if not update_data:
                return {'success': False, 'error': 'No data to update'}
            
            # Update trainer record
            result = self.supabase.table('trainers').update(update_data).eq('whatsapp', phone_number).execute()
            
            if result.data:
                log_info(f"Updated trainer profile for {phone_number}: {list(update_data.keys())}")
                return {'success': True, 'updated_fields': list(update_data.keys())}
            else:
                return {'success': False, 'error': 'No trainer record found to update'}
                
        except Exception as e:
            log_error(f"Error updating trainer profile: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _update_client_profile(self, phone_number: str, update_data: Dict) -> Dict:
        """Update client profile with provided data"""
        try:
            if not update_data:
                return {'success': False, 'error': 'No data to update'}
            
            # Update client record
            result = self.supabase.table('clients').update(update_data).eq('whatsapp', phone_number).execute()
            
            if result.data:
                log_info(f"Updated client profile for {phone_number}: {list(update_data.keys())}")
                return {'success': True, 'updated_fields': list(update_data.keys())}
            else:
                return {'success': False, 'error': 'No client record found to update'}
                
        except Exception as e:
            log_error(f"Error updating client profile: {str(e)}")
            return {'success': False, 'error': str(e)}
    
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
            # Transform weekday availability data into expected format
            available_days, preferred_time_slots, working_hours = self._transform_availability_data(form_data)
            
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
                'working_hours': working_hours,  # JSONB structure with detailed availability
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

    def _transform_availability_data(self, form_data: Dict) -> tuple:
        """
        Transform weekday availability data from flow format to expected format.

        Flow sends: monday_preset, monday_hours, tuesday_preset, tuesday_hours, etc.
        Expected: available_days (list), preferred_time_slots (string), and working_hours (dict)

        Returns:
            tuple: (available_days: list, preferred_time_slots: str, working_hours: dict)
        """
        try:
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

            # Preset to time slot mapping
            preset_mapping = {
                'full_day': {'start': '00:00', 'end': '24:00'},
                'business': {'start': '08:00', 'end': '17:00'},
                'morning': {'start': '05:00', 'end': '12:00'},
                'evening': {'start': '17:00', 'end': '21:00'}
            }

            # Day abbreviations for short summary
            day_abbrev = {
                'monday': 'M',
                'tuesday': 'T',
                'wednesday': 'W',
                'thursday': 'Th',
                'friday': 'F',
                'saturday': 'Sa',
                'sunday': 'Su'
            }

            available_days = []
            short_slots = []
            working_hours = {}

            for day in weekdays:
                preset_key = f'{day}_preset'
                hours_key = f'{day}_hours'

                preset = form_data.get(preset_key, 'not_available')
                hours = form_data.get(hours_key, [])

                # Handle not available case
                if preset == 'not_available':
                    working_hours[day] = {'available': False}
                    continue

                # Add day to available days (capitalize first letter for consistency)
                available_days.append(day.capitalize())

                # Build working_hours entry for this day
                if preset == 'custom' and hours:
                    # Custom hours - use the array of hour slots
                    if isinstance(hours, list) and len(hours) > 0:
                        try:
                            # Get first hour's start and last hour's end
                            first_hour = hours[0].split('-')[0]
                            last_hour = hours[-1].split('-')[1]

                            # Create working_hours entry with slots
                            working_hours[day] = {
                                'start': f'{first_hour}:00',
                                'end': f'{last_hour}:00',
                                'available': True,
                                'slots': hours  # Keep the original slots array
                            }

                            # Create short summary
                            short_slots.append(f'{day_abbrev[day]}:{first_hour}-{last_hour}')
                        except (IndexError, AttributeError) as e:
                            log_warning(f"Error parsing custom hours for {day}: {str(e)}")
                            working_hours[day] = {'available': True}
                            short_slots.append(f'{day_abbrev[day]}:Custom')
                    else:
                        working_hours[day] = {'available': True}
                        short_slots.append(f'{day_abbrev[day]}:Custom')

                elif preset in preset_mapping:
                    # Use preset mapping
                    times = preset_mapping[preset]
                    working_hours[day] = {
                        'start': times['start'],
                        'end': times['end'],
                        'available': True
                    }

                    # Create short summary
                    if preset == 'full_day':
                        short_slots.append(f'{day_abbrev[day]}:Full')
                    else:
                        # Extract just the hours without :00
                        start_hour = times['start'].split(':')[0]
                        end_hour = times['end'].split(':')[0]
                        short_slots.append(f'{day_abbrev[day]}:{start_hour}-{end_hour}')
                else:
                    # Fallback for unknown presets
                    working_hours[day] = {'available': True}
                    short_slots.append(f'{day_abbrev[day]}:Avail')

            # Create short summary (under 50 chars)
            preferred_time_slots = ','.join(short_slots) if short_slots else 'Flexible'

            log_info(f"Transformed availability: days={available_days}, slots={preferred_time_slots}")
            log_info(f"Working hours: {json.dumps(working_hours)}")

            return available_days, preferred_time_slots, working_hours

        except Exception as e:
            log_error(f"Error transforming availability data: {str(e)}")
            # Return defaults on error
            return [], 'Flexible', {}

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
    
    def _handle_trainer_add_client_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer add client flow response"""
        try:
            log_info(f"Processing trainer add client flow response for {phone_number}")
            
            # Extract client data from flow response
            client_data = self._extract_client_data_from_flow_response(flow_response, phone_number)
            
            if not client_data:
                return {
                    'success': False,
                    'error': 'Failed to extract client data from flow response'
                }
            
            # Validate trainer exists
            trainer_result = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if not trainer_result.data:
                return {
                    'success': False,
                    'error': 'Trainer not found'
                }
            
            trainer = trainer_result.data[0]
            trainer_id = trainer['id']
            
            # Check subscription limits
            try:
                from services.subscription_manager import SubscriptionManager
                subscription_manager = SubscriptionManager(self.supabase)
                
                if not subscription_manager.can_add_client(trainer_id):
                    limits = subscription_manager.get_client_limits(trainer_id)
                    return {
                        'success': False,
                        'error': f"You've reached your client limit of {limits.get('max_clients', 'unknown')} clients. Please upgrade your subscription."
                    }
            except Exception as e:
                log_warning(f"Could not check subscription limits: {str(e)}")
            
            # Validate phone number
            from utils.validators import Validators
            validator = Validators()
            is_valid, formatted_phone, error = validator.validate_phone_number(client_data['phone'])
            
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Invalid phone number: {error}"
                }
            
            client_data['phone'] = formatted_phone
            
            # Check for duplicate client
            existing_client = self.supabase.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', formatted_phone).execute()
            if existing_client.data:
                return {
                    'success': False,
                    'error': f"You already have a client with phone number {formatted_phone}"
                }
            
            # Process based on invitation method
            invitation_method = client_data.get('invitation_method', 'manual_add')
            
            if invitation_method == 'whatsapp_invite':
                # Create invitation and send WhatsApp message
                result = self._create_and_send_invitation(trainer_id, client_data)
            else:
                # Add client directly
                result = self._add_client_directly(trainer_id, client_data)
            
            if result.get('success'):
                # Handle package deal clarification if needed
                if client_data.get('has_package_deal') and client_data.get('package_details'):
                    needs_clarification = self._check_package_needs_clarification(client_data['package_details'])

                    if needs_clarification:
                        # Set conversation state for package clarification
                        try:
                            from services.refiloe import RefiloeService
                            refiloe_service = RefiloeService(self.supabase)

                            clarification_context = {
                                'client_name': client_data['name'],
                                'client_phone': client_data['phone'],
                                'trainer_id': trainer_id,
                                'package_details_raw': client_data['package_details'],
                                'invitation_method': client_data['invitation_method']
                            }

                            refiloe_service.update_conversation_state(
                                phone_number,
                                'PACKAGE_DEAL_CLARIFICATION',
                                clarification_context
                            )

                            # Append clarification request to result message
                            clarification_msg = "\n\n📦 *Package Deal Details*\n\nI need a bit more information about the package deal. Please tell me:\n\n• How many sessions are included?\n• What's the total package price?\n• What's the package duration (e.g., 1 month, 3 months)?"

                            result['message'] = result.get('message', '') + clarification_msg

                        except Exception as e:
                            log_warning(f"Could not set package clarification state: {str(e)}")
                    else:
                        # Clear conversation state if no clarification needed
                        try:
                            from services.refiloe import RefiloeService
                            refiloe_service = RefiloeService(self.supabase)
                            refiloe_service.clear_conversation_state(phone_number)
                        except Exception as e:
                            log_warning(f"Could not clear conversation state: {str(e)}")
                else:
                    # Clear any conversation state
                    try:
                        from services.refiloe import RefiloeService
                        refiloe_service = RefiloeService(self.supabase)
                        refiloe_service.clear_conversation_state(phone_number)
                    except Exception as e:
                        log_warning(f"Could not clear conversation state: {str(e)}")

                return result
            else:
                return result
                
        except Exception as e:
            log_error(f"Error handling trainer add client flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_client_data_from_flow_response(self, flow_response: Dict, trainer_phone: str) -> Optional[Dict]:
        """
        Extract client data from flow response with proper type conversions.

        IMPORTANT TYPE CONVERSIONS:
        - has_package_deal: boolean (use directly from OptIn component)
        - custom_price_amount: string -> convert to float for database
        - sessions_per_week: string (keep as string or convert to int as needed)
        - fitness_goals: array of strings (from CheckboxGroup)
        - preferred_times: array of strings (from CheckboxGroup)
        """
        try:
            # Get the response data
            response_data = flow_response.get('response', {})

            log_info(f"Flow response data: {response_data}")

            # Extract required client contact information
            client_name = response_data.get('client_name', '').strip()
            client_phone = response_data.get('client_phone', '').strip()
            client_email = response_data.get('client_email', '').strip()

            if not client_name or not client_phone:
                log_error("Missing required client data: name or phone")
                return None

            # Extract fitness information (NEW - comprehensive fields)
            fitness_goals = response_data.get('fitness_goals', [])
            # fitness_goals comes as array from CheckboxGroup
            if isinstance(fitness_goals, str):
                # Handle case where it might come as string
                fitness_goals = [goal.strip() for goal in fitness_goals.split(',') if goal.strip()]

            specific_goals = response_data.get('specific_goals', '').strip()
            experience_level = response_data.get('experience_level', '').strip()

            # sessions_per_week comes as string from RadioButtonsGroup
            sessions_per_week = response_data.get('sessions_per_week', '').strip()

            # preferred_times comes as array from CheckboxGroup
            preferred_times = response_data.get('preferred_times', [])
            if isinstance(preferred_times, str):
                preferred_times = [time.strip() for time in preferred_times.split(',') if time.strip()]

            # Extract health information (NEW)
            health_conditions = response_data.get('health_conditions', '').strip()
            medications = response_data.get('medications', '').strip()
            additional_notes = response_data.get('additional_notes', '').strip()

            # Extract pricing information with CORRECTED TYPE HANDLING
            pricing_choice = response_data.get('pricing_choice', 'use_default')
            custom_price_amount = response_data.get('custom_price_amount', '').strip()

            # CRITICAL: Convert custom_price_amount from string to float
            final_price = None
            if pricing_choice == 'custom_price' and custom_price_amount:
                try:
                    final_price = float(custom_price_amount)
                    log_info(f"Converted custom price: {custom_price_amount} -> {final_price}")
                except (ValueError, TypeError) as e:
                    log_warning(f"Invalid custom price: {custom_price_amount}, error: {str(e)}")

            # CRITICAL: has_package_deal comes as BOOLEAN from OptIn component
            has_package_deal = response_data.get('has_package_deal', False)
            # Convert string 'true'/'false' to boolean if needed (defensive)
            if isinstance(has_package_deal, str):
                has_package_deal = has_package_deal.lower() in ('true', 'yes', '1')
            else:
                has_package_deal = bool(has_package_deal)

            package_deal_details = response_data.get('package_deal_details', '').strip()

            # Check if trainer_filled flag is present
            trainer_filled = response_data.get('trainer_filled', 'true')

            log_info(f"Extracted data - has_package_deal: {has_package_deal} (type: {type(has_package_deal)})")
            log_info(f"Extracted data - custom_price: {final_price} (type: {type(final_price)})")
            log_info(f"Extracted data - fitness_goals: {fitness_goals}")
            log_info(f"Extracted data - preferred_times: {preferred_times}")

            return {
                # Contact information
                'name': client_name,
                'phone': client_phone,
                'email': client_email if client_email else None,

                # Fitness information (NEW)
                'fitness_goals': fitness_goals,
                'specific_goals': specific_goals if specific_goals else None,
                'experience_level': experience_level if experience_level else None,
                'sessions_per_week': sessions_per_week if sessions_per_week else None,
                'preferred_times': preferred_times,

                # Health information (NEW)
                'health_conditions': health_conditions if health_conditions else None,
                'medications': medications if medications else None,
                'additional_notes': additional_notes if additional_notes else None,

                # Pricing information
                'pricing_choice': pricing_choice,
                'custom_price': final_price,  # Now properly converted to float
                'has_package_deal': has_package_deal,  # Boolean value
                'package_deal_details': package_deal_details if package_deal_details else None,

                # Metadata
                'trainer_filled': trainer_filled == 'true',
                'invitation_method': 'whatsapp_invite'  # Always send invitation for trainer-filled profiles
            }

        except Exception as e:
            log_error(f"Error extracting client data from flow response: {str(e)}", exc_info=True)
            return None
    
    def _create_and_send_invitation(self, trainer_id: str, client_data: Dict) -> Dict:
        """
        Create invitation and send WhatsApp message to client.
        For trainer-filled profiles, stores ALL trainer-provided data in JSONB.
        """
        try:
            import uuid

            # Generate invitation token
            invitation_token = str(uuid.uuid4())

            # Prepare trainer_provided_data JSONB with ALL client information
            trainer_provided_data = {
                'name': client_data['name'],
                'email': client_data.get('email'),
                'fitness_goals': client_data.get('fitness_goals', []),
                'specific_goals': client_data.get('specific_goals'),
                'experience_level': client_data.get('experience_level'),
                'sessions_per_week': client_data.get('sessions_per_week'),
                'preferred_times': client_data.get('preferred_times', []),
                'health_conditions': client_data.get('health_conditions'),
                'medications': client_data.get('medications'),
                'additional_notes': client_data.get('additional_notes'),
                'pricing_choice': client_data.get('pricing_choice'),
                'custom_price': client_data.get('custom_price'),
                'has_package_deal': client_data.get('has_package_deal', False),
                'package_deal_details': client_data.get('package_deal_details')
            }

            # Create invitation record with comprehensive data
            invitation_data = {
                'trainer_id': trainer_id,
                'client_phone': client_data['phone'],
                'client_name': client_data['name'],
                'client_email': client_data.get('email'),
                'invitation_token': invitation_token,
                'invitation_method': 'whatsapp',
                'status': 'pending_client_acceptance',  # Special status for trainer-filled profiles
                'profile_completion_method': 'trainer_fills',  # Track that trainer filled the profile
                'trainer_provided_data': trainer_provided_data,  # JSONB with all data
                'pricing_choice': client_data.get('pricing_choice', 'use_default'),
                'custom_price': client_data.get('custom_price'),  # Already converted to float
                'has_package_deal': client_data.get('has_package_deal', False),  # Boolean
                'package_deal_details': client_data.get('package_deal_details'),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            invitation_result = self.supabase.table('client_invitations').insert(invitation_data).execute()
            
            if not invitation_result.data:
                return {
                    'success': False,
                    'error': 'Failed to create invitation record'
                }
            
            # Get trainer info for personalized message
            trainer_result = self.supabase.table('trainers').select('name, business_name, default_price_per_session').eq('id', trainer_id).execute()
            trainer_name = 'Your trainer'
            business_name = 'their training program'
            trainer_default_price = None

            if trainer_result.data:
                trainer_info = trainer_result.data[0]
                trainer_name = trainer_info.get('name', 'Your trainer')
                business_name = trainer_info.get('business_name') or f"{trainer_name}'s training program"
                trainer_default_price = trainer_info.get('default_price_per_session')

            # Create trainer-filled profile invitation message (different from regular invitation)
            invitation_message = f"""🎯 *Training Profile Created*

Hi {client_data['name']}! 👋

{trainer_name} has created a fitness profile for you and invited you to train together!

📋 *Your Pre-filled Profile:*
• Name: {client_data['name']}"""

            # Add optional contact info
            if client_data.get('email'):
                invitation_message += f"\n• Email: {client_data['email']}"

            # Add fitness information
            if client_data.get('fitness_goals'):
                goals_str = ', '.join(client_data['fitness_goals']) if isinstance(client_data['fitness_goals'], list) else client_data['fitness_goals']
                invitation_message += f"\n• Goals: {goals_str}"

            if client_data.get('experience_level'):
                invitation_message += f"\n• Experience: {client_data['experience_level']}"

            if client_data.get('sessions_per_week'):
                invitation_message += f"\n• Sessions/week: {client_data['sessions_per_week']}"

            # Add pricing information
            if client_data.get('custom_price'):
                invitation_message += f"\n• Price: R{client_data['custom_price']:.0f} per session (custom rate)"
            elif trainer_default_price:
                invitation_message += f"\n• Price: R{trainer_default_price:.0f} per session"

            # Add package deal if applicable
            if client_data.get('has_package_deal') and client_data.get('package_deal_details'):
                invitation_message += f"\n• Package Deal: {client_data['package_deal_details']}"

            invitation_message += f"""

👨‍🏫 *Your Trainer:*
• {trainer_name}
• {business_name}

✅ *Review and Accept*

Please review the information above. If everything looks good, reply 'ACCEPT' to start training!

You can also reply 'CHANGES' if you need to update any information.

This invitation expires in 7 days.

Reply 'ACCEPT' to get started! 🚀"""

            # Send invitation message
            send_result = self.whatsapp_service.send_message(client_data['phone'], invitation_message)
            
            if send_result.get('success', True):
                return {
                    'success': True,
                    'message': f"✅ Invitation sent to {client_data['name']}! I'll notify you when they respond.",
                    'invitation_token': invitation_token
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to send invitation message: {send_result.get('error')}"
                }
                
        except Exception as e:
            log_error(f"Error creating and sending invitation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _add_client_directly(self, trainer_id: str, client_data: Dict) -> Dict:
        """Add client directly without invitation"""
        try:
            # Create client record
            new_client_data = {
                'trainer_id': trainer_id,
                'name': client_data['name'],
                'whatsapp': client_data['phone'],
                'email': client_data.get('email'),
                'status': 'active',
                'package_type': 'single',
                'sessions_remaining': 1,
                'experience_level': 'Beginner',  # Default
                'health_conditions': 'None specified',  # Default
                'fitness_goals': 'General fitness',  # Default
                'preferred_training_times': 'Flexible',  # Default
                'connection_status': 'active',
                'requested_by': 'trainer',
                'approved_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }

            # Add custom pricing if provided
            if client_data.get('custom_price'):
                new_client_data['custom_price_per_session'] = client_data['custom_price']
            
            client_result = self.supabase.table('clients').insert(new_client_data).execute()
            
            if not client_result.data:
                return {
                    'success': False,
                    'error': 'Failed to create client record'
                }
            
            client_id = client_result.data[0]['id']
            
            # Send welcome message to client
            welcome_message = f"""🌟 *Welcome to your fitness journey!*

Hi {client_data['name']}!

You've been added as a client! I'm Refiloe, your AI fitness assistant.

I'm here to help you:
• Book training sessions
• Track your progress  
• Stay motivated
• Connect with your trainer

Ready to get started? Just say 'Hi' anytime! 💪"""
            
            # Send welcome message (don't fail if this doesn't work)
            try:
                self.whatsapp_service.send_message(client_data['phone'], welcome_message)
            except Exception as e:
                log_warning(f"Could not send welcome message to client: {str(e)}")
            
            return {
                'success': True,
                'message': f"🎉 *Client Added Successfully!*\n\n✅ {client_data['name']} has been added to your client list!\n📱 Phone: {client_data['phone']}\n\nThey can now book sessions and track progress with you!",
                'client_id': client_id
            }
            
        except Exception as e:
            log_error(f"Error adding client directly: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _check_package_needs_clarification(self, package_details: str) -> bool:
        """
        Check if package deal details are vague and need clarification.
        Returns True if clarification is needed.
        """
        import re

        if not package_details or len(package_details.strip()) < 10:
            return True

        # Check if essential information is missing
        has_session_count = bool(re.search(r'\d+\s*(session|sessions|ses)', package_details, re.IGNORECASE))
        has_price = bool(re.search(r'R?\s*\d+', package_details))
        has_duration = bool(re.search(r'\d+\s*(month|months|week|weeks|day|days)', package_details, re.IGNORECASE))

        # If any of these is missing, we need clarification
        if not (has_session_count and has_price):
            return True

        # Check for vague phrases that indicate incomplete information
        vague_phrases = ['tbd', 'to be determined', 'discuss', 'flexible', 'depends', 'various', 'etc']
        for phrase in vague_phrases:
            if phrase in package_details.lower():
                return True

        return False

    def _handle_client_onboarding_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle client onboarding flow response"""
        try:
            log_info(f"Processing client onboarding flow response for {phone_number}")

            # Check if this is an invitation flow (Scenario 1A)
            if flow_token and flow_token.startswith('client_invitation_'):
                log_info(f"Processing client invitation flow completion for {phone_number}")
                return self._handle_client_invitation_flow_completion(flow_response, phone_number, flow_token)

            # Regular client onboarding (not from invitation)
            # Extract client data from flow response
            client_data = self._extract_client_data_from_onboarding_response(flow_response, phone_number)

            if not client_data:
                return {
                    'success': False,
                    'error': 'Failed to extract client data from flow response'
                }

            # Complete client registration using the existing handler
            from services.registration.client_registration import ClientRegistrationHandler

            client_reg_handler = ClientRegistrationHandler(self.supabase, self.whatsapp_service)

            # Complete registration with flow data
            result = client_reg_handler._complete_registration(phone_number, client_data)

            if result.get('success'):
                # Clear any conversation state
                try:
                    from services.refiloe import RefiloeService
                    refiloe_service = RefiloeService(self.supabase)
                    refiloe_service.clear_conversation_state(phone_number)
                except Exception as e:
                    log_warning(f"Could not clear conversation state: {str(e)}")

                return {
                    'success': True,
                    'message': result['message'],
                    'client_id': result.get('client_id')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Registration failed')
                }

        except Exception as e:
            log_error(f"Error handling client onboarding flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_client_invitation_flow_completion(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle client invitation flow completion (Scenario 1A)"""
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')

            # Extract invitation token from flow_token (format: client_invitation_{token}_{timestamp})
            token_parts = flow_token.split('_')
            if len(token_parts) < 3:
                log_error(f"Invalid flow_token format: {flow_token}")
                return {'success': False, 'error': 'Invalid invitation token'}

            invitation_token = token_parts[2]  # Extract the actual invitation token

            # Find invitation in database
            invitation_result = self.supabase.table('client_invitations').select('*').eq(
                'invitation_token', invitation_token
            ).eq('client_phone', phone_number).eq('status', 'pending_client_completion').execute()

            if not invitation_result.data:
                log_error(f"No pending invitation found for token {invitation_token} and phone {phone_number}")
                return {'success': False, 'error': 'Invitation not found or expired'}

            invitation = invitation_result.data[0]

            # Extract client data from flow response
            flow_client_data = self._extract_client_data_from_onboarding_response(flow_response, phone_number)

            if not flow_client_data:
                return {'success': False, 'error': 'Failed to extract client data from flow'}

            # Merge prefilled data with flow data
            prefilled_data = invitation.get('prefilled_data', {})
            client_name = prefilled_data.get('name') or flow_client_data.get('name')
            client_email = prefilled_data.get('email') or flow_client_data.get('email')

            # Generate client_id
            from services.auth.authentication_service import AuthenticationService
            auth_service = AuthenticationService(self.supabase)
            client_id = auth_service.generate_unique_id(client_name, 'client')

            # Get trainer info for relationship
            trainer_result = self.supabase.table('trainers').select('trainer_id, name, first_name, last_name, whatsapp').eq(
                'id', invitation['trainer_id']
            ).execute()

            if not trainer_result.data:
                log_error(f"Trainer not found for invitation {invitation['id']}")
                return {'success': False, 'error': 'Trainer not found'}

            trainer = trainer_result.data[0]
            trainer_id = trainer['trainer_id']
            trainer_whatsapp = trainer['whatsapp']
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Create client record
            client_data = {
                'client_id': client_id,
                'whatsapp': phone_number,
                'name': client_name,
                'email': client_email if client_email and client_email.lower() not in ['skip', 'none'] else None,
                'fitness_goals': flow_client_data.get('fitness_goals'),
                'experience_level': flow_client_data.get('experience_level'),
                'health_conditions': flow_client_data.get('health_conditions'),
                'availability': flow_client_data.get('availability'),
                'status': 'active',
                'created_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }

            # Insert into clients table
            self.supabase.table('clients').insert(client_data).execute()
            log_info(f"Created client record for {client_id}")

            # Create user entry
            user_data = {
                'phone_number': phone_number,
                'client_id': client_id,
                'login_status': 'client',
                'created_at': datetime.now(sa_tz).isoformat()
            }
            self.supabase.table('users').insert(user_data).execute()
            log_info(f"Created user record for {client_id}")

            # Create trainer-client relationship
            from services.relationships.invitations.invitation_manager import InvitationManager
            from services.relationships.core.relationship_manager import RelationshipManager

            relationship_manager = RelationshipManager(self.supabase)
            invitation_manager = InvitationManager(self.supabase, self.whatsapp_service, relationship_manager)

            # Create relationship with pricing
            success, error_msg = invitation_manager.create_relationship(trainer_id, client_id, 'trainer', invitation_token)

            if success:
                # Approve the relationship immediately (client accepted invitation)
                approve_success, approve_error = relationship_manager.approve_relationship(trainer_id, client_id)

                if approve_success:
                    # Apply custom pricing if specified
                    custom_price = invitation.get('custom_price_per_session')
                    if custom_price:
                        try:
                            # Update pricing in trainer_client_list
                            self.supabase.table('trainer_client_list').update({
                                'pricing_per_session': custom_price,
                                'updated_at': datetime.now(sa_tz).isoformat()
                            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

                            log_info(f"Applied custom pricing R{custom_price} for client {client_id}")
                        except Exception as pricing_error:
                            log_error(f"Failed to apply custom pricing: {str(pricing_error)}")
                else:
                    log_error(f"Failed to approve relationship: {approve_error}")
            else:
                log_error(f"Failed to create relationship: {error_msg}")

            # Update invitation status
            self.supabase.table('client_invitations').update({
                'status': 'accepted',
                'accepted_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('id', invitation['id']).execute()

            # Notify client
            client_message = (
                f"✅ *Profile Complete!*\n\n"
                f"Welcome to Refiloe, {client_name}!\n\n"
                f"*Your Client ID:* {client_id}\n"
                f"*Trainer:* {trainer_name}\n"
                f"*Price per session:* R{custom_price if custom_price else 'TBD'}\n\n"
                f"You're now connected with your trainer.\n"
                f"Type /help to see what you can do!"
            )
            self.whatsapp_service.send_message(phone_number, client_message)

            # Notify trainer
            trainer_message = (
                f"✅ *Client Accepted Invitation!*\n\n"
                f"*{client_name}* completed their fitness profile and accepted your invitation!\n\n"
                f"*Client ID:* {client_id}\n"
                f"*Fitness Goals:* {flow_client_data.get('fitness_goals')}\n"
                f"*Experience:* {flow_client_data.get('experience_level')}\n"
                f"*Availability:* {flow_client_data.get('availability')}\n\n"
                f"They're now in your client list. 🎉"
            )
            self.whatsapp_service.send_message(trainer_whatsapp, trainer_message)

            log_info(f"Successfully completed client invitation flow for {client_id}")

            return {
                'success': True,
                'message': 'Client registration and relationship created successfully',
                'client_id': client_id
            }

        except Exception as e:
            log_error(f"Error handling client invitation flow completion: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_client_data_from_onboarding_response(self, flow_response: Dict, client_phone: str) -> Optional[Dict]:
        """Extract client data from onboarding flow response"""
        try:
            # Get the response data
            response_data = flow_response.get('response', {})
            
            # Extract client information
            full_name = response_data.get('full_name', '').strip()
            email = response_data.get('email', '').strip()
            fitness_goals = response_data.get('fitness_goals', [])
            experience_level = response_data.get('experience_level', '')
            health_conditions = response_data.get('health_conditions', '').strip()
            availability = response_data.get('availability', [])
            
            if not full_name:
                log_error("Missing required client data: full_name")
                return None
            
            # Process fitness goals (convert from array to readable text)
            goals_map = {
                'lose_weight': 'Lose weight',
                'build_muscle': 'Build muscle',
                'get_stronger': 'Get stronger',
                'improve_fitness': 'Improve fitness',
                'train_for_event': 'Train for event'
            }
            
            if isinstance(fitness_goals, list):
                processed_goals = [goals_map.get(goal, goal) for goal in fitness_goals]
                fitness_goals_text = ', '.join(processed_goals)
            else:
                fitness_goals_text = str(fitness_goals)
            
            # Process experience level
            experience_map = {
                'beginner': 'Beginner',
                'intermediate': 'Intermediate',
                'advanced': 'Advanced',
                'athlete': 'Athlete'
            }
            experience_level_text = experience_map.get(experience_level, experience_level)
            
            # Process availability (convert from array to readable text)
            availability_map = {
                'early_morning': 'Early morning (5-8am)',
                'morning': 'Morning (8-12pm)',
                'afternoon': 'Afternoon (12-5pm)',
                'evening': 'Evening (5-8pm)',
                'flexible': 'Flexible'
            }
            
            if isinstance(availability, list):
                processed_availability = [availability_map.get(slot, slot) for slot in availability]
                availability_text = ', '.join(processed_availability)
            else:
                availability_text = str(availability)
            
            # Process health conditions
            if not health_conditions or health_conditions.lower() in ['none', 'n/a', 'nothing']:
                health_conditions = 'None specified'
            
            return {
                'name': full_name,
                'email': email if email else None,
                'fitness_goals': fitness_goals_text,
                'experience_level': experience_level_text,
                'health_conditions': health_conditions,
                'availability': availability_text,
                'trainer_id': None,  # No trainer assigned yet
                'requested_by': 'client'
            }
            
        except Exception as e:
            log_error(f"Error extracting client data from onboarding flow response: {str(e)}")
            return None
    
    def handle_client_onboarding_request(self, phone_number: str) -> Dict:
        """Main entry point for client onboarding - tries flow first, falls back to text"""
        try:
            log_info(f"Processing client onboarding request for {phone_number}")
            
            # Check if user is already registered as a client
            existing_client = self.supabase.table('clients').select('*').eq('whatsapp', phone_number).execute()
            if existing_client.data:
                client_name = existing_client.data[0].get('name', 'there')
                return {
                    'success': True,
                    'already_registered': True,
                    'message': f"Welcome back, {client_name}! You're already registered as a client. How can I help you today?"
                }
            
            # Try to send WhatsApp Flow with automatic fallback
            result = self.send_client_onboarding_flow(phone_number)
            
            if result.get('success'):
                if result.get('method') == 'text_fallback':
                    # Text registration started successfully
                    return {
                        'success': True,
                        'method': 'text_fallback',
                        'message': result.get('message')
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
                # Both flow and fallback failed
                return {
                    'success': False,
                    'error': result.get('error', 'Client onboarding failed')
                }
                
        except Exception as e:
            log_error(f"Error handling client onboarding request: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_client_onboarding_flow(self, phone_number: str) -> Dict:
        """Send client onboarding flow with automatic fallback to text registration"""
        try:
            log_info(f"Attempting to send client onboarding flow to {phone_number}")

            # Try to send WhatsApp Flow
            flow_result = self._attempt_client_flow_sending(phone_number)

            if flow_result.get('success'):
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'message': 'Client onboarding flow sent successfully',
                    'flow_token': flow_result.get('flow_token')
                }
            else:
                log_info(f"WhatsApp Flow failed for {phone_number}, using text fallback: {flow_result.get('error')}")
                # Automatic fallback to text-based registration
                fallback_result = self._start_text_based_client_registration(phone_number)

                if fallback_result.get('success'):
                    return {
                        'success': True,
                        'method': 'text_fallback',
                        'message': fallback_result.get('message'),
                        'fallback_reason': flow_result.get('error')
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Both flow and fallback failed: {fallback_result.get('error')}"
                    }

        except Exception as e:
            log_error(f"Error sending client onboarding flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def send_trainer_add_client_flow(
        self,
        trainer_phone: str,
        trainer_id: str = None,
        client_name: str = None,
        client_phone: str = None,
        client_email: str = None
    ) -> Dict:
        """
        Send trainer add client flow with dynamic pricing and optional pre-filled client data.
        Passes trainer's default_price_per_session and client contact data as initial flow data.

        Args:
            trainer_phone: Trainer's WhatsApp number
            trainer_id: Optional trainer ID (will lookup if not provided)
            client_name: Optional client name to pre-populate in the flow
            client_phone: Optional client phone to pre-populate in the flow
            client_email: Optional client email to pre-populate in the flow

        Returns:
            Dict with success status and flow_token or error details
        """
        try:
            log_info(f"Sending trainer add client flow to {trainer_phone}")

            # Get trainer data if not provided
            if not trainer_id:
                trainer_result = self.supabase.table('trainers').select('id, default_price_per_session, name').eq(
                    'whatsapp', trainer_phone
                ).execute()

                if not trainer_result.data:
                    return {
                        'success': False,
                        'error': 'Trainer not found'
                    }

                trainer = trainer_result.data[0]
                trainer_id = trainer['id']
                log_info(f"Fetched trainer data: {trainer}")
            else:
                # Fetch trainer data using ID
                trainer_result = self.supabase.table('trainers').select('id, default_price_per_session, name').eq(
                    'id', trainer_id
                ).execute()

                if not trainer_result.data:
                    return {
                        'success': False,
                        'error': 'Trainer not found'
                    }

                trainer = trainer_result.data[0]
                log_info(f"Fetched trainer data: {trainer}")

            # Get trainer's default price (default to R500 if not set)
            trainer_default_price = trainer.get('default_price_per_session', 500)

            # Handle None or 0 values
            if not trainer_default_price or trainer_default_price == 0:
                trainer_default_price = 500
                log_warning(f"Trainer {trainer_id} has no default price set, using R500")

            log_info(f"Trainer default price: R{trainer_default_price}")
            log_info(f"Calculated trainer_default_price: {trainer_default_price}")

            # Generate flow token
            flow_token = f"trainer_add_client_{trainer_phone}_{int(datetime.now().timestamp())}"

            # CRITICAL: Pass trainer_default_price as initial flow data
            # This data cascades through all screens in the flow
            flow_action_payload = {
                "screen": "WELCOME",
                "data": {
                    "trainer_default_price": f"R{int(trainer_default_price)}",  # Format with R prefix as per Flow JSON schema
                    "client_name": client_name or "",
                    "client_phone": client_phone or "",
                    "client_email": client_email or ""
                }
            }

            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": trainer_phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Add New Client"
                    },
                    "body": {
                        "text": "Populate your client's details to create their profile. They'll receive an invitation to review and accept."
                    },
                    "footer": {
                        "text": f"Your default rate: R{int(trainer_default_price)}/session"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": Config.TRAINER_ADD_CLIENT_FLOW_ID,
                            "flow_cta": "Start",
                            "flow_action": "navigate",
                            "flow_action_payload": flow_action_payload
                        }
                    }
                }
            }

            # Store flow token for tracking
            self._store_flow_token(flow_token, {
                'type': 'trainer_add_client',
                'trainer_id': trainer_id,
                'trainer_phone': trainer_phone,
                'trainer_default_price': trainer_default_price,
                'client_name': client_name,
                'client_phone': client_phone,
                'client_email': client_email
            })

            log_info(f"Sending flow with payload: {flow_action_payload}")

            # Send the flow
            result = self.whatsapp_service.send_flow_message(flow_message)

            if result.get('success'):
                log_info(f"Trainer add client flow sent to {trainer_phone}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token,
                    'message': f"Flow sent! Your default rate (R{trainer_default_price}/session) will be shown."
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }

        except Exception as e:
            log_error(f"Error sending trainer add client flow: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _attempt_client_flow_sending(self, phone_number: str) -> Dict:
        """Attempt to send client onboarding WhatsApp Flow"""
        try:
            # Create flow message for client onboarding
            flow_message = self._create_client_onboarding_flow_message(phone_number)
            
            if not flow_message:
                return {
                    'success': False,
                    'error': 'Failed to create client onboarding flow message',
                    'fallback_required': True
                }
            
            # Send via WhatsApp service
            result = self.whatsapp_service.send_flow_message(flow_message)
            
            if result.get('success'):
                # Store flow token for tracking
                self._store_flow_token(phone_number, flow_message['interactive']['action']['parameters']['flow_token'])
                
                return {
                    'success': True,
                    'message': 'Client onboarding flow sent successfully',
                    'flow_token': flow_message['interactive']['action']['parameters']['flow_token']
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send flow message: {result.get("error")}',
                    'fallback_required': True
                }
                
        except Exception as e:
            log_error(f"Error attempting client flow sending: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_required': True
            }
    
    def _create_client_onboarding_flow_message(self, phone_number: str) -> Optional[Dict]:
        """Create WhatsApp flow message for client onboarding"""
        try:
            import json
            import os
            
            # Load the client onboarding flow JSON
            project_root = os.path.dirname(os.path.dirname(__file__))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'client_onboarding_flow.json')
            
            if not os.path.exists(flow_path):
                log_error(f"Client onboarding flow file not found: {flow_path}")
                return None
            
            with open(flow_path, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            
            # Generate flow token
            flow_token = f"client_onboarding_{phone_number}_{int(datetime.now().timestamp())}"
            
            # Create flow message
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Welcome to Refiloe!"
                    },
                    "body": {
                        "text": "Let's get you set up to find the perfect trainer! 🏃‍♀️"
                    },
                    "footer": {
                        "text": "Powered by Refiloe AI"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": "CLIENT_ONBOARDING_FLOW",  # This should match your Facebook Console flow ID
                            "flow_cta": "Get Started",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "WELCOME"
                            }
                        }
                    }
                }
            }
            
            return message
            
        except Exception as e:
            log_error(f"Error creating client onboarding flow message: {str(e)}")
            return None
    
    def _start_text_based_client_registration(self, phone_number: str) -> Dict:
        """Start text-based client registration as fallback"""
        try:
            from services.registration.client_registration import ClientRegistrationHandler
            
            # Initialize client registration handler
            client_reg = ClientRegistrationHandler(self.supabase, self.whatsapp_service)
            
            # Start registration
            welcome_message = client_reg.start_registration(phone_number)
            
            if welcome_message:
                log_info(f"Started text-based client registration for {phone_number}")
                return {
                    'success': True,
                    'message': welcome_message,
                    'method': 'text_based'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to start text-based registration'
                }
                
        except Exception as e:
            log_error(f"Error starting text-based client registration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== HABIT TRACKING FLOWS ====================
    
    def send_trainer_habit_setup_flow(self, phone_number: str, trainer_data: dict) -> Dict:
        """Send trainer habit setup flow"""
        try:
            # Get trainer's clients for the flow with additional info
            clients_result = self.supabase.table('clients').select('id, name, whatsapp, created_at').eq(
                'trainer_id', trainer_data['id']
            ).eq('status', 'active').order('name').execute()
            
            if not clients_result.data:
                return {
                    'success': False,
                    'error': 'No active clients found',
                    'message': 'You need to add clients first before setting up habits. Use `/add_client` to get started!'
                }
            
            # Check which clients already have habits setup
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Prepare client data for flow with habit status
            clients_for_flow = []
            for client in clients_result.data:
                # Check if client has any habits
                client_habits = habits_service.get_client_habits(client['id'], days=30)
                has_habits = client_habits['success'] and client_habits.get('days_tracked', 0) > 0
                
                # Format client display with status
                status_emoji = "✅" if has_habits else "🆕"
                status_text = "Has habits" if has_habits else "New setup"
                
                clients_for_flow.append({
                    "id": client['id'], 
                    "title": f"{status_emoji} {client['name']} ({status_text})",
                    "description": f"Phone: {client.get('whatsapp', 'N/A')}"
                })
            
            # Limit to 10 clients for better UX
            if len(clients_for_flow) > 10:
                clients_for_flow = clients_for_flow[:10]
            
            # Create flow message with client data
            flow_token = f"habit_setup_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "🎯 Setup Client Habits"
                    },
                    "body": {
                        "text": "Help your clients build lasting healthy habits! Choose which habits to track and set personalized goals."
                    },
                    "footer": {
                        "text": "Habit tracking setup"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "trainer_habit_setup_flow",
                            "flow_cta": "Setup Habits",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "clients": clients_for_flow
                                }
                            }
                        }
                    }
                }
            }
            
            # Store flow token
            self._store_flow_token(flow_token, {
                'type': 'trainer_habit_setup',
                'trainer_id': trainer_data['id'],
                'phone': phone_number,
                'clients': clients_result.data
            })
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Trainer habit setup flow sent to {phone_number}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }
                
        except Exception as e:
            log_error(f"Error sending trainer habit setup flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_client_habit_logging_flow(self, phone_number: str, client_data: dict) -> Dict:
        """Send client habit logging flow"""
        try:
            # Get client's active habits
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Check what habits they've been tracking (last 30 days for better detection)
            habits_data = habits_service.get_client_habits(client_data['id'], days=30)
            
            # Determine active habits (habits they've logged in the past 30 days)
            active_habits = []
            if habits_data['success'] and habits_data['data']:
                tracked_habits = set()
                for date_data in habits_data['data'].values():
                    tracked_habits.update(date_data.keys())
                
                # Only include valid habit types
                valid_habits = habits_service.habit_types
                tracked_habits = tracked_habits.intersection(set(valid_habits))
                
                habit_display_names = {
                    'water_intake': '💧 Water Intake',
                    'sleep_hours': '😴 Sleep Hours',
                    'steps': '🚶 Daily Steps',
                    'workout_completed': '💪 Workout',
                    'weight': '⚖️ Weight',
                    'meals_logged': '🍽️ Meals',
                    'calories': '🔥 Calories',
                    'mood': '😊 Mood'
                }
                
                # Get current streaks for each habit to show in title
                for habit in tracked_habits:
                    streak = habits_service.calculate_streak(client_data['id'], habit)
                    streak_text = f" (🔥{streak})" if streak > 0 else ""
                    
                    active_habits.append({
                        "id": habit, 
                        "title": f"{habit_display_names.get(habit, habit.replace('_', ' ').title())}{streak_text}",
                        "description": f"Current streak: {streak} days" if streak > 0 else "No current streak"
                    })
            
            # If no active habits found, they need to set up habits first
            if not active_habits:
                return {
                    'success': False,
                    'error': 'No habits setup',
                    'message': (
                        "🎯 *No habits setup yet!*\n\n"
                        "You need to setup habit tracking first. Ask your trainer to use `/setup_habits` "
                        "to configure your habits, or if you don't have a trainer, you can start with basic habits.\n\n"
                        "Would you like me to help you get started with habit tracking?"
                    )
                }
            
            # Create flow message
            flow_token = f"habit_log_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "📝 Daily Check-in"
                    },
                    "body": {
                        "text": "Time for your daily habit check-in! Let's track your progress and keep those streaks going! 🔥"
                    },
                    "footer": {
                        "text": "Habit logging"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "client_habit_logging_flow",
                            "flow_cta": "Log Habits",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "active_habits": active_habits
                                }
                            }
                        }
                    }
                }
            }
            
            # Store flow token
            self._store_flow_token(flow_token, {
                'type': 'client_habit_logging',
                'client_id': client_data['id'],
                'phone': phone_number,
                'active_habits': active_habits
            })
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Client habit logging flow sent to {phone_number}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }
                
        except Exception as e:
            log_error(f"Error sending client habit logging flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_habit_progress_flow(self, phone_number: str, client_data: dict) -> Dict:
        """Send habit progress flow"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Get current streaks
            streaks = {}
            for habit_type in ['water_intake', 'sleep_hours', 'steps', 'workout_completed']:
                streak = habits_service.calculate_streak(client_data['id'], habit_type)
                streaks[habit_type.replace('_', '')] = streak
            
            # Create flow message with current data
            flow_token = f"habit_progress_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "📊 Your Progress"
                    },
                    "body": {
                        "text": "Check out your habit progress and get personalized insights!"
                    },
                    "footer": {
                        "text": "Progress tracking"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "habit_progress_flow",
                            "flow_cta": "View Progress",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "overview",
                                "data": {
                                    "streaks": streaks
                                }
                            }
                        }
                    }
                }
            }
            
            # Store flow token
            self._store_flow_token(flow_token, {
                'type': 'habit_progress',
                'client_id': client_data['id'],
                'phone': phone_number
            })
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Habit progress flow sent to {phone_number}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }
                
        except Exception as e:
            log_error(f"Error sending habit progress flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_habit_flow_response(self, flow_data: Dict) -> Dict:
        """Handle responses from habit tracking flows"""
        try:
            flow_token = flow_data.get('flow_token')
            if not flow_token:
                return {'success': False, 'error': 'No flow token provided'}
            
            # Get flow context
            token_data = self._get_flow_token_data(flow_token)
            if not token_data:
                return {'success': False, 'error': 'Invalid or expired flow token'}
            
            flow_type = token_data.get('type')
            
            if flow_type == 'trainer_habit_setup':
                return self._handle_trainer_habit_setup_response(flow_data, token_data)
            elif flow_type == 'client_habit_logging':
                return self._handle_client_habit_logging_response(flow_data, token_data)
            elif flow_type == 'habit_progress':
                return self._handle_habit_progress_response(flow_data, token_data)
            else:
                return {'success': False, 'error': f'Unknown habit flow type: {flow_type}'}
                
        except Exception as e:
            log_error(f"Error handling habit flow response: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_trainer_habit_setup_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle trainer habit setup flow completion"""
        try:
            response_data = flow_data.get('response', {})
            trainer_id = token_data.get('trainer_id')
            
            # Extract form data
            selected_client = response_data.get('selected_client')
            selected_habits = response_data.get('selected_habits', [])
            goals = response_data.get('goals', {})
            reminder_time = response_data.get('reminder_time')
            
            if not selected_client or not selected_habits:
                return {
                    'success': False,
                    'error': 'Missing required data',
                    'message': '❌ Please select a client and at least one habit to track.'
                }
            
            # SECURITY: Validate that the selected client belongs to this trainer
            client_validation = self.supabase.table('clients').select('id, name, trainer_id').eq(
                'id', selected_client
            ).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            if not client_validation.data:
                log_error(f"Trainer {trainer_id} attempted to setup habits for unauthorized client {selected_client}")
                return {
                    'success': False,
                    'error': 'Unauthorized client access',
                    'message': '❌ You can only setup habits for your own clients. Please select a valid client.'
                }
            
            client_data = client_validation.data[0]
            
            # Validate selected habits against allowed habit types
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            valid_habits = []
            invalid_habits = []
            
            for habit in selected_habits:
                if habit in habits_service.habit_types:
                    valid_habits.append(habit)
                else:
                    invalid_habits.append(habit)
            
            if invalid_habits:
                log_warning(f"Invalid habits selected: {invalid_habits}")
                return {
                    'success': False,
                    'error': 'Invalid habits selected',
                    'message': f'❌ Invalid habits detected: {", ".join(invalid_habits)}. Please select only valid habit types.'
                }
            
            if not valid_habits:
                return {
                    'success': False,
                    'error': 'No valid habits selected',
                    'message': '❌ No valid habits selected. Please choose at least one habit to track.'
                }
            
            # Setup habits for the client using validated habits
            success_count = 0
            for habit in valid_habits:
                # Initialize habit tracking for this client
                result = habits_service.log_habit(
                    client_data['id'], 
                    habit, 
                    'initialized',
                    datetime.now().date().isoformat()
                )
                if result.get('success'):
                    success_count += 1
                
                # Set goals if provided
                goal_value = goals.get(habit.replace('_', ''))
                if goal_value:
                    habits_service.set_habit_goal(
                        client_data['id'],
                        habit,
                        goal_value,
                        'daily'
                    )
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Send success message with detailed info
            habit_names = [habit.replace('_', ' ').title() for habit in valid_habits]
            
            message = (
                f"🎉 *Habit Tracking Setup Complete!*\n\n"
                f"✅ Client: {client_data['name']}\n"
                f"📊 Habits activated: {len(valid_habits)}\n"
                f"🎯 Habits: {', '.join(habit_names)}\n\n"
                f"Your client can now:\n"
                f"• Use `/log_habit` to log daily habits\n"
                f"• Use `/habit_streak` to check streaks\n"
                f"• Simply tell me what they did (e.g., 'drank 2L water')\n\n"
                f"Track their progress anytime with `/habits`!"
            )
            
            return {
                'success': True,
                'message': message,
                'client_id': client_data['id'],
                'habits_setup': success_count
            }
            
        except Exception as e:
            log_error(f"Error handling trainer habit setup response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error setting up habits. Please try again.'
            }
    
    def _handle_client_habit_logging_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle client habit logging flow completion"""
        try:
            response_data = flow_data.get('response', {})
            client_id = token_data.get('client_id')
            
            if not client_id:
                return {
                    'success': False,
                    'error': 'No client ID in token data',
                    'message': '❌ Session expired. Please try logging habits again.'
                }
            
            # Get client's active habits to validate against
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Get client's previously tracked habits (last 30 days)
            client_habits_data = habits_service.get_client_habits(client_id, days=30)
            
            # Determine which habits this client is allowed to log
            allowed_habits = set()
            if client_habits_data['success'] and client_habits_data['data']:
                for date_data in client_habits_data['data'].values():
                    allowed_habits.update(date_data.keys())
            
            # If no habits found, they haven't been setup yet
            if not allowed_habits:
                return {
                    'success': False,
                    'error': 'No habits setup',
                    'message': (
                        '❌ *No habits setup yet!*\n\n'
                        'You need to setup habit tracking first. Ask your trainer to use `/setup_habits` '
                        'to configure your habits.\n\n'
                        'If you don\'t have a trainer, contact support to get started with habit tracking.'
                    )
                }
            
            # Extract logged habits
            completed_habits = response_data.get('completed_habits', [])
            water_amount = response_data.get('water_amount')
            sleep_hours = response_data.get('sleep_hours')
            steps_count = response_data.get('steps_count')
            weight_kg = response_data.get('weight_kg')
            
            # Validate completed habits against allowed habits
            valid_completed_habits = []
            invalid_habits = []
            
            for habit in completed_habits:
                if habit in allowed_habits:
                    valid_completed_habits.append(habit)
                else:
                    invalid_habits.append(habit)
            
            if invalid_habits:
                log_warning(f"Client {client_id} attempted to log unauthorized habits: {invalid_habits}")
                return {
                    'success': False,
                    'error': 'Unauthorized habits',
                    'message': f'❌ You can only log habits that have been setup for you. Invalid habits: {", ".join(invalid_habits)}'
                }
            
            logged_count = 0
            streaks = {}
            
            # Log boolean habits (completed/not completed)
            for habit in valid_completed_habits:
                result = habits_service.log_habit(client_id, habit, 'completed')
                if result.get('success'):
                    logged_count += 1
                    streaks[habit] = result.get('streak', 0)
            
            # Log measurable habits with specific values (only if allowed)
            measurable_habits = {
                'water_intake': water_amount,
                'sleep_hours': sleep_hours,
                'steps': steps_count,
                'weight': weight_kg
            }
            
            for habit_type, value in measurable_habits.items():
                if value and habit_type in allowed_habits:
                    result = habits_service.log_habit(client_id, habit_type, str(value))
                    if result.get('success'):
                        logged_count += 1
                        streaks[habit_type] = result.get('streak', 0)
                elif value and habit_type not in allowed_habits:
                    log_warning(f"Client {client_id} attempted to log unauthorized measurable habit: {habit_type}")
            
            # If no habits were logged, inform the user
            if logged_count == 0:
                return {
                    'success': False,
                    'error': 'No habits logged',
                    'message': (
                        '❌ *No habits were logged.*\n\n'
                        'This could be because:\n'
                        '• No habits were selected\n'
                        '• The selected habits are not setup for you\n\n'
                        'Please make sure you have habits setup and try again.'
                    )
                }
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Generate success message with streaks
            message = f"🎉 *Habits Logged Successfully!*\n\n"
            message += f"✅ {logged_count} habits recorded for today\n\n"
            
            if streaks:
                message += "*🔥 Current Streaks:*\n"
                for habit, streak in sorted(streaks.items(), key=lambda x: x[1], reverse=True):
                    habit_name = habit.replace('_', ' ').title()
                    fire_emoji = '🔥' * min(streak // 3, 5)
                    message += f"• {habit_name}: {streak} days {fire_emoji}\n"
                message += "\n"
            
            message += "💪 *Keep up the amazing work! Consistency is key to success!*"
            
            return {
                'success': True,
                'message': message,
                'habits_logged': logged_count,
                'streaks': streaks
            }
            
        except Exception as e:
            log_error(f"Error handling client habit logging response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error logging habits. Please try again.'
            }
    
    def _handle_habit_progress_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle habit progress flow completion"""
        try:
            response_data = flow_data.get('response', {})
            selected_action = response_data.get('selected_action')
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Handle the selected action
            if selected_action == 'log_today':
                message = (
                    "📝 *Ready to log today's habits!*\n\n"
                    "Use `/log_habit` to start logging, or just tell me what you did:\n\n"
                    "Examples:\n"
                    "• 'drank 2 liters water'\n"
                    "• 'slept 8 hours'\n"
                    "• 'workout completed'\n"
                    "• 'walked 10000 steps'"
                )
            elif selected_action == 'set_goals':
                message = (
                    "🎯 *Goal Setting*\n\n"
                    "Goal management is coming soon! For now, focus on building consistency.\n\n"
                    "Remember: Small daily actions lead to big results! 💪"
                )
            elif selected_action == 'view_streaks':
                message = (
                    "🔥 *Check Your Streaks*\n\n"
                    "Use `/habit_streak` to see all your current streaks and get motivated!"
                )
            elif selected_action == 'get_tips':
                message = (
                    "💡 *Habit Building Tips*\n\n"
                    "🎯 Start small - even 1% better each day adds up\n"
                    "🔗 Stack habits - link new habits to existing ones\n"
                    "📅 Be consistent - same time, same place\n"
                    "🎉 Celebrate wins - acknowledge your progress\n"
                    "💪 Focus on identity - 'I am someone who...'\n\n"
                    "You've got this! Keep building those healthy habits! 🌟"
                )
            else:
                message = "Thanks for checking your progress! Keep up the great work! 💪"
            
            return {
                'success': True,
                'message': message,
                'action': selected_action
            }
            
        except Exception as e:
            log_error(f"Error handling habit progress response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error processing your request. Please try again.'
            }
    
    def _store_flow_token(self, token: str, data: Dict) -> bool:
        """Store flow token data for later retrieval"""
        try:
            result = self.supabase.table('flow_tokens').insert({
                'token': token,
                'data': data,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
            }).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error storing flow token: {str(e)}")
            return False
    
    def _get_flow_token_data(self, token: str) -> Optional[Dict]:
        """Retrieve flow token data"""
        try:
            result = self.supabase.table('flow_tokens').select('*').eq(
                'token', token
            ).gte('expires_at', datetime.now().isoformat()).execute()
            
            if result.data:
                return result.data[0]['data']
            return None
            
        except Exception as e:
            log_error(f"Error retrieving flow token data: {str(e)}")
            return None
    
    def _cleanup_flow_token(self, token: str) -> bool:
        """Clean up used flow token"""
        try:
            result = self.supabase.table('flow_tokens').delete().eq('token', token).execute()
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error cleaning up flow token: {str(e)}")
            return False  
            
    def handle_encrypted_flow_response(self, data: Dict) -> Dict:
        """Handle encrypted WhatsApp Flow responses"""
        try:
            log_info("Processing encrypted WhatsApp Flow response")
            
            # Extract encrypted data components
            encrypted_flow_data = data.get('encrypted_flow_data')
            encrypted_aes_key = data.get('encrypted_aes_key')
            initial_vector = data.get('initial_vector')
            
            if not all([encrypted_flow_data, encrypted_aes_key, initial_vector]):
                return {
                    'success': False,
                    'error': 'Missing required encryption components'
                }
            
            # Try to extract phone number from various sources
            from flask import request
            phone_number = None
            
            # Method 1: Check WhatsApp headers (skip signature headers)
            if hasattr(request, 'headers'):
                phone_number = (request.headers.get('X-WhatsApp-Phone-Number') or 
                              request.headers.get('X-WhatsApp-From') or
                              request.headers.get('From'))
            
            # Method 2: Check request data
            if not phone_number and hasattr(request, 'json'):
                request_data = request.get_json() or {}
                phone_number = (request_data.get('phone_number') or
                              request_data.get('from') or
                              request_data.get('sender'))
            
            # Method 3: Try to get from recent webhook data (skip for now to avoid database dependency)
            # This would require the webhook_logs table to exist
            
            # Method 4: For testing, use a default test number
            if not phone_number or phone_number.startswith('sha256='):
                # Use your actual WhatsApp number for testing
                phone_number = '+27730564882'  # Your test number
                log_info(f"Using test phone number for encrypted flow: {phone_number}")
            
            # If we still don't have phone number, return a more helpful error
            if not phone_number:
                log_warning("Phone number not found in request, flow data, or recent webhooks")
                
                # For now, return success but log that we couldn't identify the user
                # This prevents the flow from failing completely
                return {
                    'success': True,
                    'message': 'Flow received but user identification pending',
                    'note': 'Phone number extraction from encrypted data not implemented'
                }
            
            # Clean phone number format
            if phone_number and not phone_number.startswith('+'):
                if phone_number.startswith('27'):
                    phone_number = '+' + phone_number
                elif phone_number.startswith('0'):
                    phone_number = '+27' + phone_number[1:]
                else:
                    phone_number = '+' + phone_number
            
            log_info(f"Processing encrypted flow for phone: {phone_number}")
            
            # Create a mock flow response structure for existing handler
            # In production, you would decrypt the actual form data here
            mock_flow_response = {
                'name': 'trainer_onboarding_flow',  # Default flow type
                'flow_token': f"encrypted_{int(datetime.now().timestamp())}",
                'data': {
                    # Mock data - in production this would be decrypted from encrypted_flow_data
                    'first_name': 'Test',
                    'surname': 'User',
                    'email': f'test.{phone_number.replace("+", "").replace(" ", "")}@example.com',
                    'city': 'Test City',
                    'business_name': 'Test Business',
                    'specializations': ['Weight Loss'],
                    'experience_years': '2-3',
                    'pricing_per_session': 500,
                    'available_days': ['Monday', 'Wednesday', 'Friday'],
                    'preferred_time_slots': 'Morning (6AM-12PM)',  # Added missing field
                    'subscription_plan': 'free',  # Added missing field
                    'terms_accepted': True,
                    'additional_notes': 'Registered via encrypted flow'
                }
            }
            
            # Create flow data structure expected by existing handler
            flow_data = {
                'phone_number': phone_number,
                'flow_response': mock_flow_response
            }
            
            # Delegate to existing flow response handler
            result = self.handle_flow_response(flow_data)
            
            if result.get('success'):
                log_info(f"Successfully processed encrypted flow for {phone_number}")
                return {
                    'success': True,
                    'message': result.get('message', 'Flow processed successfully'),
                    'phone_number': phone_number
                }
            else:
                log_error(f"Failed to process encrypted flow: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Flow processing failed')
                }
                
        except Exception as e:
            log_error(f"Error handling encrypted flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _decrypt_flow_data(self, encrypted_data: str, encrypted_key: str, iv: str) -> Dict:
        """
        Decrypt WhatsApp Flow data (placeholder implementation)
        
        In production, you would:
        1. Decrypt the AES key using your private key
        2. Use the decrypted AES key and IV to decrypt the flow data
        3. Parse the decrypted JSON data
        
        For now, this returns empty data as decryption requires proper key management
        """
        try:
            # This is a placeholder - implement actual decryption logic here
            log_warning("Flow data decryption not implemented - using mock data")
            
            return {
                'decrypted': False,
                'data': {},
                'error': 'Decryption not implemented'
            }
            
        except Exception as e:
            log_error(f"Error decrypting flow data: {str(e)}")
            return {
                'decrypted': False,
                'data': {},
                'error': str(e)
            }