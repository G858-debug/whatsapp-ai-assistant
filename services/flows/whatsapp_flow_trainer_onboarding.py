"""
WhatsApp Flow-based Trainer Onboarding Service

This service handles trainer onboarding using WhatsApp Flows (interactive forms)
for a streamlined registration experience. South African context (ZA phone numbers, Rand currency).
"""
from typing import Dict, Optional
from datetime import datetime
import pytz

from utils.logger import log_info, log_error, log_warning


class WhatsAppFlowTrainerOnboarding:
    """Handle WhatsApp Flow-based trainer onboarding"""

    def __init__(self, supabase, whatsapp_service):
        """
        Initialize WhatsApp Flow Trainer Onboarding

        Args:
            supabase: Supabase client for database operations
            whatsapp_service: WhatsApp service for sending messages/flows
        """
        self.db = supabase
        self.whatsapp = whatsapp_service
        self.flow_id = "775047838492907"
        self.flow_name = "trainer_onboarding_flow"
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

        log_info("WhatsAppFlowTrainerOnboarding initialized")

    def send_flow(self, phone_number: str) -> Dict:
        """
        Send WhatsApp Flow to trainer for onboarding

        Args:
            phone_number: Trainer's WhatsApp number (ZA format)

        Returns:
            Dict with success status, flow_token, or error message
        """
        try:
            # Generate unique flow token for this onboarding session
            timestamp = datetime.now(self.sa_tz).strftime('%Y%m%d%H%M%S')
            flow_token = f"trainer_onboarding_{phone_number}_{timestamp}"

            log_info(f"Sending trainer onboarding flow to {phone_number}, token: {flow_token}")

            # Create WhatsApp Flow message structure
            flow_message = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "🚀 Get Ready!"
                    },
                    "body": {
                        "text": "Let's set up your trainer profile! This takes about 2 minutes and will help clients find you easily. 💪"
                    },
                    "footer": {
                        "text": "Your journey to fitness success starts here!"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": self.flow_id,
                            "flow_cta": "Start Setup",
                            "flow_action": "data_exchange"
                        }
                    }
                }
            }

            # Send flow via WhatsApp service
            result = self.whatsapp.send_flow_message(flow_message)

            if result.get('success'):
                log_info(f"✅ Flow sent successfully to {phone_number}")

                # Save flow token to database for tracking
                self._save_flow_token(phone_number, flow_token)

                return {
                    'success': True,
                    'flow_token': flow_token,
                    'message_id': result.get('message_id'),
                    'method': 'whatsapp_flow'
                }
            else:
                log_error(f"❌ Failed to send flow to {phone_number}: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to send flow'),
                    'method': 'whatsapp_flow_failed'
                }

        except Exception as e:
            log_error(f"Error sending trainer onboarding flow: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'method': 'whatsapp_flow_error'
            }

    def process_flow_completion(self, flow_data: Dict, phone_number: str) -> Dict:
        """
        Process completed flow data and create trainer profile

        Args:
            flow_data: Data submitted from the WhatsApp Flow
            phone_number: Trainer's WhatsApp number

        Returns:
            Dict with success status, trainer_id if successful, or error details
        """
        try:
            log_info(f"Processing flow completion for {phone_number}")
            log_info(f"Flow data received: {flow_data}")

            # Extract all fields from flow_data
            first_name = flow_data.get('first_name', '').strip()
            surname = flow_data.get('surname', '').strip()
            email = flow_data.get('email', '').strip().lower()
            city = flow_data.get('city', '').strip()
            specialization = flow_data.get('specialization', '').strip()
            experience_years = flow_data.get('experience_years', '')
            pricing_per_session = flow_data.get('pricing_per_session', '')
            available_days = flow_data.get('available_days', [])
            preferred_time_slots = flow_data.get('preferred_time_slots', '')
            subscription_plan = flow_data.get('subscription_plan', 'free')
            notification_preferences = flow_data.get('notification_preferences', [])
            marketing_consent = flow_data.get('marketing_consent', False)
            terms_accepted = flow_data.get('terms_accepted', False)

            # Additional fields that might come from the flow
            business_name = flow_data.get('business_name', '')

            # Validate required fields
            validation_errors = []

            if not first_name:
                validation_errors.append("First name is required")
            if not surname:
                validation_errors.append("Surname is required")
            if not email:
                validation_errors.append("Email is required")
            if not terms_accepted:
                validation_errors.append("You must accept the terms and conditions")

            # Validate pricing_per_session if provided (must be positive number)
            if pricing_per_session:
                try:
                    price_value = float(pricing_per_session)
                    if price_value <= 0:
                        validation_errors.append("Price per session must be a positive number")
                except (ValueError, TypeError):
                    validation_errors.append("Price per session must be a valid number")

            if validation_errors:
                error_msg = "Validation errors: " + ", ".join(validation_errors)
                log_warning(f"Flow validation failed for {phone_number}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'validation_errors': validation_errors
                }

            # Check if trainer already exists
            existing_trainer = self._get_trainer_by_phone(phone_number)
            if existing_trainer:
                log_warning(f"Trainer already exists with phone {phone_number}")
                return {
                    'success': False,
                    'error': 'Trainer already registered with this phone number',
                    'trainer_id': existing_trainer.get('id')  # UUID from trainers.id
                }

            # Check if email already in use
            existing_email = self._get_trainer_by_email(email)
            if existing_email:
                log_warning(f"Trainer already exists with email {email}")
                return {
                    'success': False,
                    'error': 'This email is already registered',
                    'trainer_id': existing_email.get('id')  # UUID from trainers.id
                }

            # Prepare trainer data for database
            full_name = f"{first_name} {surname}"

            trainer_data = {
                'whatsapp': phone_number,
                'name': full_name,
                'first_name': first_name,
                'last_name': surname,
                'email': email,
                'city': city if city else None,
                'location': city if city else None,  # Alias for backward compatibility
                'specialization': specialization if specialization else None,
                'experience_years': self._parse_experience_years(experience_years or '0'),
                'years_experience': self._parse_experience_years(experience_years or '0'),  # Alias
                'pricing_per_session': int(float(pricing_per_session)) if pricing_per_session else None,
                'status': 'active',
                'onboarding_method': 'flow',
                'terms_accepted': terms_accepted,
                'marketing_consent': marketing_consent,
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }

            # Add optional fields
            if business_name:
                trainer_data['business_name'] = business_name

            # Handle JSONB fields
            if available_days:
                # Convert to list if it's a string or ensure it's a proper list
                if isinstance(available_days, str):
                    trainer_data['available_days'] = [day.strip() for day in available_days.split(',')]
                else:
                    trainer_data['available_days'] = available_days

            if preferred_time_slots:
                trainer_data['preferred_time_slots'] = preferred_time_slots

            if notification_preferences:
                # Ensure it's a list
                if isinstance(notification_preferences, str):
                    trainer_data['notification_preferences'] = [pref.strip() for pref in notification_preferences.split(',')]
                else:
                    trainer_data['notification_preferences'] = notification_preferences

            # Set default empty working_hours JSONB
            trainer_data['working_hours'] = {}

            # Save trainer to database
            log_info(f"Saving trainer to database: {full_name} ({email})")
            result = self.db.table('trainers').insert(trainer_data).execute()

            if result.data and len(result.data) > 0:
                # Get the UUID 'id' field (not 'trainer_id' VARCHAR) from insert result
                # Database triggers ensure trainers.trainer_id VARCHAR stays synced with trainers.id UUID
                trainer_id = result.data[0]['id']
                trainer_whatsapp = result.data[0]['whatsapp']

                log_info(f"✅ Trainer created successfully: {full_name} (ID: {trainer_id})")

                # Create or update users table entry to link phone number to trainer
                try:
                    # Check if user entry exists
                    existing_user = self.db.table('users').select('*').eq(
                        'phone_number', trainer_whatsapp
                    ).execute()

                    if existing_user.data:
                        # Update existing user entry
                        # Use UUID from trainers.id (not trainers.trainer_id VARCHAR)
                        self.db.table('users').update({
                            'trainer_id': trainer_id,
                            'updated_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('phone_number', trainer_whatsapp).execute()
                        log_info(f"Updated users table for trainer: {trainer_whatsapp}")
                    else:
                        # Create new user entry
                        # Use UUID from trainers.id (not trainers.trainer_id VARCHAR)
                        self.db.table('users').insert({
                            'phone_number': trainer_whatsapp,
                            'trainer_id': trainer_id,
                            'created_at': datetime.now(self.sa_tz).isoformat(),
                            'updated_at': datetime.now(self.sa_tz).isoformat()
                        }).execute()
                        log_info(f"Created users table entry for trainer: {trainer_whatsapp}")

                except Exception as user_error:
                    log_error(f"Error creating/updating users table: {str(user_error)}")
                    # Don't fail the whole registration if users table update fails

                # Send confirmation message
                confirmation_msg = (
                    f"🎊 *Welcome aboard, {first_name}!*\n\n"
                    f"Your trainer profile is now active. 🚀\n\n"
                    f"✅ Registration complete\n"
                    f"📧 Email: {email}\n"
                )

                if city:
                    confirmation_msg += f"📍 Location: {city}\n"

                if specialization:
                    confirmation_msg += f"💪 Specialization: {specialization}\n"

                # Display pricing in R[amount] format if provided
                if pricing_per_session:
                    try:
                        price_value = float(pricing_per_session)
                        confirmation_msg += f"💰 Default Price: R{price_value:.0f} per session\n"
                    except (ValueError, TypeError):
                        pass

                confirmation_msg += (
                    f"\n"
                    f"You can now:\n"
                    f"• Add clients to your roster\n"
                    f"• Schedule training sessions\n"
                    f"• Track client progress\n"
                    f"• Manage your business\n\n"
                    f"Type 'help' anytime to see what I can do for you! 💬"
                )

                # Send confirmation via WhatsApp
                self.whatsapp.send_message(phone_number, confirmation_msg)

                return {
                    'success': True,
                    'trainer_id': trainer_id,
                    'trainer_name': full_name,
                    'email': email,
                    'method': 'flow_registration_complete'
                }
            else:
                log_error(f"Failed to insert trainer into database: {result}")
                return {
                    'success': False,
                    'error': 'Failed to save trainer to database',
                    'details': str(result)
                }

        except Exception as e:
            log_error(f"Error processing flow completion: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error processing registration: {str(e)}"
            }

    def _save_flow_token(self, phone_number: str, flow_token: str) -> bool:
        """
        Save flow token to database for tracking

        Args:
            phone_number: Trainer's phone number
            flow_token: Unique flow session token

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            token_data = {
                'flow_token': flow_token,
                'phone_number': phone_number,
                'flow_type': 'trainer_onboarding',
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }

            result = self.db.table('flow_tokens').insert(token_data).execute()

            if result.data:
                log_info(f"Flow token saved: {flow_token}")
                return True
            else:
                log_warning(f"Failed to save flow token: {flow_token}")
                return False

        except Exception as e:
            log_error(f"Error saving flow token: {str(e)}")
            return False

    def _get_trainer_by_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Get trainer by phone number

        Args:
            phone_number: Trainer's WhatsApp number

        Returns:
            Trainer dict if found, None otherwise
        """
        try:
            result = self.db.table('trainers').select('*').eq(
                'whatsapp', phone_number
            ).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            log_error(f"Error getting trainer by phone: {str(e)}")
            return None

    def _get_trainer_by_email(self, email: str) -> Optional[Dict]:
        """
        Get trainer by email

        Args:
            email: Trainer's email address

        Returns:
            Trainer dict if found, None otherwise
        """
        try:
            result = self.db.table('trainers').select('*').eq(
                'email', email.lower()
            ).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            log_error(f"Error getting trainer by email: {str(e)}")
            return None

    def _parse_experience_years(self, experience_str: str) -> int:
        """
        Convert experience years string to integer.

        Examples:
            "0-1" -> 0
            "2-3" -> 2
            "4-5" -> 4
            "6-10" -> 6
            "10+" -> 10

        Args:
            experience_str: Experience range string from flow

        Returns:
            Integer representing years of experience (lower bound of range)
        """
        try:
            # Handle "10+" case
            if '+' in experience_str:
                return int(experience_str.replace('+', '').strip())

            # Handle range like "2-3"
            if '-' in experience_str:
                # Take the lower bound of the range
                return int(experience_str.split('-')[0].strip())

            # Handle single number
            return int(experience_str)

        except (ValueError, AttributeError):
            log_warning(f"Could not parse experience years: {experience_str}, defaulting to 0")
            return 0
