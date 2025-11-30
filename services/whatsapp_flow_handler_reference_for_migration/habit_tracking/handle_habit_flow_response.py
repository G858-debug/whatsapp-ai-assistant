    def handle_habit_flow_response(self, flow_data: Dict) -> Dict:
        """Handle responses from habit tracking flows"""
        try:
            flow_token = flow_data.get('flow_token')
            if not flow_token:
                return {'success': False, 'error': 'No flow token provided'}
            
            # Get flow context
            token_data = self._get_flow_token_data(flow_token)
            if not token_data:
                return {'success': False, 'error': 'Invalid or expired flow token'}
            
            flow_type = token_data.get('type')
            
            if flow_type == 'trainer_habit_setup':
                return self._handle_trainer_habit_setup_response(flow_data, token_data)
            elif flow_type == 'client_habit_logging':
                return self._handle_client_habit_logging_response(flow_data, token_data)
            elif flow_type == 'habit_progress':
                return self._handle_habit_progress_response(flow_data, token_data)
            else:
                return {'success': False, 'error': f'Unknown habit flow type: {flow_type}'}
                
        except Exception as e:
            log_error(f"Error handling habit flow response: {str(e)}")
            return {'success': False, 'error': str(e)}