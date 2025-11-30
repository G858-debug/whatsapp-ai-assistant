    def _handle_habit_progress_response(self, flow_data: Dict, token_data: Dict) -> Dict:
        """Handle habit progress flow completion"""
        try:
            response_data = flow_data.get('response', {})
            selected_action = response_data.get('selected_action')
            
            # Clean up flow token
            self._cleanup_flow_token(flow_data.get('flow_token'))
            
            # Handle the selected action
            if selected_action == 'log_today':
                message = (
                    "📝 *Ready to log today's habits!*\n\n"
                    "Use `/log_habit` to start logging, or just tell me what you did:\n\n"
                    "Examples:\n"
                    "• 'drank 2 liters water'\n"
                    "• 'slept 8 hours'\n"
                    "• 'workout completed'\n"
                    "• 'walked 10000 steps'"
                )
            elif selected_action == 'set_goals':
                message = (
                    "🎯 *Goal Setting*\n\n"
                    "Goal management is coming soon! For now, focus on building consistency.\n\n"
                    "Remember: Small daily actions lead to big results! 💪"
                )
            elif selected_action == 'view_streaks':
                message = (
                    "🔥 *Check Your Streaks*\n\n"
                    "Use `/habit_streak` to see all your current streaks and get motivated!"
                )
            elif selected_action == 'get_tips':
                message = (
                    "💡 *Habit Building Tips*\n\n"
                    "🎯 Start small - even 1% better each day adds up\n"
                    "🔗 Stack habits - link new habits to existing ones\n"
                    "📅 Be consistent - same time, same place\n"
                    "🎉 Celebrate wins - acknowledge your progress\n"
                    "💪 Focus on identity - 'I am someone who...'\n\n"
                    "You've got this! Keep building those healthy habits! 🌟"
                )
            else:
                message = "Thanks for checking your progress! Keep up the great work! 💪"
            
            return {
                'success': True,
                'message': message,
                'action': selected_action
            }
            
        except Exception as e:
            log_error(f"Error handling habit progress response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '❌ Error processing your request. Please try again.'
            }