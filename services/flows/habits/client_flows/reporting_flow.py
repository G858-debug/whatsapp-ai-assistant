"""
Client Habit Reporting Flow
Handles client generating habit reports
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.report_service import ReportService
import os
import tempfile


class ReportingFlow:
    """Handles habit reporting flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.report_service = ReportService(db)
    
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