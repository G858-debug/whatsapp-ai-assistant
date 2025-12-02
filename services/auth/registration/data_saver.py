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
    
    def save_trainer_registration(self, phone: str, data: Dict, method: str = 'flow') -> Tuple[bool, str, Optional[str]]:
        """
        Save trainer registration data (supports both chat and flow methods)
        
        Args:
            phone: Trainer's phone number
            data: Registration data dict
            method: Registration method ('chat' or 'flow')
        
        Returns: (success, message, trainer_id)
        """
        try:
            # Use original phone format for trainers table (with +)
            # Clean phone only for users table
            
            # Generate unique trainer ID using user_manager
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '') or data.get('surname', '')
            name = f"{first_name} {last_name}".strip()
            
            from services.auth.core.user_manager import UserManager
            user_manager = UserManager(self.db)
            trainer_id = user_manager.generate_unique_id(name, 'trainer')
            
            # Get years_experience - should already be parsed by flow handler
            years_experience = data.get('years_experience', 0)
            
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
                'years_experience': years_experience,
                'pricing_per_session': int(float(data.get('pricing_per_session', 500))) if data.get('pricing_per_session') else 500,
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
            # Should already be prepared by flow handler with available_days and preferred_time_slots
            working_hours = data.get('working_hours', {})
            if working_hours:
                trainer_data['working_hours'] = working_hours
            
            # Use pre-extracted values (already processed by flow handler)
            if data.get('available_days') is not None:
                trainer_data['available_days'] = data.get('available_days')
            
            if data.get('preferred_time_slots') is not None:
                trainer_data['preferred_time_slots'] = data.get('preferred_time_slots')
            
            # Insert into trainers table
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                # Create or update users table entry with auto-login
                # user_manager already initialized above
                user_manager.create_or_update_user_with_role(phone, 'trainer', trainer_id)
                
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
            # Generate unique client ID using user_manager
            name = data.get('full_name', '')
            
            from services.auth.core.user_manager import UserManager
            user_manager = UserManager(self.db)
            client_id = user_manager.generate_unique_id(name, 'client')
            
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
                # Create or update users table entry
                # user_manager already initialized above
                
                # For self-registration, auto-login; for trainer-created, don't auto-login
                if not created_by_trainer:
                    # Self-registration: create user entry with auto-login
                    user_manager.create_or_update_user_with_role(client_phone, 'client', client_id)
                else:
                    # Trainer-created: create user entry without auto-login
                    self.auth_service.create_user_entry(clean_phone, 'client', client_id)
                
                # If created by trainer, establish relationship
                if created_by_trainer and trainer_id:
                    self._create_trainer_client_relationship(trainer_id, client_id, 'trainer')
                
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
    
    