    def __init__(self, supabase_client, whatsapp_service):
        self.supabase = supabase_client
        self.whatsapp_service = whatsapp_service
        self.flow_data = self._load_flow_data()