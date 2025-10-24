"""Test Phase 3 imports"""
print("Testing Phase 3 imports...")

try:
    from services.habits import HabitService, AssignmentService, LoggingService, ReportService
    print("✓ Phase 3 services imported")
    
    from services.ai_intent_handler import AIIntentHandler
    print("✓ AIIntentHandler imported")
    
    # Test both calling conventions
    class MockDB:
        pass
    class MockWhatsApp:
        pass
    class MockConfig:
        ANTHROPIC_API_KEY = None
        TIMEZONE = 'Africa/Johannesburg'
    
    # Test Phase 1-3 style
    handler1 = AIIntentHandler(MockDB(), MockWhatsApp())
    print("✓ AIIntentHandler(db, whatsapp) works")
    
    # Test app_core.py style
    services = {'whatsapp': MockWhatsApp()}
    handler2 = AIIntentHandler(MockConfig, MockDB(), services)
    print("✓ AIIntentHandler(Config, supabase, services_dict) works")
    
    print("\n✅ ALL TESTS PASSED!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
