    def _create_and_send_invitation(self, trainer_id: str, client_data: Dict) -> Dict:
        """
        Create invitation and send WhatsApp message to client.
        For trainer-filled profiles, stores ALL trainer-provided data in JSONB.
        """
        try:
            import uuid

            # Generate invitation token
            invitation_token = str(uuid.uuid4())

            # Prepare trainer_provided_data JSONB with ALL client information
            trainer_provided_data = {
                'name': client_data['name'],
                'email': client_data.get('email'),
                'fitness_goals': client_data.get('fitness_goals', []),
                'specific_goals': client_data.get('specific_goals'),
                'experience_level': client_data.get('experience_level'),
                'sessions_per_week': client_data.get('sessions_per_week'),
                'preferred_times': client_data.get('preferred_times', []),
                'health_conditions': client_data.get('health_conditions'),
                'medications': client_data.get('medications'),
                'additional_notes': client_data.get('additional_notes'),
                'pricing_choice': client_data.get('pricing_choice'),
                'calculated_price': client_data.get('calculated_price'),  # Store the calculated price
                'custom_price': client_data.get('custom_price'),  # Keep for backward compatibility
                'has_package_deal': client_data.get('has_package_deal', False),
                'package_deal_details': client_data.get('package_deal_details')
            }

            # Create invitation record with comprehensive data
            # Use calculated_price as the primary price field, fall back to custom_price for backward compatibility
            client_price = client_data.get('calculated_price') or client_data.get('custom_price')

            invitation_data = {
                'trainer_id': trainer_id,
                'client_phone': client_data['phone'],
                'client_name': client_data['name'],
                'client_email': client_data.get('email'),
                'invitation_token': invitation_token,
                'invitation_method': 'type_details',  # Use allowed value: 'type_details' for WhatsApp Flow
                'status': 'pending_client_acceptance',  # Special status for trainer-filled profiles
                'profile_completion_method': 'trainer_fills',  # Track that trainer filled the profile
                'trainer_provided_data': trainer_provided_data,  # JSONB with all data (includes pricing_choice, etc.)
                'custom_price': client_price,  # Store calculated_price or custom_price
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # If there's package deal info, store it separately in the package_deal field
            if client_data.get('has_package_deal') and client_data.get('package_deal_details'):
                invitation_data['package_deal'] = client_data.get('package_deal_details')
            
            invitation_result = self.supabase.table('client_invitations').insert(invitation_data).execute()
            
            if not invitation_result.data:
                return {
                    'success': False,
                    'error': 'Failed to create invitation record'
                }
            
            # Get trainer info for personalized message
            trainer_result = self.supabase.table('trainers').select('name, business_name, default_price_per_session').eq('id', trainer_id).execute()
            trainer_name = 'Your trainer'
            business_name = 'their training program'
            trainer_default_price = None

            if trainer_result.data:
                trainer_info = trainer_result.data[0]
                trainer_name = trainer_info.get('name', 'Your trainer')
                business_name = trainer_info.get('business_name') or f"{trainer_name}'s training program"
                trainer_default_price = trainer_info.get('default_price_per_session')

            # Create trainer-filled profile invitation message (different from regular invitation)
            invitation_message = f"""🎯 *Training Profile Created*

Hi {client_data['name']}! 👋

{trainer_name} has created a fitness profile for you and invited you to train together!

📋 *Your Pre-filled Profile:*
• Name: {client_data['name']}"""

            # Add optional contact info
            if client_data.get('email'):
                invitation_message += f"\n• Email: {client_data['email']}"

            # Add fitness information
            if client_data.get('fitness_goals'):
                goals_str = ', '.join(client_data['fitness_goals']) if isinstance(client_data['fitness_goals'], list) else client_data['fitness_goals']
                invitation_message += f"\n• Goals: {goals_str}"

            if client_data.get('experience_level'):
                invitation_message += f"\n• Experience: {client_data['experience_level']}"

            if client_data.get('sessions_per_week'):
                invitation_message += f"\n• Sessions/week: {client_data['sessions_per_week']}"

            # Add pricing information
            # Use calculated_price (or custom_price for backward compatibility)
            client_price = client_data.get('calculated_price') or client_data.get('custom_price')

            if client_price:
                invitation_message += f"\n• Price: R{client_price:.0f} per session"
            elif trainer_default_price:
                invitation_message += f"\n• Price: R{trainer_default_price:.0f} per session"

            # Add package deal if applicable
            if client_data.get('has_package_deal') and client_data.get('package_deal_details'):
                invitation_message += f"\n• Package Deal: {client_data['package_deal_details']}"

            invitation_message += f"""

👨‍🏫 *Your Trainer:*
• {trainer_name}
• {business_name}

✅ *Review and Accept*

Please review the information above. If everything looks good, reply 'ACCEPT' to start training!

You can also reply 'CHANGES' if you need to update any information.

This invitation expires in 7 days.

Reply 'ACCEPT' to get started! 🚀"""

            # Send invitation message
            send_result = self.whatsapp_service.send_message(client_data['phone'], invitation_message)
            
            if send_result.get('success', True):
                return {
                    'success': True,
                    'message': f"✅ Invitation sent to {client_data['name']}! I'll notify you when they respond.",
                    'invitation_token': invitation_token
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to send invitation message: {send_result.get('error')}"
                }
                
        except Exception as e:
            log_error(f"Error creating and sending invitation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }