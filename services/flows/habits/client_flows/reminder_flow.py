"""
Client Habit Reminder Flow
Handles reminder preference configuration
"""
from typing import Dict
from datetime import datetime, time
from utils.logger import log_info, log_error


class ReminderFlow:
    """Handles reminder preference flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
    
    def continue_reminder_settings(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle reminder settings flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'show_current_settings')
            
            if step == 'show_current_settings':
                # User selected an option
                choice = message.strip()
                
                if choice == '1':
                    return self._handle_toggle_enabled(phone, client_id, task)
                elif choice == '2':
                    return self._handle_change_time(phone, client_id, task)
                elif choice == '3':
                    return self._handle_change_days(phone, client_id, task)
                elif choice == '4':
                    return self._handle_toggle_progress(phone, client_id, task)
                elif choice == '5':
                    return self._handle_toggle_encouragement(phone, client_id, task)
                elif choice == '6':
                    return self._handle_reset_defaults(phone, client_id, task)
                else:
                    msg = "❌ Invalid choice. Please select a number from 1-6."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'reminder_settings_invalid_choice'}
            
            elif step == 'ask_time':
                return self._process_time_change(phone, message, client_id, task)
            
            elif step == 'ask_days':
                return self._process_days_change(phone, message, client_id, task)
            
            return {'success': True, 'response': 'Processing...', 'handler': 'reminder_settings'}
            
        except Exception as e:
            log_error(f"Error in reminder settings flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error updating reminder settings', 'handler': 'reminder_settings_error'}
    
    def _handle_toggle_enabled(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle enabling/disabling reminders"""
        try:
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            # Get current preferences
            preferences = reminder_service._get_reminder_preferences(client_id)
            current_enabled = preferences.get('reminder_enabled', True)
            
            # Toggle the setting
            new_enabled = not current_enabled
            preferences['reminder_enabled'] = new_enabled
            
            # Update preferences
            success, msg = reminder_service.set_reminder_preferences(client_id, preferences)
            
            if success:
                status = "enabled" if new_enabled else "disabled"
                response_msg = f"✅ Reminders have been {status}!"
                
                if new_enabled:
                    response_msg += f"\n\nYou'll receive daily reminders at {preferences.get('reminder_time', '09:00:00')[:5]} UTC."
                else:
                    response_msg += "\n\nYou won't receive any automatic reminders. You can re-enable them anytime with /reminder-settings."
            else:
                response_msg = f"❌ Failed to update reminder settings: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_toggle_complete'
            }
            
        except Exception as e:
            log_error(f"Error toggling reminder enabled: {str(e)}")
            return {'success': False, 'response': 'Error updating setting', 'handler': 'reminder_settings_toggle_error'}
    
    def _handle_change_time(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle changing reminder time"""
        try:
            msg = (
                f"🕘 *Change Reminder Time*\n\n"
                f"Enter your preferred reminder time in 24-hour format (HH:MM).\n\n"
                f"*Examples:*\n"
                f"• 09:00 for 9:00 AM\n"
                f"• 18:30 for 6:30 PM\n"
                f"• 07:15 for 7:15 AM\n\n"
                f"⚠️ *Note:* Time is in UTC timezone.\n\n"
                f"Type /stop to cancel."
            )
            
            self.whatsapp.send_message(phone, msg)
            
            # Update task step
            task_data = task.get('task_data', {})
            task_data['step'] = 'ask_time'
            self.task_service.update_task(task['id'], task_data)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'reminder_settings_ask_time'
            }
            
        except Exception as e:
            log_error(f"Error handling change time: {str(e)}")
            return {'success': False, 'response': 'Error changing time', 'handler': 'reminder_settings_time_error'}
    
    def _process_time_change(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Process time change input"""
        try:
            time_input = message.strip()
            
            # Validate time format
            try:
                time_obj = datetime.strptime(time_input, '%H:%M').time()
                time_str = time_obj.strftime('%H:%M:%S')
            except ValueError:
                msg = "❌ Invalid time format. Please use HH:MM format (e.g., 09:00)."
                self.whatsapp.send_message(phone, msg)
                return {'success': True, 'response': msg, 'handler': 'reminder_settings_invalid_time'}
            
            # Update preferences
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            preferences = reminder_service._get_reminder_preferences(client_id)
            preferences['reminder_time'] = time_str
            
            success, msg = reminder_service.set_reminder_preferences(client_id, preferences)
            
            if success:
                response_msg = f"✅ Reminder time updated to {time_input} UTC!"
            else:
                response_msg = f"❌ Failed to update reminder time: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_time_complete'
            }
            
        except Exception as e:
            log_error(f"Error processing time change: {str(e)}")
            return {'success': False, 'response': 'Error updating time', 'handler': 'reminder_settings_time_process_error'}
    
    def _handle_change_days(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle changing reminder days"""
        try:
            msg = (
                f"📅 *Change Reminder Days*\n\n"
                f"Select which days you want to receive reminders.\n\n"
                f"*Options:*\n"
                f"• Type 'all' for all days (Mon-Sun)\n"
                f"• Type 'weekdays' for weekdays only (Mon-Fri)\n"
                f"• Type 'weekends' for weekends only (Sat-Sun)\n"
                f"• Type day numbers: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun\n\n"
                f"*Examples:*\n"
                f"• '1,2,3,4,5' for weekdays\n"
                f"• '1,3,5' for Mon, Wed, Fri\n"
                f"• '6,7' for weekends\n\n"
                f"Type /stop to cancel."
            )
            
            self.whatsapp.send_message(phone, msg)
            
            # Update task step
            task_data = task.get('task_data', {})
            task_data['step'] = 'ask_days'
            self.task_service.update_task(task['id'], task_data)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'reminder_settings_ask_days'
            }
            
        except Exception as e:
            log_error(f"Error handling change days: {str(e)}")
            return {'success': False, 'response': 'Error changing days', 'handler': 'reminder_settings_days_error'}
    
    def _process_days_change(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Process days change input"""
        try:
            days_input = message.strip().lower()
            
            # Parse days input
            if days_input == 'all':
                reminder_days = [1, 2, 3, 4, 5, 6, 7]
            elif days_input == 'weekdays':
                reminder_days = [1, 2, 3, 4, 5]
            elif days_input == 'weekends':
                reminder_days = [6, 7]
            else:
                # Parse comma-separated numbers
                try:
                    day_numbers = [int(d.strip()) for d in days_input.split(',')]
                    reminder_days = [d for d in day_numbers if 1 <= d <= 7]
                    
                    if not reminder_days:
                        raise ValueError("No valid days")
                        
                except ValueError:
                    msg = "❌ Invalid format. Please use 'all', 'weekdays', 'weekends', or day numbers (1-7)."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'reminder_settings_invalid_days'}
            
            # Update preferences
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            preferences = reminder_service._get_reminder_preferences(client_id)
            preferences['reminder_days'] = reminder_days
            
            success, msg = reminder_service.set_reminder_preferences(client_id, preferences)
            
            if success:
                # Convert day numbers to names for display
                day_names = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
                selected_days = [day_names[day] for day in reminder_days]
                response_msg = f"✅ Reminder days updated to: {', '.join(selected_days)}"
            else:
                response_msg = f"❌ Failed to update reminder days: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_days_complete'
            }
            
        except Exception as e:
            log_error(f"Error processing days change: {str(e)}")
            return {'success': False, 'response': 'Error updating days', 'handler': 'reminder_settings_days_process_error'}
    
    def _handle_toggle_progress(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle toggling progress info in reminders"""
        try:
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            preferences = reminder_service._get_reminder_preferences(client_id)
            current_progress = preferences.get('include_progress', True)
            
            # Toggle the setting
            new_progress = not current_progress
            preferences['include_progress'] = new_progress
            
            success, msg = reminder_service.set_reminder_preferences(client_id, preferences)
            
            if success:
                status = "included" if new_progress else "excluded"
                response_msg = f"✅ Progress information will be {status} in your reminders."
            else:
                response_msg = f"❌ Failed to update setting: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_progress_complete'
            }
            
        except Exception as e:
            log_error(f"Error toggling progress: {str(e)}")
            return {'success': False, 'response': 'Error updating setting', 'handler': 'reminder_settings_progress_error'}
    
    def _handle_toggle_encouragement(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle toggling encouragement in reminders"""
        try:
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            preferences = reminder_service._get_reminder_preferences(client_id)
            current_encouragement = preferences.get('include_encouragement', True)
            
            # Toggle the setting
            new_encouragement = not current_encouragement
            preferences['include_encouragement'] = new_encouragement
            
            success, msg = reminder_service.set_reminder_preferences(client_id, preferences)
            
            if success:
                status = "included" if new_encouragement else "excluded"
                response_msg = f"✅ Encouragement messages will be {status} in your reminders."
            else:
                response_msg = f"❌ Failed to update setting: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_encouragement_complete'
            }
            
        except Exception as e:
            log_error(f"Error toggling encouragement: {str(e)}")
            return {'success': False, 'response': 'Error updating setting', 'handler': 'reminder_settings_encouragement_error'}
    
    def _handle_reset_defaults(self, phone: str, client_id: str, task: Dict) -> Dict:
        """Handle resetting to default preferences"""
        try:
            from services.habits.reminder_service import HabitReminderService
            reminder_service = HabitReminderService(self.db, self.whatsapp)
            
            # Set default preferences
            default_preferences = {
                'reminder_enabled': True,
                'reminder_time': '09:00:00',
                'timezone': 'UTC',
                'reminder_days': [1, 2, 3, 4, 5, 6, 7],
                'include_progress': True,
                'include_encouragement': True
            }
            
            success, msg = reminder_service.set_reminder_preferences(client_id, default_preferences)
            
            if success:
                response_msg = (
                    f"✅ Reminder settings reset to defaults!\n\n"
                    f"*Default Settings:*\n"
                    f"📱 Enabled: Yes\n"
                    f"🕘 Time: 09:00 UTC\n"
                    f"📅 Days: All days (Mon-Sun)\n"
                    f"📊 Progress Info: Included\n"
                    f"💪 Encouragement: Included"
                )
            else:
                response_msg = f"❌ Failed to reset settings: {msg}"
            
            self.whatsapp.send_message(phone, response_msg)
            self.task_service.complete_task(task['id'], 'client')
            
            return {
                'success': success,
                'response': response_msg,
                'handler': 'reminder_settings_reset_complete'
            }
            
        except Exception as e:
            log_error(f"Error resetting defaults: {str(e)}")
            return {'success': False, 'response': 'Error resetting settings', 'handler': 'reminder_settings_reset_error'}