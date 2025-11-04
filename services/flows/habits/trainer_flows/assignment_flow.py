"""
Trainer Habit Assignment Flow
Handles trainer assigning habits to clients
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.habits.habit_service import HabitService
from services.habits.assignment_service import AssignmentService
from services.relationships.relationship_service import RelationshipService


class AssignmentFlow:
    """Handles habit assignment flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.habit_service = HabitService(db)
        self.assignment_service = AssignmentService(db)
        self.relationship_service = RelationshipService(db)
    
    def continue_assign_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle assign habit flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_habit_id')
            
            if step == 'ask_habit_id':
                # User provided habit_id (case-insensitive search)
                habit_id_input = message.strip()
                
                # Find habit by case-insensitive search
                habit_result = self.db.table('fitness_habits').select('*').ilike('habit_id', habit_id_input).eq('trainer_id', trainer_id).execute()
                
                if not habit_result.data:
                    error_msg = f"❌ Habit ID '{habit_id_input}' not found. Please check and try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'assign_habit_not_found'}
                
                habit = habit_result.data[0]
                habit_id = habit.get('habit_id')  # Use the actual habit_id from database
                
                # Show habit details
                info_msg = (
                    f"📌 *Assign Habit*\n\n"
                    f"*Habit:* {habit.get('habit_name')}\n"
                    f"*Target:* {habit.get('target_value')} {habit.get('unit')}\n"
                    f"*Frequency:* {habit.get('frequency')}\n\n"
                    f"Now, provide the client ID(s) to assign this habit.\n\n"
                    f"💡 You can provide:\n"
                    f"• Single ID: CLI123\n"
                    f"• Multiple IDs: CLI123, CLI456, CLI789\n\n"
                    f"Use /view-trainees to see your clients."
                )
                self.whatsapp.send_message(phone, info_msg)
                
                task_data['habit_id'] = habit_id
                task_data['habit'] = habit
                task_data['step'] = 'ask_client_ids'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': info_msg, 'handler': 'assign_habit_ask_clients'}
            
            elif step == 'ask_client_ids':
                # Parse client IDs (preserve original case for case-insensitive lookup)
                client_ids_raw = message.strip()
                client_ids = [cid.strip() for cid in client_ids_raw.replace(',', ' ').split()]
                
                if not client_ids:
                    msg = "❌ Please provide at least one client ID."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'assign_habit_no_ids'}
                
                # Verify clients are in trainer's list
                valid_clients = []
                invalid_clients = []
                
                for client_id in client_ids:
                    if self.relationship_service.check_relationship_exists(trainer_id, client_id):
                        valid_clients.append(client_id)
                    else:
                        invalid_clients.append(client_id)
                
                if not valid_clients:
                    msg = "❌ None of the provided client IDs are in your client list."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'assign_habit_no_valid_clients'}
                
                # Assign habit
                success, msg, results = self.assignment_service.assign_habit(
                    task_data['habit_id'], valid_clients, trainer_id
                )
                
                # Build response
                response_msg = f"📌 *Assignment Results*\n\n"
                
                if results['assigned']:
                    response_msg += f"✅ Assigned to {len(results['assigned'])} client(s)\n"
                
                if results['already_assigned']:
                    response_msg += f"ℹ️ {len(results['already_assigned'])} already had this habit\n"
                
                if invalid_clients:
                    response_msg += f"❌ {len(invalid_clients)} not in your client list\n"
                
                response_msg += f"\n*Habit:* {task_data['habit'].get('habit_name')}"
                
                self.whatsapp.send_message(phone, response_msg)
                self.task_service.complete_task(task['id'], 'trainer')
                return {'success': True, 'response': response_msg, 'handler': 'assign_habit_complete'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'assign_habit'}
            
        except Exception as e:
            log_error(f"Error in assign habit flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while assigning the habit.\n\n"
                "The task has been cancelled. Please try again with /assign-habit"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'assign_habit_error'}