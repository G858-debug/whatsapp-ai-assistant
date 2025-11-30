"""
 Create Client Addition Flow Message
Create WhatsApp flow message for client addition
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _create_client_addition_flow_message(self, phone: str) -> Optional[Dict]:
    """Create WhatsApp flow message for client addition"""
    try:
        import json
        import os
        from datetime import datetime

        # Get trainer data to pass pricing info
        trainer_result = self.supabase.table('trainers').select('*').eq('whatsapp', phone).execute()
        if not trainer_result.data:
            log_error(f"Trainer not found for phone: {phone}")
            return None

        trainer = trainer_result.data[0]
        trainer_price = trainer.get('pricing_per_session', 500)  # Default to 500 if not set

        # Load the client addition flow JSON
        project_root = os.path.dirname(os.path.dirname(__file__))
        flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_add_client_flow.json')

        if not os.path.exists(flow_path):
            log_error(f"Client addition flow file not found: {flow_path}")
            return None

        with open(flow_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)

        # Generate flow token
        flow_token = f"add_client_{phone}_{int(datetime.now().timestamp())}"

        # Create flow message with dynamic data
        message = {
            "recipient_type": "individual",
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "header": {
                    "type": "text",
                    "text": "Add new client"
                },
                "body": {
                    "text": "Let's add a new client to your training program! 👥"
                },
                "footer": {
                    "text": "Powered by Refiloe AI"
                },
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": flow_token,
                        "flow_id": "TRAINER_ADD_CLIENT_FLOW",  # This should match your Facebook Console flow ID
                        "flow_cta": "Add Client",
                        "flow_action": "navigate",
                        "flow_action_payload": {
                            "screen": "WELCOME",
                            "data": {
                                "trainer_price": str(trainer_price)
                            }
                        }
                    }
                }
            }
        }

        return message

    except Exception as e:
        log_error(f"Error creating client addition flow message: {str(e)}")
        return None
