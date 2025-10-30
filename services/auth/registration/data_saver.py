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
        Save trainer registration data
        Returns: (success, message, trainer_id)
        """
        try:
            # Clean phone number (remove + and other formatting)
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            # Generate unique trainer ID
            name = f"{data.get('first_name', '')} {data.get('last_name', '')}"
            trainer_id = self.auth_service.generate_unique_id(name, 'trainer')
            
            # Prepare trainer data - map all fields from config to database schema
            trainer_data = {
                'trainer_id': trainer_id,
                'whatsapp': clean_phone,  # Use cleaned phone number
                'name': name,
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'email': data.get('email'),
                'city': data.get('city'),
                'location': data.get('city'),  # Keep both for compatibility
                'business_name': data.get('business_name'),
                'specialization': data.get('specialization', []) if data.get('specialization') else [],  # Store as list
                'experience_years': data.get('experience_years'),
                'years_experience': self._parse_experience_to_number(data.get('experience_years')),  # Keep both for compatibility
                'pricing_per_session': float(data.get('pricing_per_session', 500)) if data.get('pricing_per_session') else 500.0,
                'available_days': data.get('available_days', []) if data.get('available_days') else [],  # Store as list
                'preferred_time_slots': data.get('preferred_time_slots'),
                'services_offered': data.get('services_offered', []) if data.get('services_offered') else [],  # Store as list
                'pricing_flexibility': data.get('pricing_flexibility', []) if data.get('pricing_flexibility') else [],  # Store as list
                'additional_notes': data.get('additional_notes'),
                'status': 'active',
                'registration_method': 'chat',
                'onboarding_method': 'chat',
                'terms_accepted': True,  # Assume accepted during registration
                'marketing_consent': False,  # Default to false
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into trainers table
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                # Create user entry
                self.auth_service.create_user_entry(phone, 'trainer', trainer_id)
                
                # Set login status
                self.auth_service.set_login_status(phone, 'trainer')
                
                log_info(f"Trainer registered successfully: {trainer_id}")
                
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
        """Convert experience text to number for years_experience field"""
        if not experience_text:
            return 0
        
        experience_map = {
            '0-1 years': 1,
            '2-3 years': 3,
            '4-5 years': 5,
            '6-10 years': 8,
            '10+ years': 12
        }
        
        return experience_map.get(experience_text, 0)