"""
Client Trainer Search Flow
Handles client searching for trainers
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.relationships import RelationshipService


class SearchFlow:
    """Handles trainer search flows"""
    
    def __init__(self, db, whatsapp, task_service):
        self.db = db
        self.whatsapp = whatsapp
        self.task_service = task_service
        self.relationship_service = RelationshipService(db)
    
    def continue_search_trainer(self, phone: str, message: str, client_id: str, task: Dict) -> Dict:
        """Handle search trainer flow"""
        try:
            task_data = task.get('task_data', {})
            step = task_data.get('step', 'ask_search_term')
            
            if step == 'ask_search_term':
                # User provided search term
                search_term = message.strip()
                
                if len(search_term) < 2:
                    msg = "Please provide at least 2 characters to search."
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'search_trainer_invalid'}
                
                # Search trainers
                results = self.relationship_service.search_trainers(search_term, limit=5)
                
                if not results:
                    msg = (
                        f"❌ No trainers found matching '{search_term}'.\n\n"
                        f"Try a different search term or type /stop to cancel."
                    )
                    self.whatsapp.send_message(phone, msg)
                    return {'success': True, 'response': msg, 'handler': 'search_trainer_no_results'}
                
                # Format results
                msg = f"🔍 *Search Results for '{search_term}'*\n\n"
                
                for i, trainer in enumerate(results, 1):
                    msg += (
                        f"*{i}. {trainer.get('first_name')} {trainer.get('last_name')}*\n"
                        f"   ID: {trainer.get('trainer_id')}\n"
                        f"   Specialization: {trainer.get('specialization', 'N/A')}\n"
                        f"   Experience: {trainer.get('years_of_experience', 'N/A')} years\n"
                    )
                    
                    if trainer.get('business_name'):
                        msg += f"   Business: {trainer.get('business_name')}\n"
                    
                    msg += "\n"
                
                msg += (
                    f"💡 *To invite a trainer:*\n"
                    f"Copy their ID and type:\n"
                    f"/invite-trainer"
                )
                
                self.whatsapp.send_message(phone, msg)
                self.task_service.complete_task(task['id'], 'client')
                
                return {'success': True, 'response': msg, 'handler': 'search_trainer_results'}
            
            return {'success': True, 'response': 'Processing...', 'handler': 'search_trainer'}
            
        except Exception as e:
            log_error(f"Error in search trainer flow: {str(e)}")
            
            # Stop the task
            self.task_service.stop_task(task['id'], 'client')
            
            # Send error message
            error_msg = (
                "❌ *Error Occurred*\n\n"
                "Sorry, I encountered an error while searching for trainers.\n\n"
                "The task has been cancelled. Please try again with /search-trainer"
            )
            self.whatsapp.send_message(phone, error_msg)
            
            return {'success': False, 'response': error_msg, 'handler': 'search_trainer_error'}