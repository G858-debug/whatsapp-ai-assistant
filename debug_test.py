# debug_test.py
"""
Systematic debugging script for Refiloe
Add this file to your project and visit /debug endpoint
"""

from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
import pytz

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug', methods=['GET', 'POST'])
def debug_endpoint():
    """Comprehensive debug endpoint to test all components"""
    
    results = {
        'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat(),
        'tests': {}
    }
    
    # Test 1: Environment Variables
    results['tests']['1_environment'] = {
        'ANTHROPIC_API_KEY': 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING',
        'SUPABASE_URL': 'SET' if os.getenv('SUPABASE_URL') else 'MISSING',
        'SUPABASE_SERVICE_KEY': 'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'MISSING',
        'ACCESS_TOKEN': 'SET' if os.getenv('ACCESS_TOKEN') else 'MISSING',
        'PHONE_NUMBER_ID': 'SET' if os.getenv('PHONE_NUMBER_ID') else 'MISSING',
    }
    
    # Test 2: Import Tests
    import_results = {}
    try:
        from config import Config
        import_results['config'] = 'OK'
        config = Config()
    except Exception as e:
        import_results['config'] = f'ERROR: {str(e)}'
        config = None
    
    try:
        import anthropic
        import_results['anthropic'] = 'OK'
    except Exception as e:
        import_results['anthropic'] = f'ERROR: {str(e)}'
    
    try:
        from supabase import create_client, Client
        import_results['supabase'] = 'OK'
    except Exception as e:
        import_results['supabase'] = f'ERROR: {str(e)}'
    
    results['tests']['2_imports'] = import_results
    
    # Test 3: Database Connection
    db_test = {}
    try:
        if config and config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
            from supabase import create_client
            supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            
            # Test query
            test_query = supabase.table('trainers').select('id').limit(1).execute()
            db_test['connection'] = 'OK'
            db_test['can_query'] = 'OK'
            
            # Check if your number exists
            trainer_check = supabase.table('trainers').select('*').eq('whatsapp', '27731863036').execute()
            if trainer_check.data:
                db_test['your_trainer_record'] = {
                    'found': True,
                    'id': trainer_check.data[0]['id'],
                    'name': trainer_check.data[0]['name'],
                    'status': trainer_check.data[0].get('status', 'unknown')
                }
            else:
                db_test['your_trainer_record'] = 'NOT FOUND - THIS IS THE PROBLEM!'
        else:
            db_test['error'] = 'Missing database configuration'
    except Exception as e:
        db_test['error'] = str(e)
    
    results['tests']['3_database'] = db_test
    
    # Test 4: AI Handler
    ai_test = {}
    try:
        from services.ai_intent_handler import AIIntentHandler
        
        if config:
            ai_handler = AIIntentHandler(config, supabase if 'supabase' in locals() else None)
            ai_test['initialization'] = 'OK'
            
            # Check if client is initialized
            if ai_handler.client:
                ai_test['anthropic_client'] = 'INITIALIZED'
                
                # Test a simple intent
                test_result = ai_handler.understand_message(
                    message="Show my schedule",
                    sender_type="trainer",
                    sender_data={'id': 'test', 'name': 'Test Trainer'},
                    conversation_history=[]
                )
                ai_test['test_intent'] = test_result.get('primary_intent', 'FAILED')
            else:
                ai_test['anthropic_client'] = 'NOT INITIALIZED - Using fallback'
                
                # Test fallback
                test_result = ai_handler._fallback_intent_detection("show my schedule", "trainer")
                ai_test['fallback_test'] = test_result.get('primary_intent', 'FAILED')
        else:
            ai_test['error'] = 'Config not available'
    except Exception as e:
        ai_test['error'] = str(e)
        ai_test['error_type'] = type(e).__name__
    
    results['tests']['4_ai_handler'] = ai_test
    
    # Test 5: Refiloe Service
    refiloe_test = {}
    try:
        from services.refiloe import RefiloeAssistant
        from services.whatsapp import WhatsAppService
        from utils.logger import ErrorLogger
        
        if config and 'supabase' in locals():
            # Initialize dependencies
            logger = ErrorLogger()
            whatsapp_service = WhatsAppService(config, supabase, logger)
            
            # Initialize Refiloe
            refiloe = RefiloeAssistant(config, supabase, whatsapp_service, logger)
            refiloe_test['initialization'] = 'OK'
            
            # Test message processing
            test_response = refiloe.process_message(
                whatsapp_number='27731863036',
                message_text='Hi',
                message_id='test_001'
            )
            refiloe_test['test_response'] = test_response[:100] if test_response else 'NO RESPONSE'
        else:
            refiloe_test['error'] = 'Dependencies not available'
    except Exception as e:
        refiloe_test['error'] = str(e)
        refiloe_test['error_type'] = type(e).__name__
        
        # Get the full traceback
        import traceback
        refiloe_test['traceback'] = traceback.format_exc()
    
    results['tests']['5_refiloe'] = refiloe_test
    
    # Test 6: Check specific methods
    method_test = {}
    try:
        from services.ai_intent_handler import AIIntentHandler
        
        # Check if methods exist
        method_test['_build_trainer_context'] = hasattr(AIIntentHandler, '_build_trainer_context')
        method_test['_build_client_context'] = hasattr(AIIntentHandler, '_build_client_context')
        method_test['_fallback_intent_detection'] = hasattr(AIIntentHandler, '_fallback_intent_detection')
        method_test['_parse_ai_response'] = hasattr(AIIntentHandler, '_parse_ai_response')
    except Exception as e:
        method_test['error'] = str(e)
    
    results['tests']['6_methods'] = method_test
    
    # Test 7: Direct message simulation
    if request.method == 'POST':
        sim_test = {}
        try:
            data = request.get_json() or {}
            test_message = data.get('message', 'show my schedule')
            
            # Simulate the exact flow
            from app import refiloe, whatsapp_service
            
            if refiloe:
                response = refiloe.process_message(
                    '27731863036',
                    test_message,
                    'test_msg'
                )
                sim_test['response'] = response
            else:
                sim_test['error'] = 'Refiloe not initialized in app'
        except Exception as e:
            sim_test['error'] = str(e)
            import traceback
            sim_test['traceback'] = traceback.format_exc()
        
        results['tests']['7_simulation'] = sim_test
    
    return jsonify(results)

@debug_bp.route('/debug/fix-trainer', methods=['GET'])
def fix_trainer():
    """Quick fix to add trainer to database"""
    try:
        from config import Config
        from supabase import create_client
        
        config = Config()
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        
        # Check if exists
        existing = supabase.table('trainers').select('*').eq('whatsapp', '27731863036').execute()
        
        if not existing.data:
            # Insert new trainer
            result = supabase.table('trainers').insert({
                'name': 'Test Trainer',
                'whatsapp': '27731863036',
                'email': 'trainer@example.com',
                'status': 'active',
                'created_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat(),
                'updated_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            }).execute()
            
            return jsonify({
                'success': True,
                'message': 'Trainer added successfully',
                'trainer_id': result.data[0]['id'] if result.data else None
            })
        else:
            # Update to active
            result = supabase.table('trainers').update({
                'status': 'active',
                'updated_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            }).eq('id', existing.data[0]['id']).execute()
            
            return jsonify({
                'success': True,
                'message': 'Trainer already exists and updated to active',
                'trainer': existing.data[0]
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
