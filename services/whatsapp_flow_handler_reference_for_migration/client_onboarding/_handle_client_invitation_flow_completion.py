    def _handle_client_invitation_flow_completion(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle client invitation flow completion (Scenario 1A)"""
        try:
            from datetime import datetime
            import pytz

            sa_tz = pytz.timezone('Africa/Johannesburg')

            # Extract invitation token from flow_token (format: client_invitation_{token}_{timestamp})
            token_parts = flow_token.split('_')
            if len(token_parts) < 3:
                log_error(f"Invalid flow_token format: {flow_token}")
                return {'success': False, 'error': 'Invalid invitation token'}

            invitation_token = token_parts[2]  # Extract the actual invitation token

            # Find invitation in database
            invitation_result = self.supabase.table('client_invitations').select('*').eq(
                'invitation_token', invitation_token
            ).eq('client_phone', phone_number).eq('status', 'pending_client_completion').execute()

            if not invitation_result.data:
                log_error(f"No pending invitation found for token {invitation_token} and phone {phone_number}")
                return {'success': False, 'error': 'Invitation not found or expired'}

            invitation = invitation_result.data[0]

            # Extract trainer_id from invitation FIRST
            trainer_id = invitation.get('trainer_id')

            if not trainer_id:
                log_error(f"Missing trainer_id in invitation: {invitation}")
                return {'success': False, 'error': 'Missing trainer_id'}

            log_info(f"Creating client with trainer_id: {trainer_id}")

            # Extract client data from flow response
            flow_client_data = self._extract_client_data_from_onboarding_response(flow_response, phone_number)

            if not flow_client_data:
                return {'success': False, 'error': 'Failed to extract client data from flow'}

            # Merge prefilled data with flow data
            prefilled_data = invitation.get('prefilled_data', {})
            client_name = prefilled_data.get('name') or flow_client_data.get('name')
            client_email = prefilled_data.get('email') or flow_client_data.get('email')

            # Generate client_id
            from services.auth.authentication_service import AuthenticationService
            auth_service = AuthenticationService(self.supabase)
            client_id = auth_service.generate_unique_id(client_name, 'client')

            # Get trainer info for relationship (query by trainer_id, not id)
            trainer_result = self.supabase.table('trainers').select('trainer_id, name, first_name, last_name, whatsapp').eq(
                'trainer_id', trainer_id
            ).execute()

            if not trainer_result.data:
                log_error(f"Trainer not found for trainer_id {trainer_id}")
                return {'success': False, 'error': 'Trainer not found'}

            trainer = trainer_result.data[0]
            trainer_whatsapp = trainer['whatsapp']
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()

            # Extract and format data from flow response
            flow_data = flow_response.get('response', {})

            # Extract fitness goals and format as comma-separated string
            fitness_goals = flow_data.get('fitness_goals', [])
            if isinstance(fitness_goals, list):
                # Map goal IDs to readable text
                goals_map = {
                    'lose_weight': 'Lose weight',
                    'build_muscle': 'Build muscle',
                    'get_stronger': 'Get stronger',
                    'improve_fitness': 'Improve fitness',
                    'train_for_event': 'Train for event'
                }
                processed_goals = [goals_map.get(goal, goal) for goal in fitness_goals]
                fitness_goals_str = ', '.join(processed_goals)
            else:
                fitness_goals_str = str(fitness_goals)

            # Extract preferred times and format as comma-separated string
            preferred_times = flow_data.get('availability', [])
            if isinstance(preferred_times, list):
                # Map time IDs to readable text
                availability_map = {
                    'early_morning': 'Early morning (5-8am)',
                    'morning': 'Morning (8-12pm)',
                    'afternoon': 'Afternoon (12-5pm)',
                    'evening': 'Evening (5-8pm)',
                    'flexible': 'Flexible'
                }
                processed_times = [availability_map.get(time, time) for time in preferred_times]
                preferred_times_str = ', '.join(processed_times)
            else:
                preferred_times_str = str(preferred_times)

            # Extract other fields
            experience_level = flow_data.get('experience_level', 'beginner')
            health_conditions = flow_data.get('health_conditions', '').strip()
            medications = flow_data.get('medications', '').strip()
            additional_notes = flow_data.get('additional_notes', '').strip()

            # Combine health conditions and medications if both exist
            health_info = health_conditions
            if medications:
                if health_info:
                    health_info += f"\n\nMedications: {medications}"
                else:
                    health_info = f"Medications: {medications}"

            # Get custom pricing from invitation
            custom_price = invitation.get('custom_price_per_session')

            # Create client record with ONLY columns that exist in Supabase schema
            # CRITICAL: trainer_id must be first and converted to string
            client_data = {
                'trainer_id': str(trainer_id),  # CRITICAL: Must be present and first
                'name': client_name,
                'whatsapp': phone_number,
                'status': 'active',
                'fitness_goals': fitness_goals_str,
                'availability': preferred_times_str,
                'experience_level': experience_level,
                'health_conditions': health_info if health_info else None,
                'preferred_training_times': preferred_times_str,
                'connection_status': 'active',
                'requested_by': 'client',
                'additional_notes': additional_notes if additional_notes else None,
                'client_id': client_id,
                'created_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }

            # Add optional fields only if they have values
            if client_email and client_email.strip() and client_email.lower() not in ['skip', 'none']:
                client_data['email'] = client_email

            if custom_price:
                client_data['custom_price_per_session'] = custom_price

            # Log the data being inserted for debugging
            log_info(f"Inserting client with data: trainer_id={trainer_id}, name={client_name}, phone={phone_number}")

            # Insert into clients table
            self.supabase.table('clients').insert(client_data).execute()
            log_info(f"Created client record for {client_id}")

            # Create user entry
            user_data = {
                'phone_number': phone_number,
                'client_id': client_id,
                'login_status': 'client',
                'created_at': datetime.now(sa_tz).isoformat()
            }
            self.supabase.table('users').insert(user_data).execute()
            log_info(f"Created user record for {client_id}")

            # Create trainer-client relationship
            from services.relationships.invitations.invitation_manager import InvitationManager
            from services.relationships.core.relationship_manager import RelationshipManager

            relationship_manager = RelationshipManager(self.supabase)
            invitation_manager = InvitationManager(self.supabase, self.whatsapp_service, relationship_manager)

            # Create relationship with pricing
            success, error_msg = invitation_manager.create_relationship(trainer_id, client_id, 'trainer', invitation_token)

            if success:
                # Approve the relationship immediately (client accepted invitation)
                approve_success, approve_error = relationship_manager.approve_relationship(trainer_id, client_id)

                if approve_success:
                    # Apply custom pricing if specified
                    custom_price = invitation.get('custom_price_per_session')
                    if custom_price:
                        try:
                            # Update pricing in trainer_client_list
                            self.supabase.table('trainer_client_list').update({
                                'pricing_per_session': custom_price,
                                'updated_at': datetime.now(sa_tz).isoformat()
                            }).eq('trainer_id', trainer_id).eq('client_id', client_id).execute()

                            log_info(f"Applied custom pricing R{custom_price} for client {client_id}")
                        except Exception as pricing_error:
                            log_error(f"Failed to apply custom pricing: {str(pricing_error)}")
                else:
                    log_error(f"Failed to approve relationship: {approve_error}")
            else:
                log_error(f"Failed to create relationship: {error_msg}")

            # Update invitation status
            self.supabase.table('client_invitations').update({
                'status': 'accepted',
                'accepted_at': datetime.now(sa_tz).isoformat(),
                'updated_at': datetime.now(sa_tz).isoformat()
            }).eq('id', invitation['id']).execute()

            # Notify client
            client_message = (
                f"✅ *Profile Complete!*\n\n"
                f"Welcome to Refiloe, {client_name}!\n\n"
                f"*Your Client ID:* {client_id}\n"
                f"*Trainer:* {trainer_name}\n"
                f"*Price per session:* R{custom_price if custom_price else 'TBD'}\n\n"
                f"You're now connected with your trainer.\n"
                f"Type /help to see what you can do!"
            )
            self.whatsapp_service.send_message(phone_number, client_message)

            # Notify trainer
            trainer_message = (
                f"✅ *Client Accepted Invitation!*\n\n"
                f"*{client_name}* completed their fitness profile and accepted your invitation!\n\n"
                f"*Client ID:* {client_id}\n"
                f"*Fitness Goals:* {flow_client_data.get('fitness_goals')}\n"
                f"*Experience:* {flow_client_data.get('experience_level')}\n"
                f"*Availability:* {flow_client_data.get('availability')}\n\n"
                f"They're now in your client list. 🎉"
            )
            self.whatsapp_service.send_message(trainer_whatsapp, trainer_message)

            log_info(f"Successfully completed client invitation flow for {client_id}")

            return {
                'success': True,
                'message': 'Client registration and relationship created successfully',
                'client_id': client_id
            }

        except Exception as e:
            log_error(f"Error handling client invitation flow completion: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }