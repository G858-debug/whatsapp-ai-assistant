<!-- Model: Opus 4.1 -->
<!-- Cost: $1.2821 -->
<!-- Tokens: ~85,476 -->

## ANALYSIS
The error shows that `BookingModel` cannot be imported from `models/booking.py`. Looking at the file, it's completely empty except for comments. The `BookingModel` class is missing entirely. I need to create the complete BookingModel class with all necessary methods for handling bookings.

## FILES TO CHANGE

### FILE: models/booking.py
```python
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class BookingModel:
    """Handle all booking-related database operations"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_booking(self, trainer_id: str, client_id: str, booking_data: Dict) -> Dict:
        """Create a new booking"""
        try:
            # Validate required fields
            required_fields = ['session_date', 'session_time']
            for field in required_fields:
                if field not in booking_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Prepare booking record
            booking = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'session_date': booking_data['session_date'],
                'session_time': booking_data['session_time'],
                'session_type': booking_data.get('session_type', 'one_on_one'),
                'status': 'confirmed',
                'notes': booking_data.get('notes', ''),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Check for conflicts
            conflict = self.check_booking_conflict(
                trainer_id,
                booking_data['session_date'],
                booking_data['session_time']
            )
            
            if conflict:
                return {
                    'success': False,
                    'error': 'Time slot already booked'
                }
            
            # Insert booking
            result = self.db.table('bookings').insert(booking).execute()
            
            if result.data:
                log_info(f"Booking created for client {client_id}")
                return {
                    'success': True,
                    'booking_id': result.data[0]['id'],
                    'booking': result.data[0]
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create booking'
                }
                
        except Exception as e:
            log_error(f"Error creating booking: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_booking_by_id(self, booking_id: str) -> Optional[Dict]:
        """Get booking by ID"""
        try:
            result = self.db.table('bookings').select(
                '*, clients(name, whatsapp), trainers(name, business_name)'
            ).eq('id', booking_id).single().execute()
            
            return result.data
            
        except Exception as e:
            log_error(f"Error getting booking: {str(e)}")
            return None
    
    def get_client_bookings(self, client_id: str, status: str = None) -> List[Dict]:
        """Get all bookings for a client"""
        try:
            query = self.db.table('bookings').select(
                '*, trainers(name, business_name)'
            ).eq('client_id', client_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('session_date', desc=False).order(
                'session_time', desc=False
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting client bookings: {str(e)}")
            return []
    
    def get_trainer_bookings(self, trainer_id: str, date_from: str = None, 
                            date_to: str = None) -> List[Dict]:
        """Get bookings for a trainer within date range"""
        try:
            query = self.db.table('bookings').select(
                '*, clients(name, whatsapp)'
            ).eq('trainer_id', trainer_id)
            
            if date_from:
                query = query.gte('session_date', date_from)
            if date_to:
                query = query.lte('session_date', date_to)
            
            result = query.order('session_date', desc=False).order(
                'session_time', desc=False
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting trainer bookings: {str(e)}")
            return []
    
    def update_booking_status(self, booking_id: str, new_status: str) -> Dict:
        """Update booking status"""
        try:
            valid_statuses = ['confirmed', 'completed', 'cancelled', 'no_show', 'rescheduled']
            
            if new_status not in valid_statuses:
                return {
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }
            
            result = self.db.table('bookings').update({
                'status': new_status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', booking_id).execute()
            
            if result.data:
                log_info(f"Booking {booking_id} status updated to {new_status}")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Booking not found'}
                
        except Exception as e:
            log_error(f"Error updating booking status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cancel_booking(self, booking_id: str, reason: str = None) -> Dict:
        """Cancel a booking"""
        try:
            update_data = {
                'status': 'cancelled',
                'cancelled_at': datetime.now(self.sa_tz).isoformat(),
                'cancellation_reason': reason,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('bookings').update(
                update_data
            ).eq('id', booking_id).execute()
            
            if result.data:
                log_info(f"Booking {booking_id} cancelled")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Booking not found'}
                
        except Exception as e:
            log_error(f"Error cancelling booking: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reschedule_booking(self, booking_id: str, new_date: str, 
                          new_time: str) -> Dict:
        """Reschedule a booking"""
        try:
            # Get current booking
            booking = self.get_booking_by_id(booking_id)
            if not booking:
                return {'success': False, 'error': 'Booking not found'}
            
            # Check for conflicts at new time
            conflict = self.check_booking_conflict(
                booking['trainer_id'],
                new_date,
                new_time,
                exclude_booking_id=booking_id
            )
            
            if conflict:
                return {
                    'success': False,
                    'error': 'New time slot already booked'
                }
            
            # Update booking
            result = self.db.table('bookings').update({
                'session_date': new_date,
                'session_time': new_time,
                'status': 'rescheduled',
                'rescheduled_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', booking_id).execute()
            
            if result.data:
                log_info(f"Booking {booking_id} rescheduled to {new_date} {new_time}")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Failed to reschedule'}
                
        except Exception as e:
            log_error(f"Error rescheduling booking: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_booking_conflict(self, trainer_id: str, date: str, time: str,
                              exclude_booking_id: str = None) -> bool:
        """Check if there's a booking conflict"""
        try:
            query = self.db.table('bookings').select('id').eq(
                'trainer_id', trainer_id
            ).eq('session_date', date).eq('session_time', time).in_(
                'status', ['confirmed', 'rescheduled']
            )
            
            if exclude_booking_id:
                query = query.neq('id', exclude_booking_id)
            
            result = query.execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            log_error(f"Error checking booking conflict: {str(e)}")
            return True  # Assume conflict on error to be safe
    
    def get_available_slots(self, trainer_id: str, date: str) -> List[str]:
        """Get available time slots for a trainer on a specific date"""
        try:
            # Get trainer's working hours (could be from config or database)
            all_slots = self.config.get_booking_slots()
            
            # Get day of week
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A').lower()
            
            if day_name not in all_slots:
                return []
            
            available_slots = all_slots[day_name].copy()
            
            # Get existing bookings for that date
            bookings = self.db.table('bookings').select(
                'session_time'
            ).eq('trainer_id', trainer_id).eq(
                'session_date', date
            ).in_('status', ['confirmed', 'rescheduled']).execute()
            
            # Remove booked slots
            if bookings.data:
                booked_times = [b['session_time'] for b in bookings.data]
                available_slots = [
                    slot for slot in available_slots 
                    if slot not in booked_times
                ]
            
            return available_slots
            
        except Exception as e:
            log_error(f"Error getting available slots: {str(e)}")
            return []
    
    def get_upcoming_bookings(self, trainer_id: str, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming bookings for a trainer"""
        try:
            today = datetime.now(self.sa_tz).date()
            end_date = today + timedelta(days=days_ahead)
            
            result = self.db.table('bookings').select(
                '*, clients(name, whatsapp)'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'confirmed'
            ).gte('session_date', today.isoformat()).lte(
                'session_date', end_date.isoformat()
            ).order('session_date', desc=False).order(
                'session_time', desc=False
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting upcoming bookings: {str(e)}")
            return []
    
    def mark_as_completed(self, booking_id: str, notes: str = None) -> Dict:
        """Mark a booking as completed"""
        try:
            update_data = {
                'status': 'completed',
                'completed_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if notes:
                update_data['completion_notes'] = notes
            
            result = self.db.table('bookings').update(
                update_data
            ).eq('id', booking_id).execute()
            
            if result.data:
                # Deduct session from client's balance if applicable
                booking = result.data[0]
                if booking.get('client_id'):
                    self._deduct_client_session(booking['client_id'])
                
                log_info(f"Booking {booking_id} marked as completed")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Booking not found'}
                
        except Exception as e:
            log_error(f"Error marking booking as completed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _deduct_client_session(self, client_id: str):
        """Deduct one session from client's balance"""
        try:
            # Get current balance
            client = self.db.table('clients').select(
                'sessions_remaining'
            ).eq('id', client_id).single().execute()
            
            if client.data and client.data.get('sessions_remaining', 0) > 0:
                new_balance = client.data['sessions_remaining'] - 1
                
                self.db.table('clients').update({
                    'sessions_remaining': new_balance,
                    'last_session_date': datetime.now(self.sa_tz).date().isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', client_id).execute()
                
                log_info(f"Deducted session for client {client_id}. New balance: {new_balance}")
                
        except Exception as e:
            log_error(f"Error deducting client session: {str(e)}")
    
    def get_booking_stats(self, trainer_id: str, period_days: int = 30) -> Dict:
        """Get booking statistics for a trainer"""
        try:
            start_date = (datetime.now(self.sa_tz) - timedelta(days=period_days)).date()
            
            bookings = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).gte('session_date', start_date.isoformat()).execute()
            
            if not bookings.data:
                return {
                    'total': 0,
                    'completed': 0,
                    'cancelled': 0,
                    'no_show': 0,
                    'completion_rate': 0
                }
            
            stats = {
                'total': len(bookings.data),
                'completed': sum(1 for b in bookings.data if b['status'] == 'completed'),
                'cancelled': sum(1 for b in bookings.data if b['status'] == 'cancelled'),
                'no_show': sum(1 for b in bookings.data if b['status'] == 'no_show'),
            }
            
            stats['completion_rate'] = (
                (stats['completed'] / stats['total'] * 100) 
                if stats['total'] > 0 else 0
            )
            
            return stats
            
        except Exception as e:
            log_error(f"Error getting booking stats: {str(e)}")
            return {}
```

## SUMMARY
Created the complete `BookingModel` class with all necessary methods for handling bookings including:
- Creating, updating, and cancelling bookings
- Checking for booking conflicts
- Managing available time slots
- Handling rescheduling
- Tracking booking statistics
- Integration with client session balances
- Proper error handling and logging

The class follows the existing pattern used in other models (TrainerModel, ClientModel) and includes all required functionality for the booking system.