    def send_client_habit_logging_flow(self, phone_number: str, client_data: dict) -> Dict:
        """Send client habit logging flow"""
        try:
            # Get client's active habits
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Check what habits they've been tracking (last 30 days for better detection)
            habits_data = habits_service.get_client_habits(client_data['id'], days=30)
            
            # Determine active habits (habits they've logged in the past 30 days)
            active_habits = []
            if habits_data['success'] and habits_data['data']:
                tracked_habits = set()
                for date_data in habits_data['data'].values():
                    tracked_habits.update(date_data.keys())
                
                # Only include valid habit types
                valid_habits = habits_service.habit_types
                tracked_habits = tracked_habits.intersection(set(valid_habits))
                
                habit_display_names = {
                    'water_intake': '💧 Water Intake',
                    'sleep_hours': '😴 Sleep Hours',
                    'steps': '🚶 Daily Steps',
                    'workout_completed': '💪 Workout',
                    'weight': '⚖️ Weight',
                    'meals_logged': '🍽️ Meals',
                    'calories': '🔥 Calories',
                    'mood': '😊 Mood'
                }
                
                # Get current streaks for each habit to show in title
                for habit in tracked_habits:
                    streak = habits_service.calculate_streak(client_data['id'], habit)
                    streak_text = f" (🔥{streak})" if streak > 0 else ""
                    
                    active_habits.append({
                        "id": habit, 
                        "title": f"{habit_display_names.get(habit, habit.replace('_', ' ').title())}{streak_text}",
                        "description": f"Current streak: {streak} days" if streak > 0 else "No current streak"
                    })
            
            # If no active habits found, they need to set up habits first
            if not active_habits:
                return {
                    'success': False,
                    'error': 'No habits setup',
                    'message': (
                        "🎯 *No habits setup yet!*\n\n"
                        "You need to setup habit tracking first. Ask your trainer to use `/setup_habits` "
                        "to configure your habits, or if you don't have a trainer, you can start with basic habits.\n\n"
                        "Would you like me to help you get started with habit tracking?"
                    )
                }
            
            # Create flow message
            flow_token = f"habit_log_{phone_number}_{int(datetime.now().timestamp())}"
            
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "📝 Daily Check-in"
                    },
                    "body": {
                        "text": "Time for your daily habit check-in! Let's track your progress and keep those streaks going! 🔥"
                    },
                    "footer": {
                        "text": "Habit logging"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_name": "client_habit_logging_flow",
                            "flow_cta": "Log Habits",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "welcome",
                                "data": {
                                    "active_habits": active_habits
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
                    'type': 'client_habit_logging',
                    'client_id': client_data['id'],
                    'phone': phone_number,
                    'active_habits': active_habits
                }
            )
            
            # Send the flow
            result = self.whatsapp_service.send_flow_message(message)

            if result.get('success'):
                log_info(f"Client habit logging flow sent to {phone_number}")
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
            log_error(f"Error sending client habit logging flow: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }