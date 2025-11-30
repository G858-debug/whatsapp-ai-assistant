    def handle_client_onboarding_request(self, phone_number: str) -> Dict:
        """Main entry point for client onboarding - tries flow first, falls back to text"""
        try:
            log_info(f"Processing client onboarding request for {phone_number}")
            
            # Check if user is already registered as a client
            existing_client = self.supabase.table('clients').select('*').eq('whatsapp', phone_number).execute()
            if existing_client.data:
                client_name = existing_client.data[0].get('name', 'there')
                return {
                    'success': True,
                    'already_registered': True,
                    'message': f"Welcome back, {client_name}! You're already registered as a client. How can I help you today?"
                }
            
            # Try to send WhatsApp Flow with automatic fallback
            result = self.send_client_onboarding_flow(phone_number)
            
            if result.get('success'):
                if result.get('method') == 'text_fallback':
                    # Text registration started successfully
                    return {
                        'success': True,
                        'method': 'text_fallback',
                        'message': result.get('message')
                    }
                else:
                    # WhatsApp Flow sent successfully
                    return {
                        'success': True,
                        'method': 'whatsapp_flow',
                        'message': 'WhatsApp Flow sent! Please complete the registration form.',
                        'flow_token': result.get('flow_token')
                    }
            else:
                # Both flow and fallback failed
                return {
                    'success': False,
                    'error': result.get('error', 'Client onboarding failed')
                }
                
        except Exception as e:
            log_error(f"Error handling client onboarding request: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }