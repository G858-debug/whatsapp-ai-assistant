    def _store_flow_token(self, phone_number: str, flow_token: str):
        """Store flow token for tracking"""
        try:
            self.supabase.table('flow_tokens').insert({
                'phone_number': phone_number,
                'flow_token': flow_token,
                'flow_type': 'trainer_onboarding',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            log_warning(f"Failed to store flow token: {str(e)}")