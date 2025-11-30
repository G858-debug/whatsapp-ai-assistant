    def handle_trainer_registration_request(self, phone_number: str) -> Dict:
        """Main entry point for trainer registration - tries flow first, falls back to text"""
        try:
            log_info(f"Processing trainer registration request for {phone_number}")
            
            # Check if user is already registered
            existing_trainer = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if existing_trainer.data:
                trainer_name = existing_trainer.data[0].get('first_name', 'there')
                return {
                    'success': True,
                    'already_registered': True,
                    'message': f"Welcome back, {trainer_name}! You're already registered as a trainer. How can I help you today?"
                }
            
            # Try to send WhatsApp Flow with automatic fallback
            result = self.send_trainer_onboarding_flow(phone_number)
            
            if result.get('success'):
                if result.get('method') == 'text_fallback':
                    # Text registration started successfully
                    return {
                        'success': True,
                        'method': 'text_registration',
                        'message': result.get('message'),
                        'conversation_state_update': {
                            'state': 'REGISTRATION',
                            'context': {
                                'type': 'trainer',
                                'current_step': 0
                            }
                        }
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
                # Both methods failed
                return {
                    'success': False,
                    'error': 'Registration system temporarily unavailable',
                    'message': 'Sorry, our registration system is temporarily unavailable. Please try again later or contact support.',
                    'details': result.get('details', result.get('error'))
                }
                
        except Exception as e:
            log_error(f"Error handling trainer registration request: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Something went wrong with registration. Please try again later.'
            }