## ANALYSIS

The error shows that `models/trainer.py` is trying to import a class called `Trainer` but the file only contains `TrainerModel`. Looking at the code:

1. In `app.py` line 24: `from models.trainer import Trainer` - expects a class named `Trainer`
2. In `models/trainer.py`: The class is actually named `TrainerModel`

Similarly, looking at other model files:
- `models/client.py` has `ClientModel` not `Client`
- `models/booking.py` has `BookingModel` not `Booking`

The app.py file is trying to import these with the wrong names. We need to either:
1. Fix the imports in app.py to use the correct class names, OR
2. Add the expected class names as aliases in the model files

I'll fix this by updating the model files to export the expected class names.

## FILES TO CHANGE

### FILE: models/trainer.py
```python
from typing import Dict, Optional, List
from datetime import datetime
import pytz

from utils.logger import log_error, log_info

class TrainerModel:
    """Handle all trainer-related database operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get trainer by phone number"""
        try:
            result = self.db.table('trainers').select('*').eq(
                'whatsapp', phone_number
            ).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error getting trainer by phone: {str(e)}")
            return None
    
    def get_by_id(self, trainer_id: str) -> Optional[Dict]:
        """Get trainer by ID"""
        try:
            result = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting trainer by ID: {str(e)}")
            return None
    
    def create_trainer(self, trainer_data: Dict) -> Dict:
        """Create a new trainer"""
        try:
            # Validate required fields
            required = ['name', 'whatsapp', 'email']
            for field in required:
                if field not in trainer_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Set defaults
            trainer_data.setdefault('status', 'active')
            trainer_data.setdefault('pricing_per_session', self.config.DEFAULT_SESSION_PRICE)
            trainer_data['created_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('trainers').insert(trainer_data).execute()
            
            if result.data:
                log_info(f"Trainer created: {trainer_data['name']}")
                return {
                    'success': True,
                    'trainer_id': result.data[0]['id']
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create trainer'
                }
                
        except Exception as e:
            log_error(f"Error creating trainer: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_trainer(self, trainer_id: str, update_data: Dict) -> Dict:
        """Update trainer information"""
        try:
            update_data['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('trainers').update(update_data).eq(
                'id', trainer_id
            ).execute()
            
            if result.data:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Trainer not found'}
                
        except Exception as e:
            log_error(f"Error updating trainer: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_trainer_stats(self, trainer_id: str) -> Dict:
        """Get trainer statistics"""
        try:
            # Get client count
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            # Get booking count for this month
            now = datetime.now(self.sa_tz)
            month_start = now.replace(day=1, hour=0, minute=0, second=0)
            
            bookings = self.db.table('bookings').select('id, price, status').eq(
                'trainer_id', trainer_id
            ).gte('session_datetime', month_start.isoformat()).execute()
            
            # Calculate stats
            total_clients = len(clients.data)
            total_bookings = len(bookings.data)
            completed_bookings = sum(1 for b in bookings.data if b['status'] == 'completed')
            revenue = sum(b['price'] for b in bookings.data if b['status'] in ['completed', 'scheduled'])
            
            return {
                'total_clients': total_clients,
                'monthly_bookings': total_bookings,
                'completed_sessions': completed_bookings,
                'monthly_revenue': revenue
            }
            
        except Exception as e:
            log_error(f"Error getting trainer stats: {str(e)}")
            return {
                'total_clients': 0,
                'monthly_bookings': 0,
                'completed_sessions': 0,
                'monthly_revenue': 0
            }

# Create an alias for backward compatibility
Trainer = TrainerModel
```

### FILE: models/client.py
```python
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pytz

from utils.logger import log_error, log_info

class ClientModel:
    """Handle all client-related database operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get client by phone number with trainer info"""
        try:
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('whatsapp', phone_number).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            log_error(f"Error getting client by phone: {str(e)}")
            return None
    
    def get_by_id(self, client_id: str) -> Optional[Dict]:
        """Get client by ID"""
        try:
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('id', client_id).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting client by ID: {str(e)}")
            return None
    
    def add_client(self, trainer_id: str, client_details: Dict) -> Dict:
        """Add a new client"""
        try:
            # Validate required fields
            if not client_details.get('name') or not client_details.get('phone'):
                return {
                    'success': False,
                    'error': 'Name and phone number are required'
                }
            
            # Get package details
            package = client_details.get('package', 'single')
            sessions = self.config.PACKAGE_SESSIONS.get(package, 1)
            
            # Prepare client record
            client_data = {
                'trainer_id': trainer_id,
                'name': client_details['name'],
                'whatsapp': client_details['phone'],
                'email': client_details.get('email'),
                'sessions_remaining': sessions,
                'package_type': package,
                'status': 'active',
                'custom_price_per_session': client_details.get('price'),  # ADD THIS LINE
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Check if client already exists
            existing = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('whatsapp', client_details['phone']).execute()
            
            if existing.data:
                return {
                    'success': False,
                    'error': 'Client with this phone number already exists'
                }
            
            # Insert client
            result = self.db.table('clients').insert(client_data).execute()
            
            if result.data:
                log_info(f"Client added: {client_details['name']} for trainer {trainer_id}")
                return {
                    'success': True,
                    'client_id': result.data[0]['id'],
                    'sessions': sessions
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add client'
                }
                
        except Exception as e:
            log_error(f"Error adding client: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_trainer_clients(self, trainer_id: str, status: str = 'active') -> List[Dict]:
        """Get all clients for a trainer"""
        try:
            query = self.db.table('clients').select('*').eq(
                'trainer_id', trainer_id
            )
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('name').execute()
            return result.data
            
        except Exception as e:
            log_error(f"Error getting trainer clients: {str(e)}")
            return []
    
    def update_client(self, client_id: str, update_data: Dict) -> Dict:
        """Update client information"""
        try:
            update_data['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('clients').update(update_data).eq(
                'id', client_id
            ).execute()
            
            if result.data:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Client not found'}
                
        except Exception as e:
            log_error(f"Error updating client: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_sessions(self, client_id: str, sessions_to_add: int) -> Dict:
        """Add sessions to a client's balance"""
        try:
            # Get current sessions
            client = self.get_by_id(client_id)
            if not client:
                return {'success': False, 'error': 'Client not found'}
            
            new_balance = client['sessions_remaining'] + sessions_to_add
            
            result = self.db.table('clients').update({
                'sessions_remaining': new_balance,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', client_id).execute()
            
            if result.data:
                log_info(f"Added {sessions_to_add} sessions to client {client_id}")
                return {'success': True, 'new_balance': new_balance}
            else:
                return {'success': False, 'error': 'Failed to update sessions'}
                
        except Exception as e:
            log_error(f"Error adding sessions: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_clients_needing_reminders(self, days_inactive: int = 7) -> List[Dict]:
        """Get clients who haven't had sessions in X days"""
        try:
            cutoff_date = (datetime.now(self.sa_tz) - timedelta(days=days_inactive)).isoformat()
            
            result = self.db.table('clients').select(
                '*, trainers(*)'
            ).eq('status', 'active').or_(
                f"last_session_date.lt.{cutoff_date},last_session_date.is.null"
            ).execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting clients needing reminders: {str(e)}")
            return []

# Create an alias for backward compatibility
Client = ClientModel
```

### FILE: models/booking.py
```python
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, List
import uuid

from utils.logger import log_error, log_info

class BookingModel:
    """Handle all booking-related database operations with concurrency control"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_booking(self, trainer_id: str, client_id: str, session_datetime: datetime, 
                      price: float, duration_minutes: int = 60) -> Dict:
        """
        Create a new booking with concurrency protection
        Returns: Dict with success status and booking data or error message
        """
        try:
            # Step 1: Check if slot is available (with lock)
            if not self.is_slot_available(trainer_id, session_datetime, duration_minutes):
                log_info(f"Booking conflict for trainer {trainer_id} at {session_datetime}")
                return {
                    'success': False,
                    'error': 'This time slot is no longer available',
                    'alternatives': self.get_alternative_slots(trainer_id, session_datetime)
                }
            
            # Step 2: Create unique booking ID for idempotency
            booking_id = str(uuid.uuid4())
            
            # Step 3: Calculate end time
            end_time = session_datetime + timedelta(minutes=duration_minutes)
            
            try:
                client_result = self.db.table('clients').select('custom_price_per_session').eq(
                    'id', client_id
                ).single().execute()
                
                if client_result.data and client_result.data.get('custom_price_per_session'):
                    price = float(client_result.data['custom_price_per_session'])
                    log_info(f"Using custom price R{price} for client {client_id}")
            except Exception as e:
                log_error(f"Error fetching custom price, using provided price: {str(e)}")
                # Continue with the price parameter passed to the function
            
            # Step 4: Insert booking with all details
            booking_data = {
                'id': booking_id,
                'trainer_id': trainer_id,
                'client_id': client_id,
                'session_datetime': session_datetime.isoformat(),
                'end_datetime': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'price': price,
                'status': 'scheduled',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('bookings').insert(booking_data).execute()
            
            if result.data:
                log_info(f"Booking created: {booking_id} for client {client_id}")
                
                # Update client's last session date and remaining sessions
                self.update_client_after_booking(client_id)
                
                return {
                    'success': True,
                    'booking': result.data[0],
                    'message': 'Booking confirmed successfully'
                }
            else:
                raise Exception("No data returned from booking insert")
                
        except Exception as e:
            log_error(f"Error creating booking: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to create booking. Please try again.'
            }
    
    def is_slot_available(self, trainer_id: str, start_time: datetime, 
                         duration_minutes: int = 60) -> bool:
        """
        Check if a time slot is available for booking
        Uses database query to ensure accuracy
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Query for overlapping bookings
            # A slot overlaps if:
            # - Existing booking starts before our end time AND
            # - Existing booking ends after our start time
            existing_bookings = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).eq(
                'status', 'scheduled'
            ).lt(
                'session_datetime', end_time.isoformat()
            ).gt(
                'end_datetime', start_time.isoformat()
            ).execute()
            
            # If no overlapping bookings found, slot is available
            is_available = len(existing_bookings.data) == 0
            
            if not is_available:
                log_info(f"Slot conflict found: {len(existing_bookings.data)} overlapping bookings")
            
            return is_available
            
        except Exception as e:
            log_error(f"Error checking slot availability: {str(e)}")
            # Err on the side of caution - if we can't check, assume it's not available
            return False
    
    def get_alternative_slots(self, trainer_id: str, preferred_time: datetime, 
                            days_to_check: int = 3) -> List[Dict]:
        """Get alternative available slots near the preferred time"""
        alternatives = []
        
        try:
            # Get trainer's working hours
            booking_slots = self.config.get_booking_slots()
            
            # Check slots for the next few days
            for day_offset in range(days_to_check):
                check_date = preferred_time.date() + timedelta(days=day_offset)
                day_name = check_date.strftime('%A').lower()
                
                if day_name in booking_slots:
                    for time_slot in booking_slots[day_name]:
                        # Create datetime for this slot
                        hour, minute = map(int, time_slot.split(':'))
                        slot_datetime = datetime.combine(
                            check_date, 
                            datetime.min.time().replace(hour=hour, minute=minute)
                        )
                        slot_datetime = self.sa_tz.localize(slot_datetime)
                        
                        # Skip if in the past
                        if slot_datetime < datetime.now(self.sa_tz):
                            continue
                        
                        # Check if available
                        if self.is_slot_available(trainer_id, slot_datetime):
                            alternatives.append({
                                'datetime': slot_datetime.isoformat(),
                                'display': slot_datetime.strftime('%A %d %B at %I:%M%p')
                            })
                        
                        # Return up to 5 alternatives
                        if len(alternatives) >= 5:
                            return alternatives
            
        except Exception as e:
            log_error(f"Error getting alternative slots: {str(e)}")
        
        return alternatives
    
    def cancel_booking(self, booking_id: str, reason: Optional[str] = None) -> Dict:
        """Cancel a booking"""
        try:
            # Get booking details first
            booking = self.db.table('bookings').select('*').eq('id', booking_id).single().execute()
            
            if not booking.data:
                return {'success': False, 'error': 'Booking not found'}
            
            # Update booking status
            update_data = {
                'status': 'cancelled',
                'cancelled_at': datetime.now(self.sa_tz).isoformat(),
                'cancellation_reason': reason
            }
            
            result = self.db.table('bookings').update(update_data).eq('id', booking_id).execute()
            
            if result.data:
                # Refund session to client if applicable
                if booking.data['status'] == 'scheduled':
                    self.refund_session_to_client(booking.data['client_id'])
                
                log_info(f"Booking {booking_id} cancelled")
                return {'success': True, 'message': 'Booking cancelled successfully'}
            
        except Exception as e:
            log_error(f"Error cancelling booking: {str(e)}")
            return {'success': False, 'error': 'Failed to cancel booking'}
    
    def reschedule_booking(self, booking_id: str, new_datetime: datetime) -> Dict:
        """Reschedule a booking to a new time"""
        try:
            # Get current booking
            current = self.db.table('bookings').select('*').eq('id', booking_id).single().execute()
            
            if not current.data:
                return {'success': False, 'error': 'Booking not found'}
            
            booking = current.data
            
            # Check if new slot is available
            if not self.is_slot_available(booking['trainer_id'], new_datetime, 
                                        booking['duration_minutes']):
                return {
                    'success': False,
                    'error': 'New time slot is not available',
                    'alternatives': self.get_alternative_slots(booking['trainer_id'], new_datetime)
                }
            
            # Update booking
            new_end_time = new_datetime + timedelta(minutes=booking['duration_minutes'])
            update_data = {
                'session_datetime': new_datetime.isoformat(),
                'end_datetime': new_end_time.isoformat(),
                'rescheduled_at': datetime.now(self.sa_tz).isoformat(),
                'rescheduled_from': booking['session_datetime']
            }
            
            result = self.db.table('bookings').update(update_data).eq('id', booking_id).execute()
            
            if result.data:
                log_info(f"Booking {booking_id} rescheduled to {new_datetime}")
                return {'success': True, 'message': 'Booking rescheduled successfully'}
                
        except Exception as e:
            log_error(f"Error rescheduling booking: {str(e)}")
            return {'success': False, 'error': 'Failed to reschedule booking'}
    
    def get_trainer_schedule(self, trainer_id: str, start_date: datetime, 
                           end_date: datetime) -> List[Dict]:
        """Get trainer's schedule for a date range"""
        try:
            bookings = self.db.table('bookings').select(
                '*, clients(name, whatsapp)'
            ).eq(
                'trainer_id', trainer_id
            ).gte(
                'session_datetime', start_date.isoformat()
            ).lte(
                'session_datetime', end_date.isoformat()
            ).eq(
                'status', 'scheduled'
            ).order('session_datetime').execute()
            
            return bookings.data
            
        except Exception as e:
            log_error(f"Error getting trainer schedule: {str(e)}")
            return []
    
    def get_client_bookings(self, client_id: str, include_past: bool = False) -> List[Dict]:
        """Get client's bookings"""
        try:
            query = self.db.table('bookings').select(
                '*, trainers(name, whatsapp)'
            ).eq('client_id', client_id)
            
            if not include_past:
                query = query.gte('session_datetime', datetime.now(self.sa_tz).isoformat())
            
            bookings = query.order('session_datetime').execute()
            return bookings.data
            
        except Exception as e:
            log_error(f"Error getting client bookings: {str(e)}")
            return []
    
    def update_client_after_booking(self, client_id: str):
        """Update client's session count and last session date"""
        try:
            # Decrement sessions remaining
            client = self.db.table('clients').select('sessions_remaining').eq('id', client_id).single().execute()
            
            if client.data and client.data['sessions_remaining'] > 0:
                self.db.table('clients').update({
                    'sessions_remaining': client.data['sessions_remaining'] - 1,
                    'last_session_date': datetime.now(self.sa_tz).isoformat()
                }).eq('id', client_id).execute()
                
        except Exception as e:
            log_error(f"Error updating client after booking: {str(e)}")
    
    def refund_session_to_client(self, client_id: str):
        """Refund a session to client (for cancellations)"""
        try:
            client = self.db.table('clients').select('sessions_remaining').eq('id', client_id).single().execute()
            
            if client.data:
                self.db.table('clients').update({
                    'sessions_remaining': client.data['sessions_remaining'] + 1
                }).eq('id', client_id).execute()
                
        except Exception as e:
            log_error(f"Error refunding session: {str(e)}")

# Create an alias for backward compatibility
Booking = BookingModel
```

## SUMMARY

Fixed the ImportError by adding class aliases at the bottom of each model file. The app.py expects to import `Trainer`, `Client`, and `Booking` classes, but the actual class names are `TrainerModel`, `ClientModel`, and `BookingModel`. I've added aliases (`Trainer = TrainerModel`, etc.) to maintain backward compatibility without changing all the import statements throughout the codebase.