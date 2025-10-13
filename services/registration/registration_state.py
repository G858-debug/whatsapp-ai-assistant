"""Registration state management for trainers and clients"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class RegistrationStateManager:
    """Manages registration flow state"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Registration steps
        self.TRAINER_STEPS = [
            'name', 'business_name', 'email', 'specialization', 
            'experience', 'location', 'pricing'
        ]
        
        self.CLIENT_STEPS = [
            'name', 'email', 'fitness_goals', 'experience_level',
            'health_conditions', 'availability'
        ]
    
    def get_registration_state(self, phone: str) -> Optional[Dict]:
        """Get current registration state"""
        try:
            result = self.db.table('registration_states').select('*').eq(
                'phone_number', phone
            ).eq('completed', False).single().execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            log_error(f"Error getting registration state: {str(e)}")
            return None
    
    def create_registration_state(self, phone: str, user_type: str) -> Dict:
        """Create new registration state"""
        try:
            state_data = {
                'phone_number': phone,
                'user_type': user_type,
                'current_step': 0,
                'data': {},
                'completed': False,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('registration_states').insert(
                state_data
            ).execute()
            
            return result.data[0] if result.data else state_data
            
        except Exception as e:
            log_error(f"Error creating registration state: {str(e)}")
            return {}
    
    def update_registration_state(self, phone: str, step: int, 
                                 data: Dict, completed: bool = False) -> bool:
        """Update registration state"""
        try:
            update_data = {
                'current_step': step,
                'data': data,
                'completed': completed,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if completed:
                update_data['completed_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('registration_states').update(
                update_data
            ).eq('phone_number', phone).eq('completed', False).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating registration state: {str(e)}")
            return False
    
    def complete_registration(self, phone: str, user_type: str) -> bool:
        """Mark registration as completed"""
        try:
            update_data = {
                'completed': True,
                'completed_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('registration_states').update(
                update_data
            ).eq('phone_number', phone).eq('user_type', user_type).eq('completed', False).execute()
            
            if result.data:
                log_info(f"Marked registration as complete for {phone} ({user_type})")
                return True
            else:
                log_warning(f"No registration state found to complete for {phone}")
                return False
            
        except Exception as e:
            log_error(f"Error completing registration state: {str(e)}")
            return False
    
    def get_progress_percentage(self, phone: str) -> int:
        """Calculate registration progress percentage"""
        state = self.get_registration_state(phone)
        if not state:
            return 0
        
        user_type = state.get('user_type', 'trainer')
        current_step = state.get('current_step', 0)
        total_steps = len(self.TRAINER_STEPS if user_type == 'trainer' else self.CLIENT_STEPS)
        
        if total_steps == 0:
            return 0
        
        # Calculate percentage, ensuring it doesn't exceed 100%
        percentage = min(100, int((current_step / total_steps) * 100))
        
        log_info(f"Registration progress for {phone}: {current_step}/{total_steps} ({percentage}%)")
        return percentage
    
    def can_resume_registration(self, phone: str) -> bool:
        """Check if user can resume interrupted registration"""
        state = self.get_registration_state(phone)
        if not state:
            return False
        
        # Check if already completed
        if state.get('completed', False):
            return False
        
        # Check if registration was started within last 24 hours
        created_at = state.get('created_at')
        if created_at:
            try:
                from datetime import datetime, timedelta
                
                # Handle different datetime formats
                if created_at.endswith('Z'):
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_time = datetime.fromisoformat(created_at)
                
                # Convert to SA timezone for comparison
                if created_time.tzinfo is None:
                    created_time = self.sa_tz.localize(created_time)
                
                now = datetime.now(self.sa_tz)
                time_diff = now - created_time
                
                # Allow resume within 24 hours
                can_resume = time_diff < timedelta(hours=24)
                
                log_info(f"Registration resume check for {phone}: created {time_diff} ago, can_resume: {can_resume}")
                return can_resume
                
            except Exception as e:
                log_error(f"Error parsing created_at time for {phone}: {str(e)}")
                # If we can't parse the time, allow resume (safer default)
                return True
        
        # If no created_at timestamp, allow resume
        return True
    
    def is_registration_expired(self, phone: str) -> bool:
        """Check if registration has expired and should be cleaned up"""
        state = self.get_registration_state(phone)
        if not state:
            return False
        
        # Don't expire completed registrations
        if state.get('completed', False):
            return False
        
        created_at = state.get('created_at')
        if created_at:
            try:
                from datetime import datetime, timedelta
                
                if created_at.endswith('Z'):
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_time = datetime.fromisoformat(created_at)
                
                if created_time.tzinfo is None:
                    created_time = self.sa_tz.localize(created_time)
                
                now = datetime.now(self.sa_tz)
                time_diff = now - created_time
                
                # Expire after 48 hours (double the resume window)
                is_expired = time_diff > timedelta(hours=48)
                
                if is_expired:
                    log_info(f"Registration expired for {phone}: created {time_diff} ago")
                
                return is_expired
                
            except Exception as e:
                log_error(f"Error checking expiration for {phone}: {str(e)}")
                return False
        
        return False
    
    def cleanup_expired_registrations(self) -> int:
        """Clean up expired registration states"""
        try:
            from datetime import datetime, timedelta
            
            # Calculate cutoff time (48 hours ago)
            cutoff_time = datetime.now(self.sa_tz) - timedelta(hours=48)
            cutoff_iso = cutoff_time.isoformat()
            
            # Delete expired, incomplete registrations
            result = self.db.table('registration_states').delete().lt(
                'created_at', cutoff_iso
            ).eq('completed', False).execute()
            
            deleted_count = len(result.data) if result.data else 0
            
            if deleted_count > 0:
                log_info(f"Cleaned up {deleted_count} expired registration states")
            
            return deleted_count
            
        except Exception as e:
            log_error(f"Error cleaning up expired registrations: {str(e)}")
            return 0
    
    def get_registration_summary(self, phone: str) -> Dict:
        """Get comprehensive registration summary"""
        state = self.get_registration_state(phone)
        if not state:
            return {
                'exists': False,
                'progress_percentage': 0,
                'can_resume': False,
                'is_expired': False
            }
        
        user_type = state.get('user_type', 'trainer')
        current_step = state.get('current_step', 0)
        total_steps = len(self.TRAINER_STEPS if user_type == 'trainer' else self.CLIENT_STEPS)
        
        return {
            'exists': True,
            'user_type': user_type,
            'current_step': current_step,
            'total_steps': total_steps,
            'progress_percentage': self.get_progress_percentage(phone),
            'can_resume': self.can_resume_registration(phone),
            'is_expired': self.is_registration_expired(phone),
            'completed': state.get('completed', False),
            'created_at': state.get('created_at'),
            'updated_at': state.get('updated_at'),
            'data': state.get('data', {})
        }
    
    def get_progress(self, phone: str, user_type: str) -> tuple:
        """Get registration progress (legacy method for compatibility)"""
        state = self.get_registration_state(phone)
        if not state:
            return 0, 0
        
        total_steps = len(self.TRAINER_STEPS if user_type == 'trainer' else self.CLIENT_STEPS)
        current_step = state.get('current_step', 0)
        
        return current_step, total_steps