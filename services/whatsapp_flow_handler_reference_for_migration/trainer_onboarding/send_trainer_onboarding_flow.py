    def send_trainer_onboarding_flow(self, phone_number: str) -> Dict:
        """Send the trainer onboarding flow to a phone number"""
        try:
            # Check if user is already a trainer
            existing_trainer = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if existing_trainer.data:
                return {
                    'success': False,
                    'error': 'User is already registered as a trainer',
                    'message': 'You are already registered as a trainer! If you need help, please contact support.'
                }
            
            # Send WhatsApp Flow
            flow_result = self._attempt_flow_sending(phone_number)
            
            if flow_result.get('success'):
                log_info(f"WhatsApp Flow sent successfully to {phone_number}")
                return flow_result
            
            # NO FALLBACK - Just return error with helpful message
            log_error(f"WhatsApp Flow failed for {phone_number}: {flow_result.get('error')}")
            
            # Send helpful error message to user
            try:
                self.whatsapp_service.send_message(
                    phone_number,
                    "😔 Sorry, I couldn't start the registration form. "
                    "Please try again in a few minutes or contact support."
                )
            except Exception as msg_error:
                log_error(f"Failed to send error message: {str(msg_error)}")
            
            return {
                'success': False,
                'error': flow_result.get('error', 'Flow sending failed'),
                'message': 'Registration flow unavailable'
            }
                
        except Exception as e:
            log_error(f"Error in trainer onboarding flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }