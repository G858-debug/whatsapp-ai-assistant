WHATSAPP_TEMPLATES = {
    "client_training_invitation": {
        "name": "client_training_invitation",
        "language": "en",
        "category": "UTILITY",
        "variables": {
            "body": [
                {"position": 1, "type": "text", "description": "client_name"},
                {"position": 2, "type": "text", "description": "trainer_name"},
                {"position": 3, "type": "text", "description": "currency_symbol"},
                {"position": 4, "type": "text", "description": "price_amount"}
            ]
        },
        "buttons": [
            {"type": "QUICK_REPLY", "text": "✅ Accept invitation"},
            {"type": "QUICK_REPLY", "text": "❌ Decline"}
        ]
    }
}

def get_template_config(template_name: str) -> dict:
    """Get configuration for a specific template"""
    return WHATSAPP_TEMPLATES.get(template_name, {})
