    def _store_flow_token_with_data(self, phone_number: str, flow_token: str, flow_type: str, flow_data: Dict) -> bool:
        """Store flow token data for later retrieval"""
        try:
            result = self.supabase.table('flow_tokens').insert({
                'phone_number': phone_number,
                'flow_token': flow_token,
                'flow_type': flow_type,
                'flow_data': flow_data,
                'created_at': datetime.now().isoformat()
            }).execute()

            return bool(result.data)

        except Exception as e:
            log_error(f"Error storing flow token: {str(e)}")
            return False