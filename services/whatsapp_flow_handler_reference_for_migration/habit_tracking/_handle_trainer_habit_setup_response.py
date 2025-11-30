    def _handle_trainer_habit_setup_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle trainer habit setup flow completion"""
        try:
            response_data = flow_data.get('response', {})
            trainer_id = token_data.get('trainer_id')
            
            # Extract form data
            selected_client = response_data.get('selected_client')
            selected_habits = response_data.get('selected_habits', [])
            goals = response_data.get('goals', {})
            reminder_time = response_data.get('reminder_time')
            
            if not selected_client or not selected_habits:
                return {
                    'success': False,
                    'error': 'Missing required data',
                    'message': '❌ Please select a client and at least one habit to track.'
                }
            
            # SECURITY: Validate that the selected client belongs to this trainer
            client_validation = self.supabase.table('clients').select('id, name, trainer_id').eq(
                'id', selected_client
            ).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            if not client_validation.data:
                log_error(f"Trainer {trainer_id} attempted to setup habits for unauthorized client {selected_client}")
                return {
                    'success': False,
                    'error': 'Unauthorized client access',
                    'message': '❌ You can only setup habits for your own clients. Please select a valid client.'
                }
            
            client_data = client_validation.data[0]
            
            # Validate selected habits against allowed habit types
            from services.habits import HabitTrackingService
            habits_service = HabitTrackingService(self.supabase)
            
            valid_habits = []
            invalid_habits = []
            
            for habit in selected_habits:
                if habit in habits_service.habit_types:
                    valid_habits.append(habit)
                else:
                    invalid_habits.append(habit)
            
            if invalid_habits:
                log_warning(f"Invalid habits selected: {invalid_habits}")
                return {
                    'success': False,
                    'error': 'Invalid habits selected',
                    'message': f'❌ Invalid habits detected: {", ".join(invalid_habits)}. Please select only valid habit types.'
                }
            
            if not valid_habits:
                return {
                    'success': False,
                    'error': 'No valid habits selected',
                    'message': '❌ No valid habits selected. Please choose at least one habit to track.'
                }
            
            # Setup habits for the client using validated habits
            success_count = 0
            for habit in valid_habits:
                # Initialize habit tracking for this client
                result = habits_service.log_habit(
                    client_data['id'], 
                    habit, 
                    'initialized',
                    datetime.now().date().isoformat()
                )
                if result.get('success'):
                    success_count += 1
                
                # Set goals if provided
                goal_value = goals.get(habit.replace('_', ''))
                if goal_value:
                    habits_service.set_habit_goal(
                        client_data['id'],
                        habit,
                        goal_value,
                        'daily'
                    )
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Send success message with detailed info
            habit_names = [habit.replace('_', ' ').title() for habit in valid_habits]
            
            message = (
                f"🎉 *Habit Tracking Setup Complete!*\n\n"
                f"✅ Client: {client_data['name']}\n"
                f"📊 Habits activated: {len(valid_habits)}\n"
                f"🎯 Habits: {', '.join(habit_names)}\n\n"
                f"Your client can now:\n"
                f"• Use `/log_habit` to log daily habits\n"
                f"• Use `/habit_streak` to check streaks\n"
                f"• Simply tell me what they did (e.g., 'drank 2L water')\n\n"
                f"Track their progress anytime with `/habits`!"
            )
            
            return {
                'success': True,
                'message': message,
                'client_id': client_data['id'],
                'habits_setup': success_count
            }
            
        except Exception as e:
            log_error(f"Error handling trainer habit setup response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error setting up habits. Please try again.'
            }