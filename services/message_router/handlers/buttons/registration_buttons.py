"""
Registration Button Handler
Handles registration and login button interactions
"""
from typing import Dict
from utils.logger import log_info, log_error
from services.flows.whatsapp_flow_trainer_onboarding import WhatsAppFlowTrainerOnboarding


class RegistrationButtonHandler:
    """Handles registration and login buttons"""
    
    def __init__(self, supabase_client, whatsapp_service, auth_service, reg_service=None, task_service=None):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.auth_service = auth_service
        self.reg_service = reg_service
        self.task_service = task_service
    
    def handle_registration_button(self, phone: str, button_id: str) -> Dict:
        """Handle registration and login buttons"""
        try:
            if button_id == 'register_trainer':
                return self._handle_register_trainer(phone)
            elif button_id == 'register_client':
                return self._handle_register_client(phone)
            elif button_id == 'login_trainer':
                return self._handle_login_trainer(phone)
            elif button_id == 'login_client':
                return self._handle_login_client(phone)
            else:
                return {'success': False, 'response': 'Unknown registration button', 'handler': 'unknown_registration_button'}
                
        except Exception as e:
            log_error(f"Error handling registration button: {str(e)}")
            return {'success': False, 'response': 'Error processing registration button', 'handler': 'registration_button_error'}
    
    def _handle_register_trainer(self, phone: str) -> Dict:
        """Handle trainer registration button"""
        try:
            log_info(f"Registration button clicked: register_trainer for phone: {phone}")

            # Try WhatsApp Flow first
            log_info(f"Attempting WhatsApp Flow for trainer onboarding: {phone}")
            try:
                flow_handler = WhatsAppFlowTrainerOnboarding(self.db, self.whatsapp)
                flow_result = flow_handler.send_flow(phone)

                if flow_result.get('success') == True:
                    log_info(f"WhatsApp Flow sent successfully to {phone}")
                    return {
                        'success': True,
                        'response': 'WhatsApp Flow sent successfully',
                        'handler': 'register_trainer_flow',
                        'method': 'whatsapp_flow'
                    }
                else:
                    # Flow failed, log and fall back to text-based registration
                    log_info(f"WhatsApp Flow failed for {phone}, using text-based registration fallback. Reason: {flow_result.get('error', 'Unknown error')}")
            except Exception as flow_error:
                # Flow exception, log and fall back to text-based registration
                log_error(f"WhatsApp Flow exception for {phone}, using text-based registration fallback: {str(flow_error)}")

            # Fallback to text-based registration
            log_info(f"Starting text-based registration for trainer: {phone}")
            from services.flows import RegistrationFlowHandler
            handler = RegistrationFlowHandler(
                self.db, self.whatsapp, self.auth_service,
                self.reg_service, self.task_service
            )
            return handler.start_registration(phone, 'trainer')
        except Exception as e:
            log_error(f"Error handling trainer registration: {str(e)}")
            return {'success': False, 'response': 'Error starting registration', 'handler': 'register_trainer_error'}
    
    def _handle_register_client(self, phone: str) -> Dict:
        """Handle client registration button"""
        try:
            log_info(f"Registration button clicked: register_client")
            from services.flows import RegistrationFlowHandler
            handler = RegistrationFlowHandler(
                self.db, self.whatsapp, self.auth_service,
                self.reg_service, self.task_service
            )
            return handler.start_registration(phone, 'client')
        except Exception as e:
            log_error(f"Error handling client registration: {str(e)}")
            return {'success': False, 'response': 'Error starting registration', 'handler': 'register_client_error'}
    
    def _handle_login_trainer(self, phone: str) -> Dict:
        """Handle trainer login button"""
        try:
            log_info(f"Login button clicked: login_trainer")
            from services.flows import LoginFlowHandler
            handler = LoginFlowHandler(self.db, self.whatsapp, self.auth_service, self.task_service)
            return handler.handle_role_selection(phone, 'trainer')
        except Exception as e:
            log_error(f"Error handling trainer login: {str(e)}")
            return {'success': False, 'response': 'Error processing login', 'handler': 'login_trainer_error'}
    
    def _handle_login_client(self, phone: str) -> Dict:
        """Handle client login button"""
        try:
            log_info(f"Login button clicked: login_client")
            from services.flows import LoginFlowHandler
            handler = LoginFlowHandler(self.db, self.whatsapp, self.auth_service, self.task_service)
            return handler.handle_role_selection(phone, 'client')
        except Exception as e:
            log_error(f"Error handling client login: {str(e)}")
            return {'success': False, 'response': 'Error processing login', 'handler': 'login_client_error'}