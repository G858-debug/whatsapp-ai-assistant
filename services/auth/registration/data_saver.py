"""
Data Saver
Handles registration data saving operations
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
from utils.logger import log_info, log_error


class DataSaver:
    """Handles registration data saving and relationship creation"""
    
    def __init__(self, supabase_client, auth_service):
        self.db = supabase_client
        self.auth_service = auth_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def save_trainer_registration(self, phone: str, data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Save trainer registration data (supports both chat and flow methods)
        
        Args:
            phone: Trainer's phone number
            data: Registration data dict
        
        Returns: (success, message, trainer_id)
        """
        try:
            # Use original phone format for trainers table (with +)
            # Clean phone only for users table
            
            # Generate unique trainer ID
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '') or data.get('surname', '')
            name = f"{first_name} {last_name}".strip()
            trainer_id = self.auth_service.generate_unique_id(name, 'trainer')
            
            # Prepare trainer data - map all fields from config to database schema
            trainer_data = {
                'trainer_id': trainer_id,
                'whatsapp': phone,  # Use original phone format (with +)
                'name': name,
                'first_name': first_name,
                'last_name': last_name,
                'email': data.get('email'),
                'city': data.get('city'),
                'location': data.get('city'),  # Keep both for compatibility
                'business_name': data.get('business_name'),
                'experience_years': data.get('experience_years'),
                'years_experience': self._parse_experience_to_number(data.get('experience_years')),
                'pricing_per_session': float(data.get('pricing_per_session', 500)) if data.get('pricing_per_session') else 500.0,
                'services_offered': data.get('services_offered', []) if data.get('services_offered') else [],
                'pricing_flexibility': data.get('pricing_flexibility', []) if data.get('pricing_flexibility') else [],
                'additional_notes': data.get('additional_notes'),
                'status': 'active',
                'registration_method': method,
                'onboarding_method': method,
                'terms_accepted': data.get('terms_accepted', True),
                'marketing_consent': data.get('marketing_consent', False),
                'notification_preferences': data.get('notification_preferences', []) if data.get('notification_preferences') else [],
                'subscription_status': data.get('subscription_plan', 'free') or 'free',
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Sex and birthdate
            if data.get('sex'):
                trainer_data['sex'] = data.get('sex')
            if data.get('birthdate'):
                trainer_data['birthdate'] = data.get('birthdate')
            
            # Specializations array (new field from migration)
            specializations_arr = data.get('specializations', [])
            if isinstance(specializations_arr, list) and specializations_arr:
                trainer_data['specializations_arr'] = specializations_arr
                # Also set legacy specialization field as comma-separated text
                trainer_data['specialization'] = ', '.join(specializations_arr)
            
            # Working hours (new field from migration)
            working_hours = data.get('working_hours', {})
            if working_hours:
                trainer_data['working_hours'] = working_hours
                # Extract available_days and preferred_time_slots for legacy fields
                trainer_data['available_days'] = self._extract_available_days(working_hours)
                trainer_data['preferred_time_slots'] = self._extract_preferred_time_slots(working_hours)
            
            # Insert into trainers table
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                # Create user entry with cleaned phone
                clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
                user_data = {
                    'phone_number': clean_phone,
                    'trainer_id': trainer_id,
                    'login_status': 'trainer',  # Auto-login
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                self.db.table('users').insert(user_data).execute()
                
                log_info(f"Trainer registered successfully: {trainer_id} via {method}")
                
                message = (f"🎉 *Registration Successful!*\n\n"
                          f"Your trainer ID: *{trainer_id}*\n\n"
                          f"You are now logged in as a trainer. "
                          f"You can start inviting clients and managing your training business!\n\n"
                          f"Type /help to see available commands.")
                
                return True, message, trainer_id
            else:
                return False, "Failed to save registration data. Please try again.", None
            
        except Exception as e:
            log_error(f"Error saving trainer registration: {str(e)}")
            return False, f"Registration error: {str(e)}", None
    
    def save_client_registration(self, phone: str, data: Dict, created_by_trainer: bool = False, trainer_id: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Save client registration data
        Returns: (success, message, client_id)
        """
        try:
            # Generate unique client ID
            name = data.get('full_name', '')
            client_id = self.auth_service.generate_unique_id(name, 'client')
            
            # Determine client phone number
            # If created by trainer, use phone from data (trainer provided it)
            # If self-registration, use webhook phone
            client_phone = data.get('phone_number', phone) if created_by_trainer else phone
            
            # Clean phone number
            clean_phone = client_phone.replace('+', '').replace('-', '').replace(' ', '')
            
            # Prepare client data
            client_data = {
                'client_id': client_id,
                'whatsapp': clean_phone,
                'name': name,
                'email': data.get('email'),
                'fitness_goals': data.get('fitness_goals', []) if data.get('fitness_goals') else [],  # Store as list
                'experience_level': data.get('experience_level'),
                'health_conditions': data.get('health_conditions'),
                'availability': data.get('availability', []) if data.get('availability') else [],  # Store as list
                'preferred_training_times': data.get('preferred_training_type', []) if data.get('preferred_training_type') else [],  # Store as list
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into clients table
            result = self.db.table('clients').insert(client_data).execute()
            
            if result.data:
                # Create user entry with correct phone number
                self.auth_service.create_user_entry(clean_phone, 'client', client_id)
                
                # If created by trainer, establish relationship
                if created_by_trainer and trainer_id:
                    self._create_trainer_client_relationship(trainer_id, client_id, 'trainer')
                
                # Set login status (only for self-registration, not trainer-created)
                if not created_by_trainer:
                    self.auth_service.set_login_status(clean_phone, 'client')
                
                log_info(f"Client registered successfully: {client_id}")
                
                if created_by_trainer:
                    message = (f"🎉 *Registration Successful!*\n\n"
                              f"Client ID: *{client_id}*\n\n"
                              f"The client has been added to your roster and can now access all client features.")
                else:
                    message = (f"🎉 *Registration Successful!*\n\n"
                              f"Your client ID: *{client_id}*\n\n"
                              f"You are now logged in as a client. "
                              f"You can start searching for trainers and tracking your fitness journey!\n\n"
                              f"Type /help to see available commands.")
                
                return True, message, client_id
            else:
                return False, "Failed to save registration data. Please try again.", None
            
        except Exception as e:
            log_error(f"Error saving client registration: {str(e)}")
            return False, f"Registration error: {str(e)}", None
    
    def _create_trainer_client_relationship(self, trainer_id: str, client_id: str, invited_by: str) -> bool:
        """Create bidirectional trainer-client relationship"""
        try:
            now = datetime.now(self.sa_tz).isoformat()
            
            # Add to trainer_client_list
            self.db.table('trainer_client_list').insert({
                'trainer_id': trainer_id,
                'client_id': client_id,
                'connection_status': 'active',
                'invited_by': invited_by,
                'approved_at': now,
                'created_at': now,
                'updated_at': now
            }).execute()
            
            # Add to client_trainer_list
            self.db.table('client_trainer_list').insert({
                'client_id': client_id,
                'trainer_id': trainer_id,
                'connection_status': 'active',
                'invited_by': invited_by,
                'approved_at': now,
                'created_at': now,
                'updated_at': now
            }).execute()
            
            log_info(f"Created relationship: trainer {trainer_id} <-> client {client_id}")
            return True
            
        except Exception as e:
            log_error(f"Error creating relationship: {str(e)}")
            return False
    
    def _parse_experience_to_number(self, experience_text: str) -> int:
        """
        Convert experience text to number for years_experience field
        
        Handles both formats:
        - "0-1 years" (chat-based)
        - "0-1" or "10+" (flow-based)
        """
        if not experience_text:
            return 0
        
        # Handle flow format (e.g., "0-1", "2-3", "10+")
        if '+' in experience_text:
            return int(experience_text.replace('+', '').strip())
        
        if '-' in experience_text and 'years' not in experience_text:
            # Flow format: "2-3" -> take lower bound
            return int(experience_text.split('-')[0].strip())
        
        # Handle chat format (e.g., "0-1 years", "2-3 years")
        experience_map = {
            '0-1 years': 1,
            '2-3 years': 3,
            '4-5 years': 5,
            '6-10 years': 8,
            '10+ years': 12
        }
        
        return experience_map.get(experience_text, 0)
        

    def _extract_available_days(self, working_hours: Dict) -> list:
        """Extract list of available days from working_hours for legacy field"""
        available_days = []
        for day, schedule in working_hours.items():
            preset = schedule.get('preset', 'not_available')
            if preset and preset != 'not_available':
                available_days.append(day.capitalize())
        return available_days
    
    def _extract_preferred_time_slots(self, working_hours: Dict) -> str:
        """Extract preferred time slots description from working_hours for legacy field"""
        time_preferences = set()
        for day, schedule in working_hours.items():
            preset = schedule.get('preset', 'not_available')
            if preset == 'morning':
                time_preferences.add('Morning')
            elif preset == 'evening':
                time_preferences.add('Evening')
            elif preset == 'business':
                time_preferences.add('Business Hours')
            elif preset == 'full_day':
                time_preferences.add('Full Day')
        return ', '.join(sorted(time_preferences)) if time_preferences else None    