    def _create_client_onboarding_flow_message(self, phone_number: str) -> Optional[Dict]:
        """Create WhatsApp flow message for client onboarding"""
        try:
            import json
            import os
            
            # Load the client onboarding flow JSON
            project_root = os.path.dirname(os.path.dirname(__file__))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'client_onboarding_flow.json')
            
            if not os.path.exists(flow_path):
                log_error(f"Client onboarding flow file not found: {flow_path}")
                return None
            
            with open(flow_path, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            
            # Generate flow token
            flow_token = f"client_onboarding_{phone_number}_{int(datetime.now().timestamp())}"
            
            # Create flow message
            message = {
                "recipient_type": "individual",
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Welcome to Refiloe!"
                    },
                    "body": {
                        "text": "Let's get you set up to find the perfect trainer! 🏃‍♀️"
                    },
                    "footer": {
                        "text": "Powered by Refiloe AI"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": Config.CLIENT_ONBOARDING_FLOW_ID,  # Actual client onboarding flow ID
                            "flow_cta": "Get Started",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "WELCOME"
                            }
                        }
                    }
                }
            }
            
            return message
            
        except Exception as e:
            log_error(f"Error creating client onboarding flow message: {str(e)}")
            return None