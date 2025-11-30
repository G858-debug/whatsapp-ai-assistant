    def send_habit_progress_flow(self, phone_number: str, client_data: dict) -> Dict:
        """Send habit progress flow"""
        try:
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Get current streaks
            streaks = {}
            for habit_type in ['water_intake', 'sleep_hours', 'steps', 'workout_completed']:
                streak = habits_service.calculate_streak(client_data['id'], habit_type)
                streaks[habit_type.replace('_', '')] = streak
            
            # Create flow message with current data
            flow_token = f"habit_progress_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "📊 Your Progress"
                    },
                    "body": {
                        "text": "Check out your habit progress and get personalized insights!"
                    },
                    "footer": {
                        "text": "Progress tracking"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "habit_progress_flow",
                            "flow_cta": "View Progress",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "overview",
                                "data": {
                                    "streaks": streaks
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
                    'type': 'habit_progress',
                    'client_id': client_data['id'],
                    'phone': phone_number
                }
            )
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Habit progress flow sent to {phone_number}")
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
            log_error(f"Error sending habit progress flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }