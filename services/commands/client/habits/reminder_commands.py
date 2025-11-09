"""
Client Habit Reminder Commands
Handles reminder preference management
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_reminder_settings(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /reminder-settings command"""
    try:
        # Create reminder_settings task - use phone for task identification
        task_id = task_service.create_task(
            phone=phone,
            role='client',
            task_type='reminder_settings',
            task_data={
                'step': 'show_current_settings',
                'client_id': client_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the reminder settings. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'reminder_settings_task_error'}
        
        # Get current reminder preferences
        from services.habits.reminder_service import HabitReminderService
        reminder_service = HabitReminderService(db, whatsapp)
        
        preferences = reminder_service._get_reminder_preferences(client_id)
        
        # Format current settings
        enabled_status = "✅ Enabled" if preferences.get('reminder_enabled', True) else "❌ Disabled"
        reminder_time = preferences.get('reminder_time', '09:00:00')
        reminder_days = preferences.get('reminder_days', [1, 2, 3, 4, 5, 6, 7])
        
        # Convert day numbers to names
        day_names = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 7: 'Sun'}
        active_days = [day_names[day] for day in reminder_days if day in day_names]
        
        msg = (
            f"⚙️ *Reminder Settings*\n\n"
            f"*Current Settings:*\n"
            f"📱 Status: {enabled_status}\n"
            f"🕘 Time: {reminder_time[:5]} UTC\n"
            f"📅 Days: {', '.join(active_days)}\n"
            f"📊 Include Progress: {'✅' if preferences.get('include_progress', True) else '❌'}\n"
            f"💪 Include Encouragement: {'✅' if preferences.get('include_encouragement', True) else '❌'}\n\n"
            f"*What would you like to change?*\n\n"
            f"1️⃣ Enable/Disable reminders\n"
            f"2️⃣ Change reminder time\n"
            f"3️⃣ Change reminder days\n"
            f"4️⃣ Toggle progress info\n"
            f"5️⃣ Toggle encouragement\n"
            f"6️⃣ Reset to defaults\n\n"
            f"Type the number (1-6) or /stop to cancel."
        )
        
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'reminder_settings_started'
        }
        
    except Exception as e:
        log_error(f"Error in reminder settings command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'reminder_settings_error'
        }


def handle_test_reminder(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Handle /test-reminder command"""
    try:
        # Get client info
        client_result = db.table('clients').select('name, phone').eq('client_id', client_id).execute()
        
        if not client_result.data:
            msg = "❌ Client information not found."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'test_reminder_client_not_found'}
        
        client = {
            'client_id': client_id,
            'name': client_result.data[0]['name'],
            'phone': client_result.data[0]['phone']
        }
        
        # Send test reminder
        from services.habits.reminder_service import HabitReminderService
        from datetime import date
        
        reminder_service = HabitReminderService(db, whatsapp)
        preferences = reminder_service._get_reminder_preferences(client_id)
        
        # Send test reminder (don't log to database)
        today = date.today()
        progress_data = reminder_service._calculate_daily_progress(client_id, today)
        
        test_message = reminder_service._generate_reminder_message(
            client['name'], progress_data, preferences
        )
        
        # Add test header
        test_message = f"🧪 *TEST REMINDER*\n\n{test_message}\n\n---\n💡 This was a test reminder. Your actual reminders will be sent at your scheduled time."
        
        whatsapp.send_message(phone, test_message)
        
        log_info(f"Test reminder sent to client {client_id}")
        
        return {
            'success': True,
            'response': test_message,
            'handler': 'test_reminder_sent'
        }
        
    except Exception as e:
        log_error(f"Error in test reminder command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error sending the test reminder.",
            'handler': 'test_reminder_error'
        }