    def _handle_trainer_add_client_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer add client flow response"""
        try:
            log_info(f"Processing trainer add client flow response for {phone_number}")
            log_info(f"Flow token: {flow_token}")
            log_info(f"Flow response type: {type(flow_response)}")
            log_info(f"Flow response keys: {list(flow_response.keys())}")
            log_info(f"Full flow response: {json.dumps(flow_response, indent=2)}")

            # Extract client data - handle both direct data and nested response_json format
            if 'client_name' in flow_response or 'client_phone' in flow_response:
                # Data is already at the top level (from flow_response_handler)
                client_data = self._extract_client_data_from_flow_response(flow_response, phone_number)
            elif 'response_json' in flow_response:
                # Data is nested in response_json (legacy format)
                response_json = flow_response.get('response_json', '{}')
                if isinstance(response_json, str):
                    parsed_data = json.loads(response_json)
                else:
                    parsed_data = response_json
                client_data = self._extract_client_data_from_flow_response(parsed_data, phone_number)
            else:
                # Try to extract from whatever structure we have
                client_data = self._extract_client_data_from_flow_response(flow_response, phone_number)

            if not client_data:
                log_error("Failed to extract client data from flow response")
                log_error(f"Flow response was: {json.dumps(flow_response, indent=2)}")
                return {
                    'success': False,
                    'error': 'Failed to extract client data from flow response'
                }

            log_info(f"Extracted client data: {json.dumps(client_data, indent=2)}")
            
            # Validate trainer exists
            trainer_result = self.supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
            if not trainer_result.data:
                return {
                    'success': False,
                    'error': 'Trainer not found'
                }
            
            trainer = trainer_result.data[0]
            trainer_id = trainer['id']
            
            # Check subscription limits
            try:
                from services.subscription_manager import SubscriptionManager
                subscription_manager = SubscriptionManager(self.supabase)
                
                if not subscription_manager.can_add_client(trainer_id):
                    limits = subscription_manager.get_client_limits(trainer_id)
                    return {
                        'success': False,
                        'error': f"You've reached your client limit of {limits.get('max_clients', 'unknown')} clients. Please upgrade your subscription."
                    }
            except Exception as e:
                log_warning(f"Could not check subscription limits: {str(e)}")
            
            # Validate phone number
            from utils.validators import Validators
            validator = Validators()
            is_valid, formatted_phone, error = validator.validate_phone_number(client_data['phone'])
            
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Invalid phone number: {error}"
                }
            
            client_data['phone'] = formatted_phone
            
            # Check for duplicate client
            existing_client = self.supabase.table('clients').select('*').eq('trainer_id', trainer_id).eq('whatsapp', formatted_phone).execute()
            if existing_client.data:
                return {
                    'success': False,
                    'error': f"You already have a client with phone number {formatted_phone}"
                }
            
            # Process based on invitation method
            invitation_method = client_data.get('invitation_method', 'manual_add')
            
            if invitation_method == 'whatsapp_invite':
                # Create invitation and send WhatsApp message
                result = self._create_and_send_invitation(trainer_id, client_data)
            else:
                # Add client directly
                result = self._add_client_directly(trainer_id, client_data)
            
            if result.get('success'):
                # Handle package deal clarification if needed
                if client_data.get('has_package_deal') and client_data.get('package_details'):
                    needs_clarification = self._check_package_needs_clarification(client_data['package_details'])

                    if needs_clarification:
                        # Set conversation state for package clarification
                        try:
                            from services.refiloe import RefiloeService
                            refiloe_service = RefiloeService(self.supabase)

                            clarification_context = {
                                'client_name': client_data['name'],
                                'client_phone': client_data['phone'],
                                'trainer_id': trainer_id,
                                'package_details_raw': client_data['package_details'],
                                'invitation_method': client_data['invitation_method']
                            }

                            refiloe_service.update_conversation_state(
                                phone_number,
                                'PACKAGE_DEAL_CLARIFICATION',
                                clarification_context
                            )

                            # Append clarification request to result message
                            clarification_msg = "\n\n📦 *Package Deal Details*\n\nI need a bit more information about the package deal. Please tell me:\n\n• How many sessions are included?\n• What's the total package price?\n• What's the package duration (e.g., 1 month, 3 months)?"

                            result['message'] = result.get('message', '') + clarification_msg

                        except Exception as e:
                            log_warning(f"Could not set package clarification state: {str(e)}")
                    else:
                        # Clear conversation state if no clarification needed
                        try:
                            from services.refiloe import RefiloeService
                            refiloe_service = RefiloeService(self.supabase)
                            refiloe_service.clear_conversation_state(phone_number)
                        except Exception as e:
                            log_warning(f"Could not clear conversation state: {str(e)}")
                else:
                    # Clear any conversation state
                    try:
                        from services.refiloe import RefiloeService
                        refiloe_service = RefiloeService(self.supabase)
                        refiloe_service.clear_conversation_state(phone_number)
                    except Exception as e:
                        log_warning(f"Could not clear conversation state: {str(e)}")

                return result
            else:
                return result
                
        except Exception as e:
            log_error(f"Error handling trainer add client flow response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }