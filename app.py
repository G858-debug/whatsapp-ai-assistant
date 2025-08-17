from flask import Flask, request, jsonify
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
    """Handle incoming WhatsApp messages with enhanced logging"""
    try:
        data = request.get_json()
        
        # Verify webhook signature if service is available
        if whatsapp_service and not whatsapp_service.verify_webhook_signature(request):
            log_error("Invalid webhook signature")
            return 'Unauthorized', 401
        
        # Log incoming webhook data
        log_info(f"Webhook received: {json.dumps(data, indent=2)}")
        
        # Check what type of webhook this is
        if data.get('entry'):
            for entry in data['entry']:
                if entry.get('changes'):
                    for change in entry['changes']:
                        # Log the field type
                        field = change.get('field')
                        log_info(f"Webhook field type: {field}")
                        
                        value = change.get('value', {})
                        
                        # Handle status updates
                        if value.get('statuses'):
                            log_info(f"Status update received: {value['statuses']}")
                            continue
                        
                        # Handle messages
                        if value.get('messages'):
                            messages = value['messages']
                            log_info(f"Found {len(messages)} messages")
                            
                            for message in messages:
                                try:
                                    phone_number = message.get('from')
                                    message_id = message.get('id')
                                    message_type = message.get('type', 'text')
                                    message_text = None
                                    should_reply_with_voice = False
                                    
                                    # Check for duplicates
                                    if whatsapp_service and whatsapp_service.is_duplicate_message(message_id):
                                        log_info(f"Duplicate message {message_id} - skipping")
                                        continue
                                    
                                    # Handle different message types
                                    if message_type == 'audio' or 'audio' in message:
                                        log_info(f"Audio message received from {phone_number}")
                                        
                                        if voice_processor:
                                            try:
                                                audio_id = message.get('audio', {}).get('id')
                                                
                                                if not audio_id:
                                                    log_error("No audio ID found in message")
                                                    if whatsapp_service:
                                                        whatsapp_service.send_message(
                                                            phone_number,
                                                            "🎤 I couldn't process that voice note. Please try again or type instead?"
                                                        )
                                                    continue
                                                
                                                log_info(f"Attempting to download audio with ID: {audio_id}")
                                                
                                                # Download and transcribe
                                                audio_buffer = voice_processor.download_whatsapp_media(audio_id)
                                                log_info(f"Downloaded audio: {len(audio_buffer)} bytes")
                                                
                                                message_text = voice_processor.transcribe_audio(audio_buffer)
                                                log_info(f"Transcribed text: {message_text}")
                                                
                                                should_reply_with_voice = True
                                                
                                            except Exception as e:
                                                log_error(f"Voice processing error: {str(e)}")
                                                log_error(f"Error type: {type(e).__name__}")
                                                log_error(f"Full error details: {e}", exc_info=True)
                                                
                                                if whatsapp_service:
                                                    whatsapp_service.send_message(
                                                        phone_number,
                                                        f"🎤 I had trouble processing your voice note. Error: {str(e)[:100]}... Please try typing instead."
                                                    )
                                                continue
                                        else:
                                            log_error("Voice processor not available")
                                            if whatsapp_service:
                                                whatsapp_service.send_message(
                                                    phone_number,
                                                    "🎤 Voice notes are temporarily unavailable. Please type your message instead."
                                                )
                                            continue
                                    
                                    elif message_type == 'text' or 'text' in message:
                                        message_text = message.get('text', {}).get('body', '')
                                        log_info(f"Text message: {message_text}")
                                    
                                    elif message_type == 'image' or 'image' in message:
                                        log_info(f"Image message received")
                                        if whatsapp_service:
                                            whatsapp_service.send_message(
                                                phone_number,
                                                "📷 I see you sent an image! I can't process images yet, but I can help with text or voice messages."
                                            )
                                        continue
                                    
                                    else:
                                        log_info(f"Unsupported message type: {message_type}")
                                        log_info(f"Full message data: {json.dumps(message, indent=2)}")
                                        if whatsapp_service:
                                            whatsapp_service.send_message(
                                                phone_number,
                                                f"I received your {message_type} message, but I can only process text and voice messages. Please try those instead!"
                                            )
                                        continue
                                    
                                    # Process with Refiloe if we have text
                                    if message_text:
                                        if not refiloe:
                                            log_error("Refiloe service not initialized")
                                            if whatsapp_service:
                                                whatsapp_service.send_message(
                                                    phone_number,
                                                    "I'm starting up! Please try again in a few seconds. 🚀"
                                                )
                                            continue
                                        
                                        if not whatsapp_service:
                                            log_error("WhatsApp service not initialized")
                                            continue
                                        
                                        try:
                                            log_info(f"Processing with Refiloe: {message_text[:50]}...")
                                            response = refiloe.process_message(
                                                whatsapp_number=phone_number,
                                                message_text=message_text,
                                                message_id=message_id
                                            )
                                            
                                            if response:
                                                log_info(f"Sending response: {response[:50]}...")
                                                
                                                if should_reply_with_voice and voice_processor:
                                                    try:
                                                        log_info("Converting response to voice...")
                                                        voice_buffer = voice_processor.text_to_speech(response)
                                                        log_info(f"Voice buffer size: {len(voice_buffer)} bytes")
                                                        
                                                        result = voice_processor.send_voice_note(phone_number, voice_buffer)
                                                        log_info(f"Voice send result: {result}")
                                                        
                                                    except Exception as voice_error:
                                                        log_error(f"Failed to send voice: {str(voice_error)}")
                                                        whatsapp_service.send_message(phone_number, response)
                                                else:
                                                    send_result = whatsapp_service.send_message(phone_number, response)
                                                    log_info(f"Text send result: {send_result}")
                                            else:
                                                log_warning(f"No response from Refiloe")
                                                
                                        except Exception as process_error:
                                            log_error(f"Refiloe processing error: {str(process_error)}", exc_info=True)
                                            whatsapp_service.send_message(
                                                phone_number,
                                                "I had a hiccup! 🤯 Please try again."
                                            )
                                    
                                except Exception as message_error:
                                    log_error(f"Error processing message: {str(message_error)}", exc_info=True)
                                    continue
                        
                        # Handle other value types
                        elif value.get('contacts'):
                            log_info(f"Contact update received")
                        elif value.get('errors'):
                            log_error(f"WhatsApp error: {value['errors']}")
                        else:
                            log_info(f"Unknown value type: {list(value.keys())}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        log_error(f"Critical webhook error: {str(e)}", exc_info=True)
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
