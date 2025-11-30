    def _handle_trainer_onboarding_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer onboarding flow response"""
        try:
            # Extract form data from flow response
            trainer_data = self._extract_trainer_data_from_flow_response(flow_response, phone_number)
            
            if not trainer_data:
                return {
                    'success': False,
                    'error': 'Failed to extract trainer data from flow'
                }
            
            log_info(f"Extracted trainer data: {trainer_data.get('name', 'Unknown')} - {trainer_data.get('email', 'No email')}")
            
            # Validate required fields
            validation_result = self._validate_trainer_data(trainer_data)
            if not validation_result['valid']:
                log_error(f"Trainer data validation failed: {validation_result['errors']}")
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation_result['errors']
                }
            
            # Use existing trainer registration system for consistency
            try:
                from services.registration.trainer_registration import TrainerRegistrationHandler
                
                # Create trainer using existing registration system
                reg_handler = TrainerRegistrationHandler(self.supabase, self.whatsapp_service)
                
                # Complete registration using existing system
                completion_result = reg_handler._complete_registration(phone_number, trainer_data)
                
                if completion_result.get('success'):
                    trainer_id = completion_result.get('trainer_id')
                    
                    log_info(f"Trainer registration completed via flow: {trainer_id}")
                    
                    # Mark any existing registration state as complete
                    try:
                        from services.registration.registration_state import RegistrationStateManager
                        state_manager = RegistrationStateManager(self.supabase)
                        
                        # Mark registration as complete
                        existing_state = state_manager.get_registration_state(phone_number)
                        if existing_state:
                            state_manager.complete_registration(phone_number, 'trainer')
                    except Exception as state_error:
                        log_warning(f"Could not update registration state: {str(state_error)}")
                    
                    return {
                        'success': True,
                        'message': 'Trainer profile created successfully via WhatsApp Flow',
                        'trainer_id': trainer_id,
                        'method': 'whatsapp_flow'
                    }
                else:
                    log_error(f"Registration completion failed: {completion_result.get('message')}")
                    return {
                        'success': False,
                        'error': f'Registration failed: {completion_result.get("message")}'
                    }
                    
            except ImportError as e:
                log_error(f"Could not import registration handler: {str(e)}")
                
                # Fallback: create trainer record directly
                trainer_id = self._create_trainer_record_direct(trainer_data, flow_token)
                
                if trainer_id:
                    return {
                        'success': True,
                        'message': 'Trainer profile created successfully (direct method)',
                        'trainer_id': trainer_id,
                        'method': 'direct_creation'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to create trainer record'
                    }
                
        except Exception as e:
            log_error(f"Error handling trainer onboarding response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }