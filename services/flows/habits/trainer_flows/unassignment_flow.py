"""
Trainer Habit Unassignment Flow
Handles trainer unassigning habits from clients
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.habits.assignment_service import AssignmentService
from services.relationships.relationship_service import RelationshipService


class UnassignmentFlow:
    """Handles habit unassignment flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.assignment_service = AssignmentService(db)
        self.relationship_service = RelationshipService(db)
    
    def continue_unassign_habit(self, phone: str, message: str, trainer_id: str, task: Dict) -> Dict:
        """Handle unassign habit flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_client_id')
            
            if step == 'ask_client_id':
                # User provided client_id (case-insensitive lookup)
                client_id_input = message.strip()
                
                # Verify client is in trainer's list (this will handle case-insensitive lookup)
                relationship = self.relationship_service.check_relationship_exists(trainer_id, client_id_input)
                if not relationship:
                    error_msg = f"❌ Trainee ID '{client_id_input}' not found in your client list."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'unassign_habit_trainee_not_found'}
                
                # Get the actual client_id from the relationship
                client_id = relationship.get('client_id')
                
                # Generate trainee habits dashboard link
                from services.commands.dashboard import generate_trainee_habits_dashboard
                dashboard_result = generate_trainee_habits_dashboard(phone, trainer_id, client_id, self.db, self.whatsapp)
                
                # Ask for habit ID
                msg = (
                    f"🗑️ *Unassign Habit - Step 2*\n\n"
                    f"Please provide the habit ID you want to unassign from this trainee.\n\n"
                )
                
                if dashboard_result.get('success'):
                    msg += (
                        f"💡 *View trainee's habits above* ⬆️ to find the habit ID\n\n"
                        f"📋 *Steps:* Find the habit → Copy its ID → Return here with the ID\n\n"
                    )
                else:
                    msg += f"💡 Check the trainee's assigned habits to find the habit ID.\n\n"
                
                msg += "Type /stop to cancel."
                
                self.whatsapp.send_message(phone, msg)
                
                task_data['client_id'] = client_id
                task_data['step'] = 'ask_habit_id'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': msg, 'handler': 'unassign_habit_ask_habit_id'}
            
            elif step == 'ask_habit_id':
                # User provided habit_id (case-insensitive search)
                habit_id_input = message.strip()
                client_id = task_data.get('client_id')
                
                # Find habit by case-insensitive search and verify it's assigned by this trainer
                habit_result = self.db.table('trainee_habit_assignments').select(
                    '*, fitness_habits(*)'
                ).ilike('habit_id', habit_id_input).eq('client_id', client_id).eq('trainer_id', trainer_id).eq('is_active', True).execute()
                
                if not habit_result.data:
                    error_msg = f"❌ Habit ID '{habit_id_input}' not found in your assignments to this trainee."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'unassign_habit_not_found'}
                
                assignment = habit_result.data[0]
                habit = assignment.get('fitness_habits')
                habit_id = assignment.get('habit_id')  # Use the actual habit_id from database
                
                if not habit:
                    error_msg = "❌ Habit details not found. Please try again."
                    self.whatsapp.send_message(phone, error_msg)
                    return {'success': True, 'response': error_msg, 'handler': 'unassign_habit_details_error'}
                
                # Ask for confirmation
                confirm_msg = (
                    f"⚠️ *Confirm Unassignment*\n\n"
                    f"*Habit:* {habit.get('habit_name')}\n"
                    f"*Target:* {habit.get('target_value')} {habit.get('unit')}\n"
                    f"*Trainee:* {client_id}\n\n"
                    f"This will:\n"
                    f"• Remove this habit from the trainee\n"
                    f"• Keep all existing habit logs\n"
                    f"• Stop future progress tracking\n\n"
                    f"Reply *YES* to confirm unassignment, or *NO* to cancel."
                )
                self.whatsapp.send_message(phone, confirm_msg)
                
                task_data['habit_id'] = habit_id
                task_data['habit'] = habit
                task_data['step'] = 'confirm'
                self.task_service.update_task(task['id'], 'trainer', task_data)
                return {'success': True, 'response': confirm_msg, 'handler': 'unassign_habit_confirm'}
            
            elif step == 'confirm':
                response = message.strip().lower()
                
                if response == 'yes':
                    # Unassign habit
                    success, msg = self.assignment_service.unassign_habit(
                        task_data['habit_id'], 
                        task_data['client_id'], 
                        trainer_id
                    )
                    
                    if success:
                        habit_name = task_data['habit'].get('habit_name')
                        response_msg = f"✅ Habit '{habit_name}' unassigned successfully!"
                        self.whatsapp.send_message(phone, response_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': True, 'response': response_msg, 'handler': 'unassign_habit_success'}
                    else:
                        error_msg = f"❌ Failed to unassign habit: {msg}"
                        self.whatsapp.send_message(phone, error_msg)
                        self.task_service.complete_task(task['id'], 'trainer')
                        return {'success': False, 'response': error_msg, 'handler': 'unassign_habit_failed'}
                
                elif response == 'no':
                    msg = "✅ Unassignment cancelled. Habit remains assigned."
                    self.whatsapp.send_message(phone, msg)
                    self.task_service.complete_task(task['id'], 'trainer')
                    return {'success': True, 'response': msg, 'handler': 'unassign_habit_cancelled'}
                
                else:
                    msg = "Please reply *YES* to confirm or *NO* to cancel."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'unassign_habit_invalid_response'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'unassign_habit'}
            
        except Exception as e:
            log_error(f"Error in unassign habit flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'trainer')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while unassigning the habit.\n\n"
                "The task has been cancelled. Please try again with /unassign-habit"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'unassign_habit_error'}