"""
 Handle Package Clarification
Handle trainer's response to package deal clarification request
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_package_clarification(self, phone: str, message: str, context: Dict) -> Dict:
    """Handle trainer's response to package deal clarification request"""
    try:
        import re
        from services.openai_service import OpenAIService

        # Use AI to extract structured package information
        openai_service = OpenAIService()

        prompt = f"""Extract package deal information from the following text. The text describes a fitness training package deal.

Text: "{message}"

Previous context: "{context.get('package_details_raw', 'N/A')}"

Extract and return ONLY a JSON object with these fields:
- sessions: number of sessions (integer)
- price: total package price in Rands (integer)
- duration: package duration (e.g., "1 month", "3 months", "8 weeks")

If you cannot determine a value, use null. Return ONLY valid JSON, no other text."""

        ai_response = openai_service.get_completion(prompt, model="gpt-4")

        # Parse AI response
        try:
            import json
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                package_info = json.loads(json_match.group())
            else:
                package_info = json.loads(ai_response)

            # Validate extracted data
            if not package_info.get('sessions') or not package_info.get('price'):
                return {
                    'success': False,
                    'message': "I couldn't extract all the package details. Please provide:\n\n• Number of sessions\n• Total package price\n• Duration (optional)\n\nFor example: '10 sessions for R4500 over 2 months'"
                }

        except (json.JSONDecodeError, AttributeError) as e:
            log_warning(f"Failed to parse AI response for package clarification: {str(e)}")
            return {
                'success': False,
                'message': "I couldn't understand the package details. Please provide them in this format:\n\n'[Number] sessions for R[Price] over [Duration]'\n\nFor example: '10 sessions for R4500 over 2 months'"
            }

        # Update invitation or client record with structured package info
        client_phone = context.get('client_phone')
        trainer_id = context.get('trainer_id')

        # Try to find invitation first
        invitation_result = self.db.table('client_invitations').select('*').eq(
            'trainer_id', trainer_id
        ).eq('client_phone', client_phone).eq('status', 'pending').execute()

        if invitation_result.data:
            # Update invitation with structured package info
            self.db.table('client_invitations').update({
                'package_info': package_info
            }).eq('id', invitation_result.data[0]['id']).execute()
        else:
            # Update client record if already added
            client_result = self.db.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).eq('whatsapp', client_phone).execute()

            if client_result.data:
                self.db.table('clients').update({
                    'package_info': package_info,
                    'package_type': 'package',
                    'sessions_remaining': package_info.get('sessions', 1)
                }).eq('id', client_result.data[0]['id']).execute()

        success_msg = f"""✅ *Package Deal Confirmed!*

📦 **Package Details:**
• Sessions: {package_info.get('sessions')} sessions
• Total Price: R{package_info.get('price')}"""

        if package_info.get('duration'):
            success_msg += f"\n• Duration: {package_info.get('duration')}"

        success_msg += f"\n• Price per session: R{package_info.get('price') // package_info.get('sessions', 1)}"
        success_msg += f"\n\n✨ All set! Your client {context.get('client_name')} is ready to go!"

        return {
            'success': True,
            'message': success_msg
        }

    except Exception as e:
        log_error(f"Error handling package clarification: {str(e)}")
        return {
            'success': False,
            'message': "❌ Sorry, there was an error processing your package details. Please contact support."
        }
