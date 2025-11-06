"""
Habit Reminder Service
Handles daily habit reminders for trainees
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, time, timedelta
from utils.logger import log_info, log_error
import pytz


class HabitReminderService:
    """Service for managing habit reminders"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
    
    def send_daily_reminders(self) -> Dict:
        """Send daily habit reminders to all eligible trainees"""
        try:
            today = date.today()
            current_time = datetime.now().time()
            
            log_info(f"Starting daily habit reminders for {today}")
            
            # Get all clients with active habit assignments
            clients = self._get_clients_for_reminders(today)
            
            if not clients:
                log_info("No clients found for reminders")
                return {
                    'success': True,
                    'total_clients': 0,
                    'reminders_sent': 0,
                    'reminders_skipped': 0,
                    'errors': 0
                }
            
            results = {
                'success': True,
                'total_clients': len(clients),
                'reminders_sent': 0,
                'reminders_skipped': 0,
                'errors': 0,
                'details': []
            }
            
            for client in clients:
                try:
                    client_id = client['client_id']
                    
                    # Check if reminder already sent today
                    if self._is_reminder_already_sent(client_id, today):
                        results['reminders_skipped'] += 1
                        results['details'].append({
                            'client_id': client_id,
                            'status': 'skipped',
                            'reason': 'Already sent today'
                        })
                        continue
                    
                    # Get client's reminder preferences
                    preferences = self._get_reminder_preferences(client_id)
                    
                    # Check if reminders are enabled for this client
                    if not preferences.get('reminder_enabled', True):
                        results['reminders_skipped'] += 1
                        results['details'].append({
                            'client_id': client_id,
                            'status': 'skipped',
                            'reason': 'Reminders disabled'
                        })
                        continue
                    
                    # Check if today is a reminder day for this client
                    if not self._is_reminder_day(preferences):
                        results['reminders_skipped'] += 1
                        results['details'].append({
                            'client_id': client_id,
                            'status': 'skipped',
                            'reason': 'Not a reminder day'
                        })
                        continue
                    
                    # Send reminder
                    reminder_result = self._send_habit_reminder(client, preferences, today)
                    
                    if reminder_result['success']:
                        results['reminders_sent'] += 1
                        results['details'].append({
                            'client_id': client_id,
                            'status': 'sent',
                            'message': reminder_result.get('message', '')
                        })
                    else:
                        results['errors'] += 1
                        results['details'].append({
                            'client_id': client_id,
                            'status': 'error',
                            'reason': reminder_result.get('error', 'Unknown error')
                        })
                
                except Exception as e:
                    log_error(f"Error sending reminder to client {client.get('client_id', 'unknown')}: {str(e)}")
                    results['errors'] += 1
                    results['details'].append({
                        'client_id': client.get('client_id', 'unknown'),
                        'status': 'error',
                        'reason': str(e)
                    })
            
            log_info(f"Daily reminders completed: {results['reminders_sent']} sent, {results['reminders_skipped']} skipped, {results['errors']} errors")
            
            return results
            
        except Exception as e:
            log_error(f"Error in send_daily_reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_clients': 0,
                'reminders_sent': 0,
                'reminders_skipped': 0,
                'errors': 0
            }
    
    def _get_clients_for_reminders(self, reminder_date: date) -> List[Dict]:
        """Get all clients who should receive reminders"""
        try:
            # Get all clients with active habit assignments
            result = self.db.table('trainee_habit_assignments').select(
                'client_id, clients(name, phone)'
            ).eq('is_active', True).execute()
            
            if not result.data:
                return []
            
            # Group by client_id to avoid duplicates
            clients_dict = {}
            for assignment in result.data:
                client_id = assignment['client_id']
                client_info = assignment.get('clients')
                
                if client_info and client_id not in clients_dict:
                    clients_dict[client_id] = {
                        'client_id': client_id,
                        'name': client_info.get('name', 'Unknown'),
                        'phone': client_info.get('phone', '')
                    }
            
            return list(clients_dict.values())
            
        except Exception as e:
            log_error(f"Error getting clients for reminders: {str(e)}")
            return []
    
    def _is_reminder_already_sent(self, client_id: str, reminder_date: date) -> bool:
        """Check if reminder was already sent to client today"""
        try:
            result = self.db.table('habit_reminders').select('id').eq(
                'client_id', client_id
            ).eq('reminder_date', reminder_date.isoformat()).eq('status', 'sent').execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            log_error(f"Error checking if reminder already sent: {str(e)}")
            return False
    
    def _get_reminder_preferences(self, client_id: str) -> Dict:
        """Get reminder preferences for client"""
        try:
            result = self.db.table('habit_reminder_preferences').select('*').eq(
                'client_id', client_id
            ).execute()
            
            if result.data:
                return result.data[0]
            else:
                # Return default preferences
                return {
                    'reminder_enabled': True,
                    'reminder_time': '09:00:00',
                    'timezone': 'UTC',
                    'reminder_days': [1, 2, 3, 4, 5, 6, 7],  # All days
                    'include_progress': True,
                    'include_encouragement': True
                }
                
        except Exception as e:
            log_error(f"Error getting reminder preferences: {str(e)}")
            return {
                'reminder_enabled': True,
                'reminder_time': '09:00:00',
                'timezone': 'UTC',
                'reminder_days': [1, 2, 3, 4, 5, 6, 7],
                'include_progress': True,
                'include_encouragement': True
            }
    
    def _is_reminder_day(self, preferences: Dict) -> bool:
        """Check if today is a reminder day based on preferences"""
        try:
            today_weekday = datetime.now().isoweekday()  # 1=Monday, 7=Sunday
            reminder_days = preferences.get('reminder_days', [1, 2, 3, 4, 5, 6, 7])
            
            return today_weekday in reminder_days
            
        except Exception as e:
            log_error(f"Error checking reminder day: {str(e)}")
            return True  # Default to sending reminder
    
    def _send_habit_reminder(self, client: Dict, preferences: Dict, reminder_date: date) -> Dict:
        """Send habit reminder to specific client"""
        try:
            client_id = client['client_id']
            client_name = client['name']
            phone = client['phone']
            
            if not phone:
                return {'success': False, 'error': 'No phone number'}
            
            # Get client's habit progress for today
            progress_data = self._calculate_daily_progress(client_id, reminder_date)
            
            # Create reminder record
            reminder_record = {
                'client_id': client_id,
                'reminder_date': reminder_date.isoformat(),
                'reminder_time': preferences.get('reminder_time', '09:00:00'),
                'total_habits': progress_data['total_habits'],
                'completed_habits': progress_data['completed_habits'],
                'remaining_habits': progress_data['remaining_habits'],
                'reminder_type': 'daily',
                'status': 'pending'
            }
            
            # Generate reminder message
            message = self._generate_reminder_message(
                client_name, progress_data, preferences
            )
            
            # Send WhatsApp message
            whatsapp_result = self.whatsapp.send_message(phone, message)
            
            if whatsapp_result.get('success', False):
                # Update reminder record as sent
                reminder_record.update({
                    'status': 'sent',
                    'sent_at': datetime.now().isoformat(),
                    'message_sent': message
                })
                
                # Insert reminder record
                self.db.table('habit_reminders').insert(reminder_record).execute()
                
                log_info(f"Habit reminder sent to {client_id} ({client_name})")
                
                return {
                    'success': True,
                    'message': message,
                    'progress': progress_data
                }
            else:
                # Update reminder record as failed
                reminder_record.update({
                    'status': 'failed',
                    'message_sent': message
                })
                
                # Insert reminder record
                self.db.table('habit_reminders').insert(reminder_record).execute()
                
                return {
                    'success': False,
                    'error': 'Failed to send WhatsApp message'
                }
                
        except Exception as e:
            log_error(f"Error sending habit reminder: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_daily_progress(self, client_id: str, target_date: date) -> Dict:
        """Calculate client's habit progress for specific date"""
        try:
            # Get all active habit assignments for client
            assignments_result = self.db.table('trainee_habit_assignments').select(
                'habit_id, fitness_habits(habit_name, target_value, unit)'
            ).eq('client_id', client_id).eq('is_active', True).execute()
            
            if not assignments_result.data:
                return {
                    'total_habits': 0,
                    'completed_habits': 0,
                    'remaining_habits': 0,
                    'habits_detail': []
                }
            
            total_habits = len(assignments_result.data)
            completed_habits = 0
            habits_detail = []
            
            for assignment in assignments_result.data:
                habit_id = assignment['habit_id']
                habit_info = assignment.get('fitness_habits', {})
                
                if not habit_info:
                    continue
                
                habit_name = habit_info.get('habit_name', 'Unknown')
                target_value = float(habit_info.get('target_value', 0))
                unit = habit_info.get('unit', '')
                
                # Get logs for this habit on target date
                logs_result = self.db.table('habit_logs').select('completed_value').eq(
                    'habit_id', habit_id
                ).eq('client_id', client_id).eq('log_date', target_date.isoformat()).execute()
                
                completed_value = sum(
                    float(log['completed_value']) for log in logs_result.data
                ) if logs_result.data else 0
                
                is_completed = completed_value >= target_value
                if is_completed:
                    completed_habits += 1
                
                habits_detail.append({
                    'habit_name': habit_name,
                    'target_value': target_value,
                    'completed_value': completed_value,
                    'unit': unit,
                    'is_completed': is_completed,
                    'remaining': max(0, target_value - completed_value)
                })
            
            return {
                'total_habits': total_habits,
                'completed_habits': completed_habits,
                'remaining_habits': total_habits - completed_habits,
                'habits_detail': habits_detail
            }
            
        except Exception as e:
            log_error(f"Error calculating daily progress: {str(e)}")
            return {
                'total_habits': 0,
                'completed_habits': 0,
                'remaining_habits': 0,
                'habits_detail': []
            }
    
    def _generate_reminder_message(self, client_name: str, progress_data: Dict, preferences: Dict) -> str:
        """Generate personalized reminder message"""
        try:
            total_habits = progress_data['total_habits']
            completed_habits = progress_data['completed_habits']
            remaining_habits = progress_data['remaining_habits']
            habits_detail = progress_data['habits_detail']
            
            if total_habits == 0:
                return f"Hi {client_name}! 👋\n\nYou don't have any habits assigned yet. Contact your trainer to get started with your fitness journey! 💪"
            
            # Start with greeting
            message = f"🌅 *Good morning, {client_name}!*\n\n"
            
            # Add progress summary if enabled
            if preferences.get('include_progress', True):
                if completed_habits == 0:
                    message += f"📋 You have *{total_habits}* habits to complete today.\n\n"
                elif completed_habits == total_habits:
                    message += f"🎉 *Amazing!* You've completed all {total_habits} habits today!\n\n"
                else:
                    message += f"📊 *Progress Update:*\n"
                    message += f"✅ Completed: {completed_habits}/{total_habits} habits\n"
                    message += f"⏳ Remaining: {remaining_habits} habits\n\n"
            
            # Add remaining habits details
            if remaining_habits > 0:
                message += f"🎯 *Habits to complete today:*\n\n"
                
                for i, habit in enumerate(habits_detail, 1):
                    if not habit['is_completed']:
                        remaining = habit['remaining']
                        unit = habit['unit']
                        message += f"{i}. *{habit['habit_name']}*\n"
                        message += f"   Target: {remaining} {unit} remaining\n\n"
            
            # Add encouragement if enabled
            if preferences.get('include_encouragement', True):
                if completed_habits == total_habits:
                    encouragements = [
                        "🏆 You're crushing your goals! Keep up the excellent work!",
                        "💪 Outstanding dedication! You're an inspiration!",
                        "🌟 Perfect day! Your consistency is paying off!",
                        "🔥 You're on fire! This is how champions are made!"
                    ]
                elif completed_habits > 0:
                    encouragements = [
                        "💪 Great start! You're building amazing habits!",
                        "🌟 Keep the momentum going! You've got this!",
                        "🔥 Every step counts! You're doing fantastic!",
                        "💯 Progress is progress! Stay consistent!"
                    ]
                else:
                    encouragements = [
                        "🌅 A new day, a fresh start! You can do this!",
                        "💪 Every journey begins with a single step!",
                        "🎯 Focus on one habit at a time. You've got this!",
                        "🌟 Believe in yourself! Today is your day!"
                    ]
                
                import random
                message += random.choice(encouragements) + "\n\n"
            
            # Add action prompt
            message += "📱 *Ready to log your progress?*\n"
            message += "Type /log-habits to get started!\n\n"
            message += "💡 *Tip:* Use /view-progress to see your detailed progress anytime."
            
            return message
            
        except Exception as e:
            log_error(f"Error generating reminder message: {str(e)}")
            return f"Hi {client_name}! 👋\n\nTime for your daily habit check-in! Type /log-habits to record your progress. 💪"
    
    def set_reminder_preferences(self, client_id: str, preferences: Dict) -> Tuple[bool, str]:
        """Set reminder preferences for a client"""
        try:
            # Validate preferences
            valid_preferences = {
                'client_id': client_id,
                'reminder_enabled': preferences.get('reminder_enabled', True),
                'reminder_time': preferences.get('reminder_time', '09:00:00'),
                'timezone': preferences.get('timezone', 'UTC'),
                'reminder_days': preferences.get('reminder_days', [1, 2, 3, 4, 5, 6, 7]),
                'include_progress': preferences.get('include_progress', True),
                'include_encouragement': preferences.get('include_encouragement', True),
                'last_updated': datetime.now().isoformat()
            }
            
            # Upsert preferences
            result = self.db.table('habit_reminder_preferences').upsert(
                valid_preferences, on_conflict='client_id'
            ).execute()
            
            if result.data:
                log_info(f"Reminder preferences updated for client {client_id}")
                return True, "Reminder preferences updated successfully"
            else:
                return False, "Failed to update reminder preferences"
                
        except Exception as e:
            log_error(f"Error setting reminder preferences: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def get_reminder_stats(self, date_from: date = None, date_to: date = None) -> Dict:
        """Get reminder statistics for a date range"""
        try:
            if not date_from:
                date_from = date.today() - timedelta(days=7)
            if not date_to:
                date_to = date.today()
            
            # Get reminder statistics
            result = self.db.table('habit_reminders').select('*').gte(
                'reminder_date', date_from.isoformat()
            ).lte('reminder_date', date_to.isoformat()).execute()
            
            if not result.data:
                return {
                    'total_reminders': 0,
                    'sent_reminders': 0,
                    'failed_reminders': 0,
                    'success_rate': 0,
                    'date_range': f"{date_from} to {date_to}"
                }
            
            total_reminders = len(result.data)
            sent_reminders = len([r for r in result.data if r['status'] == 'sent'])
            failed_reminders = len([r for r in result.data if r['status'] == 'failed'])
            success_rate = (sent_reminders / total_reminders * 100) if total_reminders > 0 else 0
            
            return {
                'total_reminders': total_reminders,
                'sent_reminders': sent_reminders,
                'failed_reminders': failed_reminders,
                'success_rate': round(success_rate, 2),
                'date_range': f"{date_from} to {date_to}",
                'details': result.data
            }
            
        except Exception as e:
            log_error(f"Error getting reminder stats: {str(e)}")
            return {
                'total_reminders': 0,
                'sent_reminders': 0,
                'failed_reminders': 0,
                'success_rate': 0,
                'error': str(e)
            }