"""
WhatsApp Flow-based Trainer Onboarding Service

This service handles trainer onboarding using WhatsApp Flows (interactive forms)
for a streamlined registration experience. South African context (ZA phone numbers, Rand currency).
"""
from typing import Dict, Optional
from datetime import datetime
import pytz

from utils.logger import log_info, log_error, log_warning
from services.auth import AuthenticationService
from services.auth.registration.data_saver import DataSaver


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
        
        # Initialize services
        self.auth_service = AuthenticationService(supabase)
        self.data_saver = DataSaver(supabase, self.auth_service)

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
            # Check for existing active flow tokens and mark as abandoned
            self._mark_abandoned_flows(phone_number)
            
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
            
            # Extract flow_token from flow_data
            flow_token = flow_data.get('flow_token', '')

            # Extract all fields from flow_data
            # Basic info
            first_name = flow_data.get('first_name', '').strip()
            surname = flow_data.get('surname', '').strip()
            email = flow_data.get('email', '').strip().lower()
            city = flow_data.get('city', '').strip()
            sex = flow_data.get('sex', '')
            birthdate = flow_data.get('birthdate', '')
            
            # Business details
            business_name = flow_data.get('business_name', '')
            specializations = flow_data.get('specializations', [])  # Array from CheckboxGroup
            experience_years = flow_data.get('experience_years', '')
            pricing_per_session = flow_data.get('pricing_per_session', '')
            
            # Preferences
            subscription_plan = flow_data.get('subscription_plan', 'basic')
            
            # Business setup
            services_offered = flow_data.get('services_offered', [])  # Array from CheckboxGroup
            
            # Terms
            terms_accepted = flow_data.get('terms_accepted', False)
            additional_notes = flow_data.get('additional_notes', '')
            
            # Legacy fields (for backward compatibility)
            notification_preferences = flow_data.get('notification_preferences', [])
            marketing_consent = flow_data.get('marketing_consent', False)

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
                
                # Mark flow token as failed
                if flow_token:
                    try:
                        self.db.table('flow_tokens').update({
                            'status': 'failed',
                            'error': error_msg,
                            'completed_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('flow_token', flow_token).execute()
                    except Exception as e:
                        log_warning(f"Failed to update flow token status: {str(e)}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'validation_errors': validation_errors
                }

            # Check if trainer already exists
            existing_trainer = self._get_trainer_by_phone(phone_number)
            if existing_trainer:
                log_warning(f"Trainer already exists with phone {phone_number}")
                
                # Mark flow token as failed
                if flow_token:
                    try:
                        self.db.table('flow_tokens').update({
                            'status': 'failed',
                            'error': 'Trainer already registered',
                            'completed_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('flow_token', flow_token).execute()
                    except Exception as e:
                        log_warning(f"Failed to update flow token status: {str(e)}")
                
                return {
                    'success': False,
                    'error': 'Trainer already registered with this phone number',
                    'trainer_id': existing_trainer.get('id')  # UUID from trainers.id
                }

            # Check if email already in use
            existing_email = self._get_trainer_by_email(email)
            if existing_email:
                log_warning(f"Trainer already exists with email {email}")
                
                # Mark flow token as failed
                if flow_token:
                    try:
                        self.db.table('flow_tokens').update({
                            'status': 'failed',
                            'error': 'Email already registered',
                            'completed_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('flow_token', flow_token).execute()
                    except Exception as e:
                        log_warning(f"Failed to update flow token status: {str(e)}")
                
                return {
                    'success': False,
                    'error': 'This email is already registered',
                    'trainer_id': existing_email.get('id')  # UUID from trainers.id
                }

            # Prepare data for data_saver
            # Build working_hours JSONB from weekly availability
            working_hours = self._build_working_hours(flow_data)
            
            # Prepare registration data dict
            registration_data = {
                'first_name': first_name,
                'surname': surname,
                'email': email,
                'city': city,
                'sex': sex,
                'birthdate': birthdate,
                'business_name': business_name,
                'specializations': specializations,  # Array
                'experience_years': experience_years,
                'pricing_per_session': pricing_per_session,
                'working_hours': working_hours,  # JSONB
                'services_offered': services_offered,
                'subscription_plan': subscription_plan,
                'notification_preferences': notification_preferences,
                'terms_accepted': terms_accepted,
                'marketing_consent': marketing_consent,
                'additional_notes': additional_notes
            }
            
            # Use data_saver to save trainer registration
            log_info(f"Saving trainer via data_saver: {first_name} {surname} ({email})")
            success, message, trainer_id = self.data_saver.save_trainer_registration(
                phone_number, 
                registration_data,
                method='flow'
            )
            
            if success:
                log_info(f"✅ Trainer created successfully via data_saver: {trainer_id}")
                
                # Build custom confirmation message
                specialization_text = ', '.join(specializations) if specializations else None
                
                confirmation_msg = (
                    f"🎊 *Welcome aboard, {first_name}!*\n\n"
                    f"Your trainer profile is now active. 🚀\n\n"
                    f"✅ Registration complete\n"
                    f"📧 Email: {email}\n"
                )

                if city:
                    confirmation_msg += f"📍 Location: {city}\n"

                if specialization_text:
                    confirmation_msg += f"💪 Specialization: {specialization_text}\n"

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
                
                # Mark flow token as completed and clean up old tokens
                if flow_token:
                    try:
                        # Mark current token as completed
                        self.db.table('flow_tokens').update({
                            'status': 'completed',
                            'completed_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('flow_token', flow_token).execute()
                        log_info(f"Flow token marked as completed: {flow_token}")
                        
                        # Delete any old failed/abandoned/active tokens (but not this completed one)
                        self.db.table('flow_tokens').delete().eq(
                            'phone_number', phone_number
                        ).eq('flow_type', 'trainer_onboarding').neq(
                            'flow_token', flow_token
                        ).in_('status', ['failed', 'abandoned', 'active']).execute()
                        log_info(f"Cleaned up old flow tokens for {phone_number}")
                    except Exception as e:
                        log_warning(f"Failed to update flow token status: {str(e)}")

                return {
                    'success': True,
                    'trainer_id': trainer_id,
                    'trainer_name': f"{first_name} {surname}",
                    'email': email,
                    'method': 'flow_registration_complete'
                }
            else:
                log_error(f"Failed to save trainer: {message}")
                
                # Mark flow token as failed
                if flow_token:
                    try:
                        self.db.table('flow_tokens').update({
                            'status': 'failed',
                            'error': message,
                            'completed_at': datetime.now(self.sa_tz).isoformat()
                        }).eq('flow_token', flow_token).execute()
                    except Exception as e:
                        log_warning(f"Failed to update flow token status: {str(e)}")
                
                return {
                    'success': False,
                    'error': message
                }

        except Exception as e:
            log_error(f"Error processing flow completion: {str(e)}", exc_info=True)
            
            # Mark flow token as failed
            flow_token = flow_data.get('flow_token', '')
            if flow_token:
                try:
                    self.db.table('flow_tokens').update({
                        'status': 'failed',
                        'error': str(e),
                        'completed_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('flow_token', flow_token).execute()
                except Exception as update_error:
                    log_warning(f"Failed to update flow token status: {str(update_error)}")
            
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

    def _update_users_table(self, phone_number: str, trainer_id: str) -> bool:
        """
        Create or update users table entry to link phone number to trainer_id

        Args:
            phone_number: Trainer's WhatsApp phone number
            trainer_id: VARCHAR trainer_id (e.g., "TR_JOHN_123")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Clean phone number for users table (remove +, -, spaces)
            clean_phone = phone_number.replace('+', '').replace('-', '').replace(' ', '')

            # Check if user entry exists
            existing_user = self.db.table('users').select('*').eq(
                'phone_number', clean_phone
            ).execute()

            if existing_user.data:
                # Update existing user entry with trainer_id and login_status
                self.db.table('users').update({
                    'trainer_id': trainer_id,  # VARCHAR ID like "TR_JOHN_123"
                    'login_status': 'trainer',  # Auto-login after registration
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('phone_number', clean_phone).execute()
                log_info(f"Updated users table for trainer: {clean_phone} with trainer_id: {trainer_id}, login_status: trainer")
            else:
                # Create new user entry with trainer_id and login_status
                self.db.table('users').insert({
                    'phone_number': clean_phone,
                    'trainer_id': trainer_id,  # VARCHAR ID like "TR_JOHN_123"
                    'login_status': 'trainer',  # Auto-login after registration
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                log_info(f"Created users table entry for trainer: {clean_phone} with trainer_id: {trainer_id}, login_status: trainer")

            return True

        except Exception as e:
            log_error(f"Error creating/updating users table: {str(e)}")
            # Don't fail the whole registration if users table update fails
            return False

    def _generate_trainer_id(self, first_name: str, surname: str) -> str:
        """
        Generate unique VARCHAR trainer_id like "TR_JOHN_123"

        Args:
            first_name: Trainer's first name
            surname: Trainer's surname

        Returns:
            Unique trainer_id string (e.g., "TR_JOHN_123")
        """
        import random
        import string

        try:
            # Clean and format name part (use first 4 chars of first name)
            name_part = (first_name[:4] if first_name else 'USER').upper()
            # Remove non-alphanumeric characters
            name_part = ''.join(c for c in name_part if c.isalnum())

            # Generate random 3-digit suffix
            suffix = ''.join(random.choices(string.digits, k=3))

            # Construct trainer_id
            trainer_id = f"TR_{name_part}_{suffix}"

            # Check uniqueness in database
            existing = self.db.table('trainers').select('id').eq('trainer_id', trainer_id).execute()

            if existing.data:
                # If exists, regenerate with different suffix
                log_info(f"Trainer ID {trainer_id} already exists, regenerating...")
                return self._generate_trainer_id(first_name, surname)

            log_info(f"Generated unique trainer_id: {trainer_id}")
            return trainer_id

        except Exception as e:
            log_error(f"Error generating trainer_id: {str(e)}")
            # Fallback to timestamp-based ID
            timestamp = datetime.now(self.sa_tz).strftime('%H%M%S')
            fallback_id = f"TR_USER_{timestamp}"
            log_warning(f"Using fallback trainer_id: {fallback_id}")
            return fallback_id

    def _build_working_hours(self, flow_data: Dict) -> Dict:
        """
        Build working_hours JSONB structure from flow availability data
        
        Args:
            flow_data: Complete flow data with availability fields
        
        Returns:
            Dict with structure:
            {
                "monday": {"preset": "business", "hours": ["08-09", "09-10", ...]},
                "tuesday": {"preset": "morning", "hours": []},
                ...
            }
        """
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        working_hours = {}
        
        for day in days:
            preset_key = f"{day}_preset"
            hours_key = f"{day}_hours"
            
            preset = flow_data.get(preset_key, 'not_available')
            hours = flow_data.get(hours_key, [])
            
            # Ensure hours is a list
            if isinstance(hours, str):
                hours = [h.strip() for h in hours.split(',') if h.strip()]
            elif not isinstance(hours, list):
                hours = []
            
            working_hours[day] = {
                "preset": preset,
                "hours": hours
            }
        
        log_info(f"Built working_hours structure with {len(working_hours)} days")
        return working_hours

    def _extract_available_days(self, working_hours: Dict) -> list:
        """
        Extract list of available days from working_hours for backward compatibility
        
        Args:
            working_hours: JSONB working hours structure
        
        Returns:
            List of day names where trainer is available (e.g., ["Monday", "Wednesday", "Friday"])
        """
        available_days = []
        
        for day, schedule in working_hours.items():
            preset = schedule.get('preset', 'not_available')
            
            # Consider available if preset is not "not_available"
            if preset and preset != 'not_available':
                # Capitalize day name
                available_days.append(day.capitalize())
        
        return available_days

    def _extract_preferred_time_slots(self, working_hours: Dict) -> str:
        """
        Extract preferred time slots description from working_hours for backward compatibility
        
        Args:
            working_hours: JSONB working hours structure
        
        Returns:
            Text description of preferred times (e.g., "Morning, Evening")
        """
        time_preferences = set()
        
        for day, schedule in working_hours.items():
            preset = schedule.get('preset', 'not_available')
            
            # Map presets to time slot descriptions
            if preset == 'morning':
                time_preferences.add('Morning')
            elif preset == 'evening':
                time_preferences.add('Evening')
            elif preset == 'business':
                time_preferences.add('Business Hours')
            elif preset == 'full_day':
                time_preferences.add('Full Day')
        
        # Return comma-separated unique preferences
        return ', '.join(sorted(time_preferences)) if time_preferences else None

    def _mark_abandoned_flows(self, phone_number: str) -> None:
        """
        Delete any existing flow tokens for this phone (active, failed, or abandoned)
        Keeps database clean by removing old tokens when user requests new flow
        
        Args:
            phone_number: Trainer's phone number
        """
        try:
            # Delete all non-completed flow tokens for this phone
            # Keep 'completed' tokens for reference, delete everything else
            result = self.db.table('flow_tokens').delete().eq(
                'phone_number', phone_number
            ).eq('flow_type', 'trainer_onboarding').neq('status', 'completed').execute()
            
            if result.data:
                log_info(f"Deleted {len(result.data)} old flow token(s) for {phone_number}")
        
        except Exception as e:
            log_warning(f"Error cleaning up old flows: {str(e)}")
            # Don't fail the flow send if this fails
