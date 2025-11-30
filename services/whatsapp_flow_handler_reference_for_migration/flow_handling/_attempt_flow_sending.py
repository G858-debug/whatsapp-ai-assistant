    def _attempt_flow_sending(self, phone_number: str) -> Dict:
        """Attempt to send WhatsApp Flow (assumes flow is already created in Facebook Console)"""
        try:
            # Create flow message (assumes flow exists in Facebook Console)
            flow_message = self.create_flow_message(phone_number)
            if not flow_message:
                return {
                    'success': False,
                    'error': 'Failed to create flow message',
                    'fallback_required': True
                }
            
            # Send via WhatsApp service
            result = self.whatsapp_service.send_flow_message(flow_message)
            
            if result.get('success'):
                # Store flow token for tracking
                self._store_flow_token(phone_number, flow_message['interactive']['action']['parameters']['flow_token'])
                
                return {
                    'success': True,
                    'message': 'Trainer onboarding flow sent successfully',
                    'flow_token': flow_message['interactive']['action']['parameters']['flow_token']
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send flow message: {result.get("error")}',
                    'fallback_required': True
                }
                
        except Exception as e:
            log_error(f"Error attempting flow sending: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fallback_required': True
            }