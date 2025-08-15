from flask import Flask, request, jsonify, send_file, render_template
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

# Import dashboard
from routes.dashboard import dashboard_bp, DashboardService

# Initialize Flask app
app = Flask(__name__)
config = Config()
logger = ErrorLogger()

# Initialize services with proper error handling
supabase = None
whatsapp_service = None
refiloe = None
scheduler = None
voice_processor = None

try:
    # Initialize database
    supabase = init_supabase(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    log_info("Database initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize database: {str(e)}")

try:
    # Initialize services with error handling
    if supabase:
        whatsapp_service = WhatsAppService(config, supabase, logger)
        log_info("WhatsApp service initialized successfully")
        
        refiloe = RefiloeAssistant(config, supabase, whatsapp_service, logger)
        log_info("Refiloe assistant initialized successfully")
        
        scheduler = SchedulerService(config, supabase, whatsapp_service, logger)
        log_info("Scheduler service initialized successfully")
        
        # Initialize dashboard service
        import routes.dashboard as dashboard_module
        dashboard_module.dashboard_service = DashboardService(config, supabase)
        log_info("Dashboard service initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize services: {str(e)}")

# Try to initialize voice processor if available
try:
    from voice_helpers import VoiceProcessor
    voice_processor = VoiceProcessor()
    log_info("Voice processor initialized successfully")
except ImportError:
    log_warning("Voice processor not available - voice features disabled")
except Exception as e:
    log_error(f"Failed to initialize voice processor: {str(e)}")

# Voice processing configuration
VOICE_CONFIG = {
    'max_audio_size_mb': 16,
    'max_audio_duration_seconds': 120,  # 2 minutes
    'supported_languages': ['en', 'af', 'zu', 'xh'],  # English, Afrikaans, Zulu, Xhosa
    'fallback_to_text': True,
    'retry_attempts': 3,
    'error_messages': {
        'transcription_failed': "🎤 I couldn't understand that voice note clearly. Could you try again or type instead?",
        'audio_too_long': "🎤 Voice notes should be under 2 minutes. Please record a shorter message.",
        'network_error': "📶 Connection issue with voice notes. Please try again.",
        'general_error': "🎤 Having trouble with voice notes right now. Please type your message instead.",
    }
}

log_info(f"Application initialized - Database: {supabase is not None}, WhatsApp: {whatsapp_service is not None}, Refiloe: {refiloe is not None}")

# Register blueprints
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

@app.route('/')
def home():
    """Home page"""
    return """
    <html>
        <head>
            <title>Refiloe AI Assistant</title>
            <style>
                body { font-family: Arial; padding: 40px; background: #f0f0f0; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                h1 { color: #333; }
                .status { padding: 10px; background: #e8f5e9; border-radius: 5px; color: #2e7d32; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 I'm Refiloe</h1>
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

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        
        # Verify webhook signature if service is available
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
                    
                    # Handle voice notes (only if voice processor is available)
                    if 'audio' in message and voice_processor:
                        try:
                            result = voice_processor.handle_voice_note_with_fallback(
                                message, 
                                phone_number
                            )
                            
                            if result['success']:
                                message_text = result['text']
                                should_reply_with_voice = result.get('should_reply_with_voice', False)
                            else:
                                # Error already handled and user notified
                                continue
                        except Exception as e:
                            log_error(f"Voice processing error: {str(e)}")
                            if whatsapp_service:
                                whatsapp_service.send_message(
                                    phone_number,
                                    "🎤 I'm having trouble with voice notes right now. Please type your message instead."
                                )
                            continue
                    
                    # Handle text messages
                    elif 'text' in message:
                        message_text = message['text']['body']
                        log_info(f"Text message from {phone_number}: {message_text}")
                    
                    # Handle voice notes when voice processor not available
                    elif 'audio' in message and not voice_processor:
                        log_info(f"Voice note received but processor not available")
                        if whatsapp_service:
                            whatsapp_service.send_message(
                                phone_number,
                                "🎤 Voice notes are temporarily unavailable. Please send a text message instead."
                            )
                        continue
                    
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
                                f"I received your {message_type}, but I can only process text messages at the moment. Please send me a text message instead! 😊"
                            )
                        continue
                    
                    # Process with Refiloe
                    if message_text:
                        # Check if services are initialized
                        if not refiloe:
                            log_error("Refiloe service not initialized")
                            if whatsapp_service:
                                whatsapp_service.send_message(
                                    phone_number,
                                    "I'm starting up! Please try again in a few seconds. 🚀"
                                )
                            continue
                        
                        if not whatsapp_service:
                            log_error("WhatsApp service not initialized - cannot send response")
                            continue
                        
                        try:
                            # Process the message
                            log_info(f"Processing message with Refiloe for {phone_number}")
                            response = refiloe.process_message(phone_number, message_text)
                            
                            if response:
                                log_info(f"Refiloe response generated: {response[:100]}...")
                                
                                # Send response with appropriate format
                                if should_reply_with_voice and voice_processor:
                                    try:
                                        voice_buffer = voice_processor.text_to_speech(response)
                                        voice_processor.send_voice_note(phone_number, voice_buffer)
                                        log_info(f"Sent voice response to {phone_number}")
                                    except Exception as voice_error:
                                        log_error(f"Failed to send voice response: {str(voice_error)}")
                                        # Fallback to text
                                        whatsapp_service.send_message(phone_number, response)
                                else:
                                    # Send as text message
                                    send_result = whatsapp_service.send_message(phone_number, response)
                                    if send_result.get('success'):
                                        log_info(f"Message sent successfully to {phone_number}")
                                    else:
                                        log_error(f"Failed to send message: {send_result.get('error')}")
                            else:
                                log_warning(f"No response generated for message from {phone_number}")
                                
                        except Exception as process_error:
                            log_error(f"Error processing message with Refiloe: {str(process_error)}")
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
                'refiloe': 'initialized' if refiloe else 'not initialized',
                'scheduler': scheduler.check_health() if scheduler else 'not initialized',
                'voice_processor': 'available' if voice_processor else 'not available',
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
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for debugging"""
    try:
        data = request.get_json()
        phone = data.get('phone', '27731863036')
        message = data.get('message', 'Test message')
        
        if not refiloe:
            return jsonify({
                'success': False,
                'error': 'Refiloe not initialized'
            }), 500
        
        response = refiloe.process_message(phone, message)
        
        return jsonify({
            'success': True,
            'input': message,
            'response': response,
            'services': {
                'database': supabase is not None,
                'whatsapp': whatsapp_service is not None,
                'refiloe': refiloe is not None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
