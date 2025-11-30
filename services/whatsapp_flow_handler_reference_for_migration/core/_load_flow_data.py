    def _load_flow_data(self) -> Dict:
        """Load the trainer onboarding flow JSON"""
        try:
            # Get the project root directory (go up one level from services)
            project_root = os.path.dirname(os.path.dirname(__file__))
            flow_path = os.path.join(project_root, 'whatsapp_flows', 'trainer_onboarding_flow.json')
            with open(flow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Error loading flow data: {str(e)}")
            return {}