    def _handle_client_onboarding_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle client onboarding flow response"""
        try:
            log_info(f"Processing client onboarding flow response for {phone_number}")

            # Check if this is an invitation flow (Scenario 1A)
            if flow_token and flow_token.startswith('client_invitation_'):
                log_info(f"Processing client invitation flow completion for {phone_number}")
                return self._handle_client_invitation_flow_completion(flow_response, phone_number, flow_token)

            # Regular client onboarding (not from invitation)
            # Extract client data from flow response
            client_data = self._extract_client_data_from_onboarding_response(flow_response, phone_number)

            if not client_data:
                return {
                    'success': False,
                    'error': 'Failed to extract client data from flow response'
                }

            # Complete client registration using the existing handler
            from services.registration.client_registration import ClientRegistrationHandler

            client_reg_handler = ClientRegistrationHandler(self.supabase, self.whatsapp_service)

            # Complete registration with flow data
            result = client_reg_handler._complete_registration(phone_number, client_data)

            if result.get('success'):
                # Clear any conversation state
                try:
                    from services.refiloe import RefiloeService
                    refiloe_service = RefiloeService(self.supabase)
                    refiloe_service.clear_conversation_state(phone_number)
                except Exception as e:
                    log_warning(f"Could not clear conversation state: {str(e)}")

                return {
                    'success': True,
                    'message': result['message'],
                    'client_id': result.get('client_id')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Registration failed')
                }

        except Exception as e:
            log_error(f"Error handling client onboarding flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }