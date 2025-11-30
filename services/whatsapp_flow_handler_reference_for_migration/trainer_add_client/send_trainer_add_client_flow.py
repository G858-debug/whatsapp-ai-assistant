    def send_trainer_add_client_flow(
        self,
        trainer_phone: str,
        trainer_id: str = None,
        client_name: str = None,
        client_phone: str = None,
        client_email: str = None
    ) -> Dict:
        """
        Send trainer add client flow with dynamic pricing and optional pre-filled client data.
        Passes trainer's default_price_per_session and client contact data as initial flow data.

        Args:
            trainer_phone: Trainer's WhatsApp number
            trainer_id: Optional trainer ID (will lookup if not provided)
            client_name: Optional client name to pre-populate in the flow
            client_phone: Optional client phone to pre-populate in the flow
            client_email: Optional client email to pre-populate in the flow

        Returns:
            Dict with success status and flow_token or error details
        """
        try:
            log_info(f"Sending trainer add client flow to {trainer_phone}")

            # Get trainer data if not provided
            if not trainer_id:
                trainer_result = self.supabase.table('trainers').select('id, default_price_per_session, name').eq(
                    'whatsapp', trainer_phone
                ).execute()

                if not trainer_result.data:
                    return {
                        'success': False,
                        'error': 'Trainer not found'
                    }

                trainer = trainer_result.data[0]
                trainer_id = trainer['id']
                log_info(f"Fetched trainer data: {trainer}")
            else:
                # Fetch trainer data using ID
                trainer_result = self.supabase.table('trainers').select('id, default_price_per_session, name').eq(
                    'id', trainer_id
                ).execute()

                if not trainer_result.data:
                    return {
                        'success': False,
                        'error': 'Trainer not found'
                    }

                trainer = trainer_result.data[0]
                log_info(f"Fetched trainer data: {trainer}")

            # Get trainer's default price (default to R500 if not set)
            trainer_default_price = trainer.get('default_price_per_session', 500)

            # Handle None or 0 values
            if not trainer_default_price or trainer_default_price == 0:
                trainer_default_price = 500
                log_warning(f"Trainer {trainer_id} has no default price set, using R500")

            log_info(f"Trainer default price: R{trainer_default_price}")
            log_info(f"Calculated trainer_default_price: {trainer_default_price}")

            # Generate flow token
            flow_token = f"trainer_add_client_{trainer_phone}_{int(datetime.now().timestamp())}"

            # CRITICAL: Pass trainer_default_price as initial flow data
            # This data cascades through all screens in the flow
            flow_action_payload = {
                "screen": "WELCOME",
                "data": {
                    "trainer_default_price": f"R{int(trainer_default_price)}",  # Format with R prefix as per Flow JSON schema
                    "client_name": client_name or "",
                    "client_phone": client_phone or "",
                    "client_email": client_email or ""
                }
            }

            flow_message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": trainer_phone,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Add new client"
                    },
                    "body": {
                        "text": "Populate " + (client_name if client_name else "your client") + "'s details to create their profile. They'll receive an invitation to review and accept."
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": Config.TRAINER_ADD_CLIENT_FLOW_ID,
                            "flow_cta": "Start",
                            "flow_action": "navigate",
                            "flow_action_payload": flow_action_payload
                        }
                    }
                }
            }

            # Store flow token for tracking
            self._store_flow_token_with_data(
                phone_number=trainer_phone,
                flow_token=flow_token,
                flow_type='trainer_onboarding',
                flow_data={
                    'type': 'trainer_add_client',
                    'trainer_id': trainer_id,
                    'trainer_phone': trainer_phone,
                    'trainer_default_price': trainer_default_price,
                    'client_name': client_name,
                    'client_phone': client_phone,
                    'client_email': client_email
                }
            )

            log_info(f"Sending flow with payload: {flow_action_payload}")

            # Send the flow
            result = self.whatsapp_service.send_flow_message(flow_message)

            if result.get('success'):
                log_info(f"Trainer add client flow sent to {trainer_phone}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token,
                    'message': "Flow sent!"
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }

        except Exception as e:
            log_error(f"Error sending trainer add client flow: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }