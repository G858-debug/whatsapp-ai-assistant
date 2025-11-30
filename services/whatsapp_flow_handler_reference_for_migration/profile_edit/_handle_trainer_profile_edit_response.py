    def _handle_trainer_profile_edit_response(self, flow_response: Dict, phone_number: str, flow_token: str) -> Dict:
        """Handle trainer profile edit flow response"""
        try:
            # Extract form data from flow response
            update_data = self._extract_profile_edit_data_from_flow_response(flow_response, phone_number, 'trainer')
            
            if not update_data:
                return {
                    'success': False,
                    'error': 'No update data provided'
                }
            
            # Update trainer profile with only the changed fields
            result = self._update_trainer_profile(phone_number, update_data)
            
            if result.get('success'):
                # Send confirmation message
                from app import app
                whatsapp_service = app.config['services']['whatsapp']
                
                updated_fields = list(update_data.keys())
                fields_text = ', '.join(updated_fields)
                
                response = (
                    f"✅ *Profile Updated Successfully!*\n\n"
                    f"Updated fields: {fields_text}\n\n"
                    f"📱 *Next Steps:*\n"
                    f"• Type `/profile` to view your updated profile\n"
                    f"• Continue using Refiloe as normal\n\n"
                    f"Thanks for keeping your profile up to date! 🎉"
                )
                
                whatsapp_service.send_message(phone_number, response)
                
                return {
                    'success': True,
                    'message': 'Trainer profile updated successfully',
                    'updated_fields': updated_fields
                }
            else:
                return result
                
        except Exception as e:
            log_error(f"Error handling trainer profile edit response: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }