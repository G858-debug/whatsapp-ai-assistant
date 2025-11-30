    def send_trainer_habit_setup_flow(self, phone_number: str, trainer_data: dict) -> Dict:
        """Send trainer habit setup flow"""
        try:
            # Get trainer's clients for the flow with additional info
            clients_result = self.supabase.table('clients').select('id, name, whatsapp, created_at').eq(
                'trainer_id', trainer_data['id']
            ).eq('status', 'active').order('name').execute()
            
            if not clients_result.data:
                return {
                    'success': False,
                    'error': 'No active clients found',
                    'message': 'You need to add clients first before setting up habits. Use `/add_client` to get started!'
                }
            
            # Check which clients already have habits setup
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Prepare client data for flow with habit status
            clients_for_flow = []
            for client in clients_result.data:
                # Check if client has any habits
                client_habits = habits_service.get_client_habits(client['id'], days=30)
                has_habits = client_habits['success'] and client_habits.get('days_tracked', 0) > 0
                
                # Format client display with status
                status_emoji = "✅" if has_habits else "🆕"
                status_text = "Has habits" if has_habits else "New setup"
                
                clients_for_flow.append({
                    "id": client['id'], 
                    "title": f"{status_emoji} {client['name']} ({status_text})",
                    "description": f"Phone: {client.get('whatsapp', 'N/A')}"
                })
            
            # Limit to 10 clients for better UX
            if len(clients_for_flow) > 10:
                clients_for_flow = clients_for_flow[:10]
            
            # Create flow message with client data
            flow_token = f"habit_setup_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "🎯 Setup Client Habits"
                    },
                    "body": {
                        "text": "Help your clients build lasting healthy habits! Choose which habits to track and set personalized goals."
                    },
                    "footer": {
                        "text": "Habit tracking setup"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "trainer_habit_setup_flow",
                            "flow_cta": "Setup Habits",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "clients": clients_for_flow
                                }
                            }
                        }
                    }
                }
            }
            
            # Store flow token
            self._store_flow_token_with_data(
                phone_number=phone_number,
                flow_token=flow_token,
                flow_type='assessment_flow',
                flow_data={
                    'type': 'trainer_habit_setup',
                    'trainer_id': trainer_data['id'],
                    'phone': phone_number,
                    'clients': clients_result.data
                }
            )
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Trainer habit setup flow sent to {phone_number}")
                return {
                    'success': True,
                    'method': 'whatsapp_flow',
                    'flow_token': flow_token
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send flow',
                    'details': result
                }
                
        except Exception as e:
            log_error(f"Error sending trainer habit setup flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }