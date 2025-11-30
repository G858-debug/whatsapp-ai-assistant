    def handle_flow_response(self, flow_data: Dict) -> Dict:
        """Process completed trainer onboarding flow"""
        try:
            # Extract phone number from flow data
            phone_number = flow_data.get('phone_number')
            
            if not phone_number:
                log_error("No phone number in flow response data")
                return {
                    'success': False,
                    'error': 'Missing phone number in flow data'
                }
            
            log_info(f"Processing flow response for {phone_number}")
            
            # Extract flow response payload
            flow_response = flow_data.get('flow_response', {})
            
            if not flow_response:
                log_error("No flow_response in flow data")
                return {
                    'success': False,
                    'error': 'Missing flow response data'
                }
            
            # Get flow name and token
            flow_name = flow_response.get('name', 'trainer_onboarding_flow')
            flow_token = flow_response.get('flow_token')
            
            log_info(f"Flow name: {flow_name}, Flow token: {flow_token}")
            
            # Route to appropriate handler based on flow type
            if flow_name in ['trainer_onboarding_flow', 'flow']:
                return self._handle_trainer_onboarding_response(flow_response, phone_number, flow_token)
            elif flow_name == 'trainer_profile_edit_flow':
                return self._handle_trainer_profile_edit_response(flow_response, phone_number, flow_token)
            elif flow_name == 'client_profile_edit_flow':
                return self._handle_client_profile_edit_response(flow_response, phone_number, flow_token)
            elif flow_name == 'trainer_add_client_flow':
                return self._handle_trainer_add_client_response(flow_response, phone_number, flow_token)
            elif flow_name == 'client_onboarding_flow':
                return self._handle_client_onboarding_response(flow_response, phone_number, flow_token)
            elif flow_name in ['trainer_habit_setup_flow', 'client_habit_logging_flow', 'habit_progress_flow']:
                return self.handle_habit_flow_response(flow_data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown flow type: {flow_name}'
                }
                
        except Exception as e:
            log_error(f"Error handling flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }