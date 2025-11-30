    def _handle_client_habit_logging_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle client habit logging flow completion"""
        try:
            response_data = flow_data.get('response', {})
            client_id = token_data.get('client_id')
            
            if not client_id:
                return {
                    'success': False,
                    'error': 'No client ID in token data',
                    'message': '❌ Session expired. Please try logging habits again.'
                }
            
            # Get client's active habits to validate against
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            # Get client's previously tracked habits (last 30 days)
            client_habits_data = habits_service.get_client_habits(client_id, days=30)
            
            # Determine which habits this client is allowed to log
            allowed_habits = set()
            if client_habits_data['success'] and client_habits_data['data']:
                for date_data in client_habits_data['data'].values():
                    allowed_habits.update(date_data.keys())
            
            # If no habits found, they haven't been setup yet
            if not allowed_habits:
                return {
                    'success': False,
                    'error': 'No habits setup',
                    'message': (
                        '❌ *No habits setup yet!*\n\n'
                        'You need to setup habit tracking first. Ask your trainer to use `/setup_habits` '
                        'to configure your habits.\n\n'
                        'If you don\'t have a trainer, contact support to get started with habit tracking.'
                    )
                }
            
            # Extract logged habits
            completed_habits = response_data.get('completed_habits', [])
            water_amount = response_data.get('water_amount')
            sleep_hours = response_data.get('sleep_hours')
            steps_count = response_data.get('steps_count')
            weight_kg = response_data.get('weight_kg')
            
            # Validate completed habits against allowed habits
            valid_completed_habits = []
            invalid_habits = []
            
            for habit in completed_habits:
                if habit in allowed_habits:
                    valid_completed_habits.append(habit)
                else:
                    invalid_habits.append(habit)
            
            if invalid_habits:
                log_warning(f"Client {client_id} attempted to log unauthorized habits: {invalid_habits}")
                return {
                    'success': False,
                    'error': 'Unauthorized habits',
                    'message': f'❌ You can only log habits that have been setup for you. Invalid habits: {", ".join(invalid_habits)}'
                }
            
            logged_count = 0
            streaks = {}
            
            # Log boolean habits (completed/not completed)
            for habit in valid_completed_habits:
                result = habits_service.log_habit(client_id, habit, 'completed')
                if result.get('success'):
                    logged_count += 1
                    streaks[habit] = result.get('streak', 0)
            
            # Log measurable habits with specific values (only if allowed)
            measurable_habits = {
                'water_intake': water_amount,
                'sleep_hours': sleep_hours,
                'steps': steps_count,
                'weight': weight_kg
            }
            
            for habit_type, value in measurable_habits.items():
                if value and habit_type in allowed_habits:
                    result = habits_service.log_habit(client_id, habit_type, str(value))
                    if result.get('success'):
                        logged_count += 1
                        streaks[habit_type] = result.get('streak', 0)
                elif value and habit_type not in allowed_habits:
                    log_warning(f"Client {client_id} attempted to log unauthorized measurable habit: {habit_type}")
            
            # If no habits were logged, inform the user
            if logged_count == 0:
                return {
                    'success': False,
                    'error': 'No habits logged',
                    'message': (
                        '❌ *No habits were logged.*\n\n'
                        'This could be because:\n'
                        '• No habits were selected\n'
                        '• The selected habits are not setup for you\n\n'
                        'Please make sure you have habits setup and try again.'
                    )
                }
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Generate success message with streaks
            message = f"🎉 *Habits Logged Successfully!*\n\n"
            message += f"✅ {logged_count} habits recorded for today\n\n"
            
            if streaks:
                message += "*🔥 Current Streaks:*\n"
                for habit, streak in sorted(streaks.items(), key=lambda x: x[1], reverse=True):
                    habit_name = habit.replace('_', ' ').title()
                    fire_emoji = '🔥' * min(streak // 3, 5)
                    message += f"• {habit_name}: {streak} days {fire_emoji}\n"
                message += "\n"
            
            message += "💪 *Keep up the amazing work! Consistency is key to success!*"
            
            return {
                'success': True,
                'message': message,
                'habits_logged': logged_count,
                'streaks': streaks
            }
            
        except Exception as e:
            log_error(f"Error handling client habit logging response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error logging habits. Please try again.'
            }