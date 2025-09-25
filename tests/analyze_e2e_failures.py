# tests/analyze_e2e_failures.py
def analyze_failure(test_name, expected, actual):
    """Analyze why an E2E test failed and suggest fixes"""
    
    suggestions = []
    
    if "not recognized" in actual and "welcome back" in expected:
        suggestions.append({
            "issue": "Trainer recognition failing",
            "check": [
                "1. Is trainer lookup query correct?",
                "2. Is phone number format matching?",
                "3. Check database connection"
            ],
            "files_to_check": [
                "services/ai_intent_handler.py",
                "services/registration/trainer_registration.py"
            ]
        })
    
    elif "invalid command" in actual:
        suggestions.append({
            "issue": "Natural language not understood",
            "check": [
                "1. Add this phrase to AI prompt examples",
                "2. Update command patterns",
                "3. Check text preprocessing"
            ],
            "files_to_check": [
                "services/ai_intent_handler.py"
            ]
        })
    
    return suggestions
