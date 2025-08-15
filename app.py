from flask import Flask, request, jsonify, send_file, render_template
import os
from datetime import datetime
import pytz
import json
from voice_helpers import VoiceProcessor

# Import our modules
from config import Config
from utils.logger import ErrorLogger, log_info, log_error, log_warning
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeAssistant
from services.scheduler import SchedulerService
from models import init_supabase

# Import dashboard
from routes.dashboard import dashboard_bp, DashboardService

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
    
    # Initialize dashboard service
    import routes.dashboard as dashboard_module
    dashboard_module.dashboard_service = DashboardService(config, supabase)

    # Initialize voice processor (if separate file)
    voice_processor = VoiceProcessor()
    audio_buffer = voice_processor.download_whatsapp_media(message['audio']['id'])
    
    # Register dashboard blueprint
    app.register_blueprint(dashboard_bp)
    
    log_info("All services initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize services: {str(e)}")
    supabase = None
    whatsapp_service = None
    refiloe = None
    scheduler = None

# Error template (create templates/error.html)
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', 
                         message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    log_error(f"Server error: {str(e)}")
    return render_template('error.html', 
                         message="Internal server error"), 500

# Routes
@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Refiloe AI - Personal Trainer Assistant</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 20px;
                }
                h1 {
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }
                p {
                    font-size: 1.2em;
                    opacity: 0.9;
                }
                .status {
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    border-radius: 20px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>👋 Hi! I'm Refiloe</h1>
                <p>Your AI assistant for personal trainers</p>
                <div class="status">✅ System Online</div>
            </div>
        </body>
    </html>
    """

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

# In app.py - REPLACE your current handle_message function with this:

# In app.py - Updated handle_message function with comprehensive error handling

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        
        # Verify webhook signature
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
                try:  # Individual message error handling
                    phone_number = message['from']
                    message_id = message['id']
                    
                    # Check for duplicate messages
                    if whatsapp_service and whatsapp_service.is_duplicate_message(message_id):
                        log_info(f"Duplicate message {message_id} ignored")
                        continue
                    
                    message_text = None
                    should_reply_with_voice = False
                    
                    # Handle voice notes
                    if 'audio' in message:
                        result = whatsapp_service.handle_voice_note_with_fallback(
                            message, 
                            phone_number
                        )
                        
                        if result['success']:
                            message_text = result['text']
                            should_reply_with_voice = result.get('should_reply_with_voice', False)
                        else:
                            # Error already handled and user notified
                            continue
                    
                    # Handle text messages
                    elif 'text' in message:
                        message_text = message['text']['body']
                        log_info(f"Text message from {phone_number}: {message_text}")
                    
                    # Handle unsupported message types
                    else:
                        message_type = 'unknown'
                        if 'image' in message:
                            message_type = 'image'
                        elif 'video' in message:
                            message_type = 'video'
                        elif 'document' in message:
                            message_type = 'document'
                        elif 'sticker' in message:
                            message_type = 'sticker'
                        
                        log_info(f"{message_type} message from {phone_number} - not supported")
                        
                        if message_type != 'unknown' and whatsapp_service:
                            whatsapp_service.send_message(
                                phone_number,
                                f"I received your {message_type}, but I can only process text and voice messages at the moment. Please send me a text or voice message instead! 😊"
                            )
                        continue
                    
                    # Process with Refiloe
                    if message_text and refiloe:
                        try:
                            response = refiloe.process_message(phone_number, message_text)
                            
                            # Send response with appropriate format
                            if whatsapp_service:
                                if should_reply_with_voice:
                                    try:
                                        voice_buffer = whatsapp_service.text_to_speech(response)
                                        whatsapp_service.send_voice_note(phone_number, voice_buffer)
                                        log_info(f"Sent voice response to {phone_number}")
                                        
                                    except Exception as voice_error:
                                        log_error(f"Failed to send voice response: {str(voice_error)}")
                                        # Fallback to text
                                        whatsapp_service.send_message(phone_number, response)
                                        whatsapp_service.send_message(
                                            phone_number,
                                            "📝 (I tried to send this as a voice note but had to send text instead)"
                                        )
                                else:
                                    whatsapp_service.send_message(phone_number, response)
                                    
                        except Exception as process_error:
                            log_error(f"Error processing message with Refiloe: {str(process_error)}")
                            if whatsapp_service:
                                whatsapp_service.send_message(
                                    phone_number,
                                    "I'm having a moment! 🤯 Let me collect myself... Please try again in a few seconds."
                                )
                    
                except Exception as message_error:
                    log_error(f"Error processing individual message: {str(message_error)}")
                    continue  # Skip to next message
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        log_error(f"Critical error in webhook: {str(e)}", exc_info=True)
        # Don't expose internal errors to WhatsApp
        return jsonify({'status': 'error'}), 500

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
                'dashboard': 'enabled' if dashboard_module.dashboard_service else 'disabled',
                'ai_model': config.AI_MODEL if hasattr(config, 'AI_MODEL') else 'not configured',
            },
            'version': '2.1.0',
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
    app.run(host='0.0.0.0', port=port, debug=False)
