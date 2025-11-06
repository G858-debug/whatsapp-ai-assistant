"""
Trainer Habit Reporting Flow
Handles trainer viewing client progress and generating reports
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.logging_service import LoggingService
from services.habits.report_service import ReportService
from services.relationships.relationship_service import RelationshipService
import os
import tempfile


class ReportingFlow:
    """Handles habit reporting flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.logging_service = LoggingService(db)
        self.report_service = ReportService(db)
        self.relationship_service = RelationshipService(db)
    
    def continue_view_trainee_progress(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle view trainee progress flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id (case-insensitive lookup)
                client_id_input = message.strip()
                
                # Verify client is in trainer's list (this will handle case-insensitive lookup)
                relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id_input)
                if not relationship:
                    error_msg = f"❌ Client ID '{client_id_input}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'view_trainee_progress_not_found'}
                
                # Get the actual client_id from the relationship
                client_id = relationship.get('client_id')
                
                # Generate progress dashboard link
                from services.commands.dashboard import generate_trainee_progress_dashboard
                dashboard_result = generate_trainee_progress_dashboard(phone, trainer_id, client_id, self.db, self.whatsapp)
                
                # Complete the task since we've sent the dashboard
                self.task_service.complete_task(task['id'], 'trainer')
                
                if dashboard_result.get('success'):
                    return dashboard_result
                else:
                    # Fallback to old flow if dashboard fails
                    date_msg = (
                        f"📊 *View Client Progress*\n\n"
                        f"Which date would you like to see?\n\n"
                        f"*Options:*\n"
                        f"• Type 'today' for today's progress\n"
                        f"• Type 'yesterday' for yesterday\n"
                        f"• Or enter a date (YYYY-MM-DD format)\n\n"
                        f"Example: 2024-01-15"
                    )
                    self.whatsapp.send_message(phone, date_msg)
                    
                    task_data['client_id'] = client_id
                    task_data['step'] = 'ask_date'
                    self.task_service.update_task(task['id'], 'trainer', task_data)
                    return {'success': True, 'response': date_msg, 'handler': 'view_trainee_progress_ask_date'}
            
            elif step == 'ask_date':
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
                    return {'success': True, 'response': msg, 'handler': 'view_trainee_progress_invalid_date'}
                
                # Get progress
                success, msg, progress_list = self.logging_service.calculate_daily_progress(
                    task_data['client_id'], target_date
                )
                
                if not success:
                    error_msg = f"❌ Error calculating progress: {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'view_trainee_progress_error'}
                
                if not progress_list:
                    no_data_msg = f"📊 No progress data for {target_date.strftime('%Y-%m-%d')}"
                    self.whatsapp.send_message(phone, no_data_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': no_data_msg, 'handler': 'view_trainee_progress_no_data'}
                
                # Format progress
                response_msg = f"📊 *Client Progress*\n\n"
                response_msg += f"*Date:* {target_date.strftime('%Y-%m-%d')}\n"
                response_msg += f"*Client ID:* {task_data['client_id']}\n\n"
                
                for i, progress in enumerate(progress_list, 1):
                    response_msg += f"*{i}. {progress['habit_name']}*\n"
                    response_msg += f"   Target: {progress['target']} {progress['unit']}\n"
                    response_msg += f"   Completed: {progress['completed']} {progress['unit']}\n"
                    response_msg += f"   Due: {progress['due']} {progress['unit']}\n"
                    response_msg += f"   Progress: {progress['percentage']}%\n"
                    response_msg += f"   Logs: {progress['log_count']}\n\n"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'trainer')
                return {'success': True, 'response': response_msg, 'handler': 'view_trainee_progress_success'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'view_trainee_progress'}
            
        except Exception as e:
            log_error(f"Error in view trainee progress flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while viewing progress.\n\n"
                "The task has been cancelled. Please try again with /view-trainee-progress"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'view_trainee_progress_error'}
    
    def continue_trainee_report(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle trainee report flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            report_type = task_data.get('report_type', 'weekly')
            
            if step == 'ask_client_id':
                # User provided client_id (case-insensitive lookup)
                client_id_input = message.strip()
                
                # Verify client is in trainer's list (this will handle case-insensitive lookup)
                relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id_input)
                if not relationship:
                    error_msg = f"❌ Client ID '{client_id_input}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'trainee_report_not_found'}
                
                # Get the actual client_id from the relationship
                client_id = relationship.get('client_id')
                
                # Ask for period
                if report_type == 'weekly':
                    period_msg = (
                        f"📈 *Weekly Report*\n\n"
                        f"Which week would you like to see?\n\n"
                        f"*Options:*\n"
                        f"• Type 'this week' for current week\n"
                        f"• Type 'last week' for previous week\n"
                        f"• Or enter week start date (YYYY-MM-DD)\n\n"
                        f"Example: 2024-01-15"
                    )
                else:
                    period_msg = (
                        f"📈 *Monthly Report*\n\n"
                        f"Which month would you like to see?\n\n"
                        f"*Options:*\n"
                        f"• Type 'this month' for current month\n"
                        f"• Type 'last month' for previous month\n"
                        f"• Or enter month and year (MM-YYYY)\n\n"
                        f"Example: 01-2024 for January 2024"
                    )
                
                self.whatsapp.send_message(phone, period_msg)
                
                task_data['client_id'] = client_id
                task_data['step'] = 'ask_period'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': period_msg, 'handler': 'trainee_report_ask_period'}
            
            elif step == 'ask_period':
                period_input = message.strip().lower()
                
                try:
                    if report_type == 'weekly':
                        # Parse week
                        if period_input == 'this week':
                            week_start = date.today() - timedelta(days=date.today().weekday())
                        elif period_input == 'last week':
                            week_start = date.today() - timedelta(days=date.today().weekday() + 7)
                        else:
                            week_start = datetime.strptime(message.strip(), '%Y-%m-%d').date()
                        
                        # Generate report
                        success, msg, csv_content = self.report_service.generate_trainer_report(
                            trainer_id, task_data['client_id'], week_start, week_start + timedelta(days=6)
                        )
                        
                        report_name = f"weekly_report_{task_data['client_id']}_{week_start.strftime('%Y%m%d')}.csv"
                    
                    else:  # monthly
                        # Parse month
                        if period_input == 'this month':
                            target_month = date.today().month
                            target_year = date.today().year
                        elif period_input == 'last month':
                            last_month = date.today().replace(day=1) - timedelta(days=1)
                            target_month = last_month.month
                            target_year = last_month.year
                        else:
                            parts = message.strip().split('-')
                            target_month = int(parts[0])
                            target_year = int(parts[1])
                        
                        # Generate report
                        from calendar import monthrange
                        month_start = date(target_year, target_month, 1)
                        last_day = monthrange(target_year, target_month)[1]
                        month_end = date(target_year, target_month, last_day)
                        
                        success, msg, csv_content = self.report_service.generate_trainer_report(
                            trainer_id, task_data['client_id'], month_start, month_end
                        )
                        
                        report_name = f"monthly_report_{task_data['client_id']}_{target_year}{target_month:02d}.csv"
                
                except (ValueError, IndexError):
                    msg = "❌ Invalid format. Please follow the examples provided."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'trainee_report_invalid_period'}
                
                if not success or not csv_content:
                    error_msg = f"❌ {msg}"
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'trainee_report_failed'}
                
                # Save and send CSV
                try:
                    from services.helpers.supabase_storage import SupabaseStorageHelper
                    
                    temp_dir = tempfile.gettempdir()
                    filepath = os.path.join(temp_dir, report_name)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    storage_helper = SupabaseStorageHelper(self.db)
                    public_url = storage_helper.upload_csv(filepath, report_name)
                    
                    if public_url:
                        result = self.whatsapp.send_document(
                            phone, public_url, filename=report_name,
                            caption=f"📈 {report_type.capitalize()} Report for {task_data['client_id']}"
                        )
                        
                        if result.get('success'):
                            response_msg = "✅ Report generated and sent!"
                            self.whatsapp.send_message(phone, response_msg)
                            
                            try:
                                os.remove(filepath)
                            except:
                                pass
                            
                            self.task_service.complete_task(task['id'], 'trainer')
                            return {'success': True, 'response': response_msg, 'handler': 'trainee_report_sent'}
                    
                    raise Exception("Failed to send report")
                
                except Exception as e:
                    log_error(f"Error sending report: {str(e)}")
                    error_msg = "❌ Failed to send report. Please try again."
                    self.whatsapp.send_message(phone, error_msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': False, 'response': error_msg, 'handler': 'trainee_report_send_failed'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'trainee_report'}
            
        except Exception as e:
            log_error(f"Error in trainee report flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while generating the report.\n\n"
                "The task has been cancelled. Please try again."
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'trainee_report_error'}
    
    def continue_client_progress(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle client progress dashboard flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id (case-insensitive lookup)
                client_id_input = message.strip()
                
                # Verify client is in trainer's list
                relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id_input)
                if not relationship:
                    error_msg = f"❌ Client ID '{client_id_input}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'client_progress_not_found'}
                
                # Get the actual client_id from the relationship
                client_id = relationship.get('client_id')
                
                # Generate client progress dashboard link with trainer context
                dashboard_result = self._generate_client_progress_dashboard(phone, trainer_id, client_id)
                
                # Complete the task since we've sent the dashboard
                self.task_service.complete_task(task['id'], 'trainer')
                
                return dashboard_result
            
            return {'success': True, 'response': 'Processing...', 'handler': 'client_progress'}
            
        except Exception as e:
            log_error(f"Error in client progress flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while generating the progress dashboard.\n\n"
                "The task has been cancelled. Please try again with /client-progress"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'client_progress_error'}
    
    def _generate_client_progress_dashboard(self, phone: str, trainer_id: str, client_id: str) -> Dict:
        """Generate client progress dashboard link for trainer view"""
        try:
            from services.dashboard import DashboardTokenManager
            import os
            
            # Generate secure token for trainer viewing client progress
            token_manager = DashboardTokenManager(self.db)
            token = token_manager.generate_token(trainer_id, 'trainer', 'view_client_progress')
            
            if not token:
                return {
                    'success': False,
                    'response': "❌ Could not generate progress dashboard. Please try again.",
                    'handler': 'client_progress_dashboard_error'
                }
            
            # Get client name
            client_result = self.db.table('clients').select('name').eq('client_id', client_id).execute()
            client_name = client_result.data[0]['name'] if client_result.data else client_id
            
            # Get base URL from environment or use default
            base_url = os.getenv('BASE_URL', 'https://your-app.railway.app')
            dashboard_url = f"{base_url}/dashboard/trainer/{trainer_id}/{token}/trainee/{client_id}"
            
            msg = (
                f"📊 *{client_name}'s Progress Dashboard*\n\n"
                f"Comprehensive progress tracking and analysis:\n\n"
                f"🔗 {dashboard_url}\n\n"
                f"✨ *Features:*\n"
                f"• Detailed habit progress tracking\n"
                f"• Individual habit performance\n"
                f"• Progress streaks and achievements\n"
                f"• Leaderboard with your other trainees\n"
                f"• Completion statistics\n"
                f"• Mobile-friendly interface\n\n"
                f"🎯 *Perfect for:*\n"
                f"• Monitoring client progress\n"
                f"• Identifying improvement areas\n"
                f"• Celebrating achievements\n"
                f"• Comparing performance\n\n"
                f"🔒 *Security:* Link expires in 1 hour"
            )
            
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'client_progress_dashboard_sent',
                'dashboard_url': dashboard_url
            }
            
        except Exception as e:
            log_error(f"Error generating client progress dashboard: {str(e)}")
            return {
                'success': False,
                'response': "❌ Could not generate progress dashboard. Please try again.",
                'handler': 'client_progress_dashboard_error'
            }