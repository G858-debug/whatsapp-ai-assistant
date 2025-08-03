from flask import Flask, request, jsonify, send_file
import os
from datetime import datetime
import pytz
import json

# Import our modules
from config import Config
from utils.logger import ErrorLogger, log_info, log_error, log_warning
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeAssistant
from services.scheduler import SchedulerService
from models import init_supabase

# Initialize Flask app
app = Flask(__name__)
config = Config()
logger = ErrorLogger()

# Initialize services
try:
    # Initialize database
    supabase = init_supabase(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Initialize services with error handling
    whatsapp_service = WhatsAppService(config, supabase, logger)
    refiloe = RefiloeAssistant(config, supabase, whatsapp_service, logger)
    scheduler = SchedulerService(config, supabase, whatsapp_service, logger)
    
    log_info("All services initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize services: {str(e)}")
    supabase = None
    whatsapp_service = None
    refiloe = None
    scheduler = None

# Routes
@app.route('/')
def home():
    return "Hi! I'm Refiloe, your AI assistant for personal trainers! 💪😊"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification for WhatsApp"""
    try:
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == config.VERIFY_TOKEN:
            log_info("Webhook verified successfully")
            return challenge
        else:
            log_error("Webhook verification failed")
            return 'Forbidden', 403
    except Exception as e:
        log_error(f"Error in webhook verification: {str(e)}")
        return 'Internal Server Error', 500

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        
        # Verify webhook signature (security improvement)
        if whatsapp_service and not whatsapp_service.verify_webhook_signature(request):
            log_error("Invalid webhook signature")
            return 'Unauthorized', 401
        
        # Log incoming webhook data
        log_info(f"Webhook received: {json.dumps(data, indent=2)}")
        
        # Process messages
        if (data.get('entry') and 
            data['entry'][0].get('changes') and 
            data['entry'][0]['changes'][0].get('value', {}).get('messages')):
            
            messages = data['entry'][0]['changes'][0]['value']['messages']
            
            for message in messages:
                phone_number = message['from']
                message_id = message['id']
                
                # Check for duplicate messages
                if whatsapp_service and whatsapp_service.is_duplicate_message(message_id):
                    log_info(f"Duplicate message {message_id} ignored")
                    continue
                
                # Handle text messages
                if 'text' in message:
                    message_text = message['text']['body']
                    log_info(f"Processing message from {phone_number}: {message_text}")
                    
                    # Process with Refiloe
                    if refiloe:
                        response = refiloe.process_message(phone_number, message_text)
                        
                        # Send response
                        if whatsapp_service:
                            whatsapp_service.send_message(phone_number, response)
                    else:
                        log_error("Refiloe service not initialized")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        log_error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            'status': 'healthy' if supabase else 'degraded',
            'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat(),
            'services': {
                'database': 'connected' if supabase else 'disconnected',
                'whatsapp': whatsapp_service.check_health() if whatsapp_service else 'not initialized',
                'scheduler': scheduler.check_health() if scheduler else 'not initialized',
                'ai_model': config.AI_MODEL if hasattr(config, 'AI_MODEL') else 'not configured',
            },
            'version': '2.0.1',
            'errors_today': logger.get_error_count_today() if logger else 0
        }
        return jsonify(health_status)
    except Exception as e:
        log_error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
        }), 500

@app.route('/logs/errors')
def view_errors():
    """View recent errors (protected endpoint)"""
    # In production, add authentication here
    try:
        if logger:
            errors = logger.get_recent_errors(limit=50)
            return jsonify({
                'error_count': len(errors),
                'errors': errors,
                'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            })
        else:
            return jsonify({
                'error': 'Logger not initialized',
                'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
        }), 500

@app.route('/logs/download')
def download_logs():
    """Download error logs"""
    # In production, add authentication here
    try:
        if logger:
            log_file = logger.get_log_file_path()
            if os.path.exists(log_file):
                return send_file(log_file, as_attachment=True, download_name='refiloe_errors.log')
            else:
                return jsonify({'error': 'Log file not found'}), 404
        else:
            return jsonify({'error': 'Logger not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin endpoints
@app.route('/admin/add_trainer', methods=['POST'])
def add_trainer():
    """Add a new trainer"""
    try:
        if not refiloe:
            return jsonify({'error': 'Service not initialized'}), 500
            
        data = request.get_json()
        
        # Validate input
        required_fields = ['name', 'whatsapp', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add trainer through Refiloe
        result = refiloe.add_trainer(data)
        
        return jsonify(result)
    except Exception as e:
        log_error(f"Error adding trainer: {str(e)}")
        return jsonify({'error': 'Failed to add trainer'}), 500

@app.route('/admin/trigger_reminders/<trainer_id>')
def trigger_reminders(trainer_id):
    """Manually trigger reminders for a trainer"""
    try:
        if not scheduler:
            return jsonify({'error': 'Scheduler not initialized'}), 500
            
        result = scheduler.send_trainer_reminders(trainer_id)
        return jsonify(result)
    except Exception as e:
        log_error(f"Error triggering reminders: {str(e)}")
        return jsonify({'error': 'Failed to send reminders'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    log_error(f"Server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

# Cleanup on shutdown
import atexit
def cleanup():
    if scheduler:
        scheduler.shutdown()
    if logger:
        logger.close()

atexit.register(cleanup)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # Set debug=False in production
