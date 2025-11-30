    def _add_client_directly(self, trainer_id: str, client_data: Dict) -> Dict:
        """Add client directly without invitation"""
        try:
            # Create client record
            new_client_data = {
                'trainer_id': trainer_id,
                'name': client_data['name'],
                'whatsapp': client_data['phone'],
                'email': client_data.get('email'),
                'status': 'active',
                'package_type': 'single',
                'sessions_remaining': 1,
                'experience_level': 'Beginner',  # Default
                'health_conditions': 'None specified',  # Default
                'fitness_goals': 'General fitness',  # Default
                'preferred_training_times': 'Flexible',  # Default
                'connection_status': 'active',
                'requested_by': 'trainer',
                'approved_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # Add custom pricing if provided
            # Use calculated_price as primary, fall back to custom_price for backward compatibility
            client_price = client_data.get('calculated_price') or client_data.get('custom_price')
            if client_price:
                new_client_data['custom_price_per_session'] = client_price
            
            client_result = self.supabase.table('clients').insert(new_client_data).execute()
            
            if not client_result.data:
                return {
                    'success': False,
                    'error': 'Failed to create client record'
                }
            
            client_id = client_result.data[0]['id']
            
            # Send welcome message to client
            welcome_message = f"""🌟 *Welcome to your fitness journey!*

Hi {client_data['name']}!

You've been added as a client! I'm Refiloe, your AI fitness assistant.

I'm here to help you:
• Book training sessions
• Track your progress  
• Stay motivated
• Connect with your trainer

Ready to get started? Just say 'Hi' anytime! 💪"""
            
            # Send welcome message (don't fail if this doesn't work)
            try:
                self.whatsapp_service.send_message(client_data['phone'], welcome_message)
            except Exception as e:
                log_warning(f"Could not send welcome message to client: {str(e)}")
            
            return {
                'success': True,
                'message': f"🎉 *Client Added Successfully!*\n\n✅ {client_data['name']} has been added to your client list!\n📱 Phone: {client_data['phone']}\n\nThey can now book sessions and track progress with you!",
                'client_id': client_id
            }
            
        except Exception as e:
            log_error(f"Error adding client directly: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }