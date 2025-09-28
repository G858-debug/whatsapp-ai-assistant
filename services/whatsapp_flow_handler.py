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
    
    def create_and_publish_flow(self) -> Dict:
        """Create and publish the trainer onboarding flow in WhatsApp Business Manager"""
        try:
            # Check if flow already exists
            existing_flow = self.get_flow_by_name("trainer_onboarding_flow")
            if existing_flow.get('success'):
                log_info("Flow already exists, using existing flow")
                return {'success': True, 'flow_id': existing_flow.get('flow_id')}
            
            # Create the flow
            flow_data = {
                "name": "trainer_onboarding_flow",
                "categories": ["UTILITY"],
                "version": "7.3",
                "screens": self.flow_data.get('screens', [])
            }
            
            result = self._create_flow_via_api(flow_data)
            if result.get('success'):
                log_info(f"Flow created successfully: {result.get('flow_id')}")
                return result
            else:
                log_error(f"Failed to create flow: {result.get('error')}")
                return result
                
        except Exception as e:
            log_error(f"Error creating and publishing flow: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_flow_by_name(self, flow_name: str) -> Dict:
        """Get flow by name from WhatsApp Business Manager"""
        try:
            # This would require implementing the Flows API
            # For now, return a placeholder
            return {'success': False, 'error': 'Flow lookup not implemented'}
        except Exception as e:
            log_error(f"Error getting flow by name: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _create_flow_via_api(self, flow_data: Dict) -> Dict:
        """Create flow via WhatsApp Business API"""
        try:
            # This would require implementing the Flows API
            # For now, return a placeholder indicating manual setup required
            log_warning("Flow creation via API not implemented. Flow must be created manually in WhatsApp Business Manager.")
            return {
                'success': False, 
                'error': 'Flow must be created manually in WhatsApp Business Manager first',
                'message': 'Please create the flow "trainer_onboarding_flow" in your WhatsApp Business Manager'
            }
        except Exception as e:
            log_error(f"Error creating flow via API: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_trainer_onboarding_flow(self, phone_number: str) -> Dict:
        """Send the trainer onboarding flow to a phone number"""
        try:
            # Check if user is already a trainer
            existing_trainer = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if existing_trainer.data:
                return {
                    'success': False,
                    'error': 'User is already registered as a trainer',
                    'message': 'You are already registered as a trainer! If you need help, please contact support.'
                }
            
            # Ensure flow exists and is published
            flow_result = self.create_and_publish_flow()
            if not flow_result.get('success'):
                log_warning(f"Flow not available: {flow_result.get('error')}")
                return {
                    'success': False,
                    'error': 'Flow not available',
                    'message': 'WhatsApp Flow registration is not available. Please use text-based registration.',
                    'fallback_required': True
                }
            
            # Create flow message
            flow_message = self.create_flow_message(phone_number)
            if not flow_message:
                return {
                    'success': False,
                    'error': 'Failed to create flow message'
                }
            
            # Send via WhatsApp service using the flow message method
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
                    'error': 'Failed to send flow message',
                    'details': result.get('error')
                }
                
        except Exception as e:
            log_error(f"Error sending trainer onboarding flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_flow_response(self, flow_data: Dict) -> Dict:
        """Process completed trainer onboarding flow"""
        try:
            flow_name = flow_data.get('name')
            if flow_name != 'trainer_onboarding_flow':
                return {
                    'success': False,
                    'error': 'Invalid flow type'
                }
            
            # Extract flow action payload - updated for new structure
            action_payload = flow_data.get('flow_action_payload', {})
            flow_token = flow_data.get('flow_token')
            
            if not action_payload or not flow_token:
                return {
                    'success': False,
                    'error': 'Missing flow data'
                }
            
            # Check if flow was completed (reached terminal screen)
            if action_payload.get('screen') != 'registration_complete':
                return {
                    'success': False,
                    'error': 'Flow not completed',
                    'message': 'Please complete all steps in the registration flow'
                }
            
            # Extract form data from the new structure
            trainer_data = self._extract_trainer_data_from_flow(action_payload)
            
            if not trainer_data:
                return {
                    'success': False,
                    'error': 'Failed to extract trainer data'
                }
            
            # Validate required fields
            validation_result = self._validate_trainer_data(trainer_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation_result['errors']
                }
            
            # Create trainer record
            trainer_id = self._create_trainer_record(trainer_data, flow_token)
            
            if trainer_id:
                # Send confirmation message
                confirmation_message = self._create_confirmation_message(trainer_data)
                self.whatsapp_service.send_message(trainer_data['phone'], confirmation_message)
                
                return {
                    'success': True,
                    'message': 'Trainer profile created successfully',
                    'trainer_id': trainer_id,
                    'confirmation_sent': True
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
