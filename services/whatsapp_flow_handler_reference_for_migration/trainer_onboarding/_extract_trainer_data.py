    def _extract_trainer_data(self, action_payload: Dict) -> Dict:
        """Legacy method - kept for backward compatibility"""
        return self._extract_trainer_data_from_flow(action_payload)