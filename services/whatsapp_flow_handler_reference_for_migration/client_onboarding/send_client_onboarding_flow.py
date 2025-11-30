    def send_client_onboarding_flow(self, phone_number: str) -> Dict:
        """Send client onboarding flow with automatic fallback to text registration"""
        try:
            log_info(f"Attempting to send client onboarding flow to {phone_number}")

            # Try to send WhatsApp Flow
            flow_result = self._attempt_client_flow_sending(phone_number)

            if flow_result.get('success'):
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'message': 'Client onboarding flow sent successfully',
                    'flow_token': flow_result.get('flow_token')
                }
            else:
                log_info(f"WhatsApp Flow failed for {phone_number}, using text fallback: {flow_result.get('error')}")
                # Automatic fallback to text-based registration
                fallback_result = self._start_text_based_client_registration(phone_number)

                if fallback_result.get('success'):
                    return {
                        'success': True,
                        'method': 'text_fallback',
                        'message': fallback_result.get('message'),
                        'fallback_reason': flow_result.get('error')
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Both flow and fallback failed: {fallback_result.get('error')}"
                    }

        except Exception as e:
            log_error(f"Error sending client onboarding flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }