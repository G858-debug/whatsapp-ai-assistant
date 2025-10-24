"""
Client Habit Flow Handlers - Phase 3
Handles multi-step flows for client habit tracking
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.assignment_service import AssignmentService
from services.habits.logging_service import LoggingService
from services.habits.report_service import ReportService
import os
import tempfile


class ClientHabitFlows:
    """Handles client habit flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.assignment_service = AssignmentService(db)
        self.logging_service = LoggingService(db)
        self.report_service = ReportService(db)
    
    def continue_log_habits(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle log habits flow"""
        try:
            task_data = task.get('task_data', {})
            habits = task_data.get('habits', [])
            current_index = task_data.get('current_habit_index', 0)
            logged_values = task_data.get('logged_values', {})
            
            # Validate and store current value
            if current_index > 0:
                current_habit = habits[current_index - 1]
                habit_id = current_habit['habit_id']
                
                try:
                    value = float(message.strip())
                    
                    if value < 0:
                        msg = "❌ Value cannot be negative. Please enter a valid number."
                        self.whatsapp.send_message(phone, msg)
                        return {'success': True, 'response': msg, 'handler': 'log_habits_invalid'}
                    
                    # Log the habit
                    success, log_msg, log_data = self.logging_service.log_habit(
                        client_id, habit_id, value
                    )
                    
                    if not success:
                        error_msg = f"❌ Failed to log habit: {log_msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        return {'success': True, 'response': error_msg, 'handler': 'log_habits_failed'}
                    
                    logged_values[habit_id] = value
                    task_data['logged_values'] = logged_values
                    
                except ValueError:
                    msg = "❌ Please enter a valid number."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'log_habits_invalid'}
            
            # Check if all habits logged
            if current_index >= len(habits):
                # Calculate and show summary
                success, msg, progress_list = self.logging_service.calculate_daily_progress(client_id)
                
                if success and progress_list:
                    summary_msg = "✅ *All Habits Logged!*\n\n📊 *Today's Progress:*\n\n"
                    
                    for progress in progress_list:
                        summary_msg += f"*{progress['habit_name']}*\n"
                        summary_msg += f"   Completed: {progress['completed']}/{progress['target']} {progress['unit']}\n"
                        summary_msg += f"   Progress: {progress['percentage']}%\n"
                        
                        if progress['percentage'] >= 100:
                            summary_msg += "   🎉 Target achieved!\n"
                        elif progress['percentage'] >= 75:
                            summary_msg += "   💪 Almost there!\n"
                        elif progress['percentage'] >= 50:
                            summary_msg += "   👍 Good progress!\n"
                        
                        summary_msg += "\n"
                    
                    summary_msg += "💡 You can log again later if needed!"
                    
                    self.whatsapp.send_message(phone, summary_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': summary_msg, 'handler': 'log_habits_complete'}
                else:
                    simple_msg = "✅ All habits logged successfully!"
                    self.whatsapp.send_message(phone, simple_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': simple_msg, 'handler': 'log_habits_complete'}
            
            # Ask for next habit
            next_habit = habits[current_index]
            habit_msg = (
                f"*{current_index + 1}/{len(habits)}: {next_habit['habit_name']}*\n\n"
                f"Target: {next_habit['target_value']} {next_habit['unit']}\n\n"
                f"How much did you complete?\n"
                f"(Enter a number)"
            )
            self.whatsapp.send_message(phone, habit_msg)
            
            task_data['current_habit_index'] = current_index + 1
            self.task_service.update_task(task['id'], 'client', task_data)
            
            return {'success': True, 'response': habit_msg, 'handler': 'log_habits_continue'}
            
        except Exception as e:
            log_error(f"Error in log habits flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error logging habits', 'handler': 'log_habits_error'}
    
    def continue_view_progress(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle view progress flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_date')
            
            if step == 'ask_date':
                # Parse date
                date_input = message.strip().lower()
                
                try:
                    if date_input == 'today':
                        target_date = date.today()
                    elif date_input == 'yesterday':
                        target_date = date.today() - timedelta(days=1)
                    else:
                        target_date = datetime.strptime(message.strip(), '%Y-%m-%d').date()
                except ValueError:
                    msg = "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15) or type 'today'/'yesterday'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'view_progress_invalid_date'}
                
                # Get progress
                success, msg, progress_list = self.logging_service.calculate_daily_progress(
                    client_id, target_date
                )
                
                if not success:
                    error_msg = f"❌ Error calculating progress: {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'view_progress_error'}
                
                if not progress_list:
                    no_data_msg = (
                        f"📊 *No Progress Data*\n\n"
                        f"No habits logged for {target_date.strftime('%Y-%m-%d')}.\n\n"
                        f"Use /log-habits to log your progress!"
                    )
                    self.whatsapp.send_message(phone, no_data_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': True, 'response': no_data_msg, 'handler': 'view_progress_no_data'}
                
                # Format progress
                response_msg = f"📊 *Your Progress*\n\n"
                response_msg += f"*Date:* {target_date.strftime('%A, %B %d, %Y')}\n\n"
                
                for i, progress in enumerate(progress_list, 1):
                    response_msg += f"*{i}. {progress['habit_name']}*\n"
                    response_msg += f"   Target: {progress['target']} {progress['unit']}\n"
                    response_msg += f"   Completed: {progress['completed']} {progress['unit']}\n"
                    response_msg += f"   Due: {progress['due']} {progress['unit']}\n"
                    response_msg += f"   Progress: {progress['percentage']}%\n"
                    
                    if progress['log_count'] > 1:
                        response_msg += f"   Logged {progress['log_count']} times\n"
                    
                    if progress['percentage'] >= 100:
                        response_msg += "   ✅ Target achieved!\n"
                    elif progress['percentage'] >= 75:
                        response_msg += "   💪 Almost there!\n"
                    elif progress['percentage'] >= 50:
                        response_msg += "   👍 Good progress!\n"
                    elif progress['percentage'] > 0:
                        response_msg += "   📈 Keep going!\n"
                    else:
                        response_msg += "   ⏳ Not started yet\n"
                    
                    response_msg += "\n"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'client')
                return {'success': True, 'response': response_msg, 'handler': 'view_progress_success'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'view_progress'}
            
        except Exception as e:
            log_error(f"Error in view progress flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error viewing progress', 'handler': 'view_progress_error'}
    
    def continue_weekly_report(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle weekly report flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_week')
            
            if step == 'ask_week':
                # Parse week
                week_input = message.strip().lower()
                
                try:
                    if week_input == 'this week':
                        week_start = date.today() - timedelta(days=date.today().weekday())
                    elif week_input == 'last week':
                        week_start = date.today() - timedelta(days=date.today().weekday() + 7)
                    else:
                        week_start = datetime.strptime(message.strip(), '%Y-%m-%d').date()
                except ValueError:
                    msg = "❌ Invalid format. Please use YYYY-MM-DD (e.g., 2024-01-15) or type 'this week'/'last week'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'weekly_report_invalid_week'}
                
                # Generate report
                success, msg, csv_content = self.report_service.generate_weekly_report(
                    client_id, week_start
                )
                
                if not success or not csv_content:
                    error_msg = f"❌ {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'weekly_report_failed'}
                
                # Save and send CSV
                try:
                    from services.helpers.supabase_storage import SupabaseStorageHelper
                    
                    temp_dir = tempfile.gettempdir()
                    report_name = f"weekly_report_{client_id}_{week_start.strftime('%Y%m%d')}.csv"
                    filepath = os.path.join(temp_dir, report_name)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    storage_helper = SupabaseStorageHelper(self.db)
                    public_url = storage_helper.upload_csv(filepath, report_name)
                    
                    if public_url:
                        result = self.whatsapp.send_document(
                            phone, public_url, filename=report_name,
                            caption=f"📈 Weekly Report ({week_start.strftime('%Y-%m-%d')} to {(week_start + timedelta(days=6)).strftime('%Y-%m-%d')})"
                        )
                        
                        if result.get('success'):
                            response_msg = "✅ Weekly report generated and sent!"
                            self.whatsapp.send_message(phone, response_msg)
                            
                            try:
                                os.remove(filepath)
                            except:
                                pass
                            
                            self.task_service.complete_task(task['id'], 'client')
                            return {'success': True, 'response': response_msg, 'handler': 'weekly_report_sent'}
                    
                    raise Exception("Failed to send report")
                
                except Exception as e:
                    log_error(f"Error sending report: {str(e)}")
                    error_msg = "❌ Failed to send report. Please try again."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'weekly_report_send_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'weekly_report'}
            
        except Exception as e:
            log_error(f"Error in weekly report flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error generating report', 'handler': 'weekly_report_error'}
    
    def continue_monthly_report(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle monthly report flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_month')
            
            if step == 'ask_month':
                # Parse month
                month_input = message.strip().lower()
                
                try:
                    if month_input == 'this month':
                        target_month = date.today().month
                        target_year = date.today().year
                    elif month_input == 'last month':
                        last_month = date.today().replace(day=1) - timedelta(days=1)
                        target_month = last_month.month
                        target_year = last_month.year
                    else:
                        parts = message.strip().split('-')
                        target_month = int(parts[0])
                        target_year = int(parts[1])
                except (ValueError, IndexError):
                    msg = "❌ Invalid format. Please use MM-YYYY (e.g., 01-2024) or type 'this month'/'last month'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'monthly_report_invalid_month'}
                
                # Validate month
                if target_month < 1 or target_month > 12:
                    msg = "❌ Month must be between 01 and 12."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'monthly_report_invalid_month'}
                
                # Generate report
                success, msg, csv_content = self.report_service.generate_monthly_report(
                    client_id, target_month, target_year
                )
                
                if not success or not csv_content:
                    error_msg = f"❌ {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'monthly_report_failed'}
                
                # Save and send CSV
                try:
                    from services.helpers.supabase_storage import SupabaseStorageHelper
                    
                    temp_dir = tempfile.gettempdir()
                    report_name = f"monthly_report_{client_id}_{target_year}{target_month:02d}.csv"
                    filepath = os.path.join(temp_dir, report_name)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    storage_helper = SupabaseStorageHelper(self.db)
                    public_url = storage_helper.upload_csv(filepath, report_name)
                    
                    if public_url:
                        month_name = date(target_year, target_month, 1).strftime('%B %Y')
                        result = self.whatsapp.send_document(
                            phone, public_url, filename=report_name,
                            caption=f"📈 Monthly Report ({month_name})"
                        )
                        
                        if result.get('success'):
                            response_msg = "✅ Monthly report generated and sent!"
                            self.whatsapp.send_message(phone, response_msg)
                            
                            try:
                                os.remove(filepath)
                            except:
                                pass
                            
                            self.task_service.complete_task(task['id'], 'client')
                            return {'success': True, 'response': response_msg, 'handler': 'monthly_report_sent'}
                    
                    raise Exception("Failed to send report")
                
                except Exception as e:
                    log_error(f"Error sending report: {str(e)}")
                    error_msg = "❌ Failed to send report. Please try again."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'client')
                    return {'success': False, 'response': error_msg, 'handler': 'monthly_report_send_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'monthly_report'}
            
        except Exception as e:
            log_error(f"Error in monthly report flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error generating report', 'handler': 'monthly_report_error'}
