"""
Client Habit Progress Flow
Handles client viewing their habit progress
"""
from typing import Dict
from datetime import datetime, date, timedelta
from utils.logger import log_info, log_error
from services.habits.logging_service import LoggingService


class ProgressFlow:
    """Handles habit progress viewing flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.logging_service = LoggingService(db)
    
    def continue_view_progress(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle view progress flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_view_type')
            
            if step == 'ask_view_type':
                # Parse view type
                view_input = message.strip().lower()
                
                if view_input in ['1', 'daily']:
                    view_type = 'daily'
                    next_step = 'ask_date'
                    next_msg = (
                        "📅 *Daily Progress View*\n\n"
                        "Which date would you like to see?\n\n"
                        "*Options:*\n"
                        "• Type 'today' for today's progress\n"
                        "• Type 'yesterday' for yesterday\n"
                        "• Or enter a date (YYYY-MM-DD format)\n\n"
                        "Example: 2024-01-15\n\n"
                        "Type /stop to cancel."
                    )
                elif view_input in ['2', 'monthly']:
                    view_type = 'monthly'
                    next_step = 'ask_month'
                    next_msg = (
                        "📈 *Monthly Progress View*\n\n"
                        "Which month would you like to see?\n\n"
                        "*Options:*\n"
                        "• Type 'this month' for current month\n"
                        "• Type 'last month' for previous month\n"
                        "• Or enter month and year (MM-YYYY)\n\n"
                        "Example: 01-2024 for January 2024\n\n"
                        "Type /stop to cancel."
                    )
                else:
                    msg = "❌ Invalid choice. Please type '1' for daily or '2' for monthly view."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'view_progress_invalid_choice'}
                
                # Update task with view type
                task_data['view_type'] = view_type
                task_data['step'] = next_step
                self.task_service.update_task(task['id'], 'client', task_data)
                
                self.whatsapp.send_message(phone, next_msg)
                return {'success': True, 'response': next_msg, 'handler': 'view_progress_view_type_selected'}
            
            elif step == 'ask_date':
                # Parse date for daily view
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
                
                # Generate dashboard link with daily view
                dashboard_result = self._generate_progress_dashboard(
                    phone, client_id, 'daily', date=target_date.strftime('%Y-%m-%d')
                )
                
                self.task_service.complete_task(task['id'], 'client')
                return dashboard_result
            
            elif step == 'ask_month':
                # Parse month for monthly view
                month_input = message.strip().lower()
                
                try:
                    if month_input == 'this month':
                        target_month = date.today().strftime('%m')
                        target_year = date.today().strftime('%Y')
                    elif month_input == 'last month':
                        last_month_date = date.today().replace(day=1) - timedelta(days=1)
                        target_month = last_month_date.strftime('%m')
                        target_year = last_month_date.strftime('%Y')
                    else:
                        # Parse MM-YYYY format
                        month_parts = message.strip().split('-')
                        if len(month_parts) != 2:
                            raise ValueError("Invalid format")
                        target_month = month_parts[0].zfill(2)
                        target_year = month_parts[1]
                        
                        # Validate month and year
                        if not (1 <= int(target_month) <= 12):
                            raise ValueError("Invalid month")
                        if not (2020 <= int(target_year) <= 2030):
                            raise ValueError("Invalid year")
                            
                except (ValueError, IndexError):
                    msg = "❌ Invalid format. Please use MM-YYYY (e.g., 01-2024) or type 'this month'/'last month'."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'view_progress_invalid_month'}
                
                # Generate dashboard link with monthly view
                dashboard_result = self._generate_progress_dashboard(
                    phone, client_id, 'monthly', month=target_month, year=target_year
                )
                
                self.task_service.complete_task(task['id'], 'client')
                return dashboard_result
            
            return {'success': True, 'response': 'Processing...', 'handler': 'view_progress'}
            
        except Exception as e:
            log_error(f"Error in view progress flow: {str(e)}")
            self.task_service.complete_task(task['id'], 'client')
            return {'success': False, 'response': 'Error viewing progress', 'handler': 'view_progress_error'}
    
    def _generate_progress_dashboard(self, phone: str, client_id: str, view_type: str, date=None, month=None, year=None) -> Dict:
        """Generate progress dashboard link with parameters"""
        try:
            from services.commands.dashboard import generate_client_habits_dashboard
            
            # Generate base dashboard link
            dashboard_result = generate_client_habits_dashboard(phone, client_id, self.db, self.whatsapp)
            
            if dashboard_result['success']:
                # Get the dashboard URL and add parameters
                base_url = dashboard_result['dashboard_url']
                
                # Add view parameters to URL
                if '?' in base_url:
                    url_params = '&'
                else:
                    url_params = '?'
                
                url_params += f'view={view_type}'
                
                if view_type == 'daily' and date:
                    url_params += f'&date={date}'
                elif view_type == 'monthly' and month and year:
                    url_params += f'&month={month}&year={year}'
                
                dashboard_url = base_url + url_params
                
                # Create custom message with parameters
                if view_type == 'daily':
                    date_str = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
                    msg = (
                        f"📊 *Your Daily Progress Dashboard*\n\n"
                        f"📅 *Date:* {date_str}\n\n"
                        f"View your detailed habit progress:\n\n"
                        f"🔗 {dashboard_url}\n\n"
                        f"✨ *Features:*\n"
                        f"• Daily progress tracking\n"
                        f"• Target vs completed comparison\n"
                        f"• Habit streaks and achievements\n"
                        f"• Leaderboard with other trainees\n"
                        f"• Trainer assignment details\n\n"
                        f"🔒 *Security:* Link expires in 1 hour"
                    )
                else:  # monthly
                    month_name = datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d').strftime('%B %Y')
                    msg = (
                        f"📈 *Your Monthly Progress Dashboard*\n\n"
                        f"📅 *Month:* {month_name}\n\n"
                        f"View your detailed habit progress:\n\n"
                        f"🔗 {dashboard_url}\n\n"
                        f"✨ *Features:*\n"
                        f"• Monthly progress tracking\n"
                        f"• Target vs completed comparison\n"
                        f"• Habit streaks and achievements\n"
                        f"• Leaderboard with other trainees\n"
                        f"• Trainer assignment details\n\n"
                        f"🔒 *Security:* Link expires in 1 hour"
                    )
                
                self.whatsapp.send_message(phone, msg)
                
                return {
                    'success': True,
                    'response': msg,
                    'handler': 'view_progress_dashboard_sent',
                    'dashboard_url': dashboard_url
                }
            else:
                return dashboard_result
                
        except Exception as e:
            log_error(f"Error generating progress dashboard: {str(e)}")
            return {
                'success': False,
                'response': "❌ Could not generate progress dashboard. Please try again.",
                'handler': 'view_progress_dashboard_error'
            }