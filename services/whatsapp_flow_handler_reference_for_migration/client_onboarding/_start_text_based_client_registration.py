    def _start_text_based_client_registration(self, phone_number: str) -> Dict:
        """Start text-based client registration as fallback"""
        try:
            from services.registration.client_registration import ClientRegistrationHandler
            
            # Initialize client registration handler
            client_reg = ClientRegistrationHandler(self.supabase, self.whatsapp_service)
            
            # Start registration
            welcome_message = client_reg.start_registration(phone_number)
            
            if welcome_message:
                log_info(f"Started text-based client registration for {phone_number}")
                return {
                    'success': True,
                    'message': welcome_message,
                    'method': 'text_based'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to start text-based registration'
                }
                
        except Exception as e:
            log_error(f"Error starting text-based client registration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }