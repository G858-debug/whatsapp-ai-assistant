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

# Debug test
from debug_test import debug_bp
app.register_blueprint(debug_bp)

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

                        # Debug: Log everything in value
                        log_info(f"Value keys: {list(value.keys())}")
                        log_info(f"Full value content: {json.dumps(value, indent=2)}")
                        
                        # Handle messages
                        if value.get('messages'):
                            messages = value['messages']
                            log_info(f"Processing {len(messages)} message(s)")
                            
                            for message in messages:
                                try:
                                    phone_number = message['from']
                                    message_id = message['id']
                                    message_type = message.get('type', 'unknown')
                                    
                                    # ENHANCED LOGGING
                                    log_info(f"Message from {phone_number}")
                                    log_info(f"Message type: {message_type}")
                                    log_info(f"Message keys: {list(message.keys())}")
                                    
                                    # Check for duplicate messages
                                    if whatsapp_service and whatsapp_service.is_duplicate_message(message_id):
                                        log_info(f"Duplicate message {message_id} ignored")
                                        continue
                                    
                                    message_text = None
                                    should_reply_with_voice = False
                                    
                                    # Handle different message types
                                    if message_type == 'audio' or 'audio' in message:
                                        log_info(f"AUDIO MESSAGE RECEIVED!")
                                        log_info(f"Audio data: {message.get('audio', {})}")
                                        
                                        if voice_processor:
                                            try:
                                                audio_data = message.get('audio', {})
                                                audio_id = audio_data.get('id')
                                                
                                                if not audio_id:
                                                    log_error("No audio ID in message")
                                                    if whatsapp_service:
                                                        whatsapp_service.send_message(
                                                            phone_number,
                                                            "🎤 Received your voice note but couldn't process it. Please try again."
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
                                            response = refiloe.process_message(phone_number, message_text)
                                            
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
                                            log_error(f"Refiloe processing error: {str(process_error)}")
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

# Add these test endpoints to your app.py file (before the if __name__ == '__main__': line)

@app.route('/test-voice', methods=['GET'])
def test_voice_page():
    """Simple page to test voice functionality"""
    return """
    <html>
        <head>
            <title>Voice Test - Refiloe</title>
            <style>
                body { font-family: Arial; padding: 40px; background: #f0f0f0; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                h1 { color: #333; }
                .test-section { margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }
                button { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                button:hover { background: #45a049; }
                .result { margin-top: 20px; padding: 10px; background: #e8f5e9; border-radius: 5px; }
                .error { background: #ffebee; color: #c62828; }
                .success { background: #e8f5e9; color: #2e7d32; }
                pre { background: #263238; color: #aed581; padding: 10px; border-radius: 5px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎤 Voice Feature Testing</h1>
                
                <div class="test-section">
                    <h2>1. Test Voice Processor Status</h2>
                    <button onclick="testVoiceStatus()">Check Voice Status</button>
                    <div id="status-result"></div>
                </div>
                
                <div class="test-section">
                    <h2>2. Test Text-to-Speech</h2>
                    <input type="text" id="tts-text" placeholder="Enter text to convert to speech" style="width: 300px; padding: 8px;">
                    <button onclick="testTTS()">Test TTS</button>
                    <div id="tts-result"></div>
                </div>
                
                <div class="test-section">
                    <h2>3. Test WhatsApp Media Download</h2>
                    <input type="text" id="media-id" placeholder="Enter WhatsApp media ID" style="width: 300px; padding: 8px;">
                    <button onclick="testMediaDownload()">Test Download</button>
                    <div id="download-result"></div>
                </div>
                
                <div class="test-section">
                    <h2>4. Send Test Voice Message</h2>
                    <input type="text" id="phone-number" placeholder="Phone number (e.g., 27731863036)" style="width: 300px; padding: 8px;">
                    <button onclick="sendTestVoice()">Send Voice Test</button>
                    <div id="send-result"></div>
                </div>
            </div>
            
            <script>
                async function testVoiceStatus() {
                    const result = document.getElementById('status-result');
                    result.innerHTML = 'Testing...';
                    try {
                        const response = await fetch('/api/test-voice-status');
                        const data = await response.json();
                        result.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        result.className = response.ok ? 'result success' : 'result error';
                    } catch (error) {
                        result.innerHTML = 'Error: ' + error.message;
                        result.className = 'result error';
                    }
                }
                
                async function testTTS() {
                    const result = document.getElementById('tts-result');
                    const text = document.getElementById('tts-text').value;
                    if (!text) {
                        result.innerHTML = 'Please enter some text';
                        return;
                    }
                    result.innerHTML = 'Testing...';
                    try {
                        const response = await fetch('/api/test-tts', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({text: text})
                        });
                        const data = await response.json();
                        result.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        result.className = response.ok ? 'result success' : 'result error';
                    } catch (error) {
                        result.innerHTML = 'Error: ' + error.message;
                        result.className = 'result error';
                    }
                }
                
                async function testMediaDownload() {
                    const result = document.getElementById('download-result');
                    const mediaId = document.getElementById('media-id').value;
                    if (!mediaId) {
                        result.innerHTML = 'Please enter a media ID';
                        return;
                    }
                    result.innerHTML = 'Testing...';
                    try {
                        const response = await fetch('/api/test-media-download', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({media_id: mediaId})
                        });
                        const data = await response.json();
                        result.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        result.className = response.ok ? 'result success' : 'result error';
                    } catch (error) {
                        result.innerHTML = 'Error: ' + error.message;
                        result.className = 'result error';
                    }
                }
                
                async function sendTestVoice() {
                    const result = document.getElementById('send-result');
                    const phone = document.getElementById('phone-number').value;
                    if (!phone) {
                        result.innerHTML = 'Please enter a phone number';
                        return;
                    }
                    result.innerHTML = 'Sending test voice message...';
                    try {
                        const response = await fetch('/api/test-send-voice', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({phone: phone})
                        });
                        const data = await response.json();
                        result.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        result.className = response.ok ? 'result success' : 'result error';
                    } catch (error) {
                        result.innerHTML = 'Error: ' + error.message;
                        result.className = 'result error';
                    }
                }
            </script>
        </body>
    </html>
    """

@app.route('/api/test-voice-status', methods=['GET'])
def test_voice_status():
    """Test if voice processor is properly initialized"""
    try:
        status = {
            'voice_processor_available': voice_processor is not None,
            'openai_configured': False,
            'whatsapp_token_configured': bool(config.ACCESS_TOKEN),
            'phone_number_configured': bool(config.PHONE_NUMBER_ID),
            'errors': []
        }
        
        if voice_processor:
            # Check OpenAI
            if hasattr(voice_processor, 'openai_client'):
                status['openai_configured'] = voice_processor.openai_client is not None
            
            # Check if methods exist
            status['methods_available'] = {
                'download_whatsapp_media': hasattr(voice_processor, 'download_whatsapp_media'),
                'transcribe_audio': hasattr(voice_processor, 'transcribe_audio'),
                'text_to_speech': hasattr(voice_processor, 'text_to_speech'),
                'send_voice_note': hasattr(voice_processor, 'send_voice_note'),
            }
            
            # Check environment variables
            import os
            status['env_vars'] = {
                'OPENAI_API_KEY': 'set' if os.getenv('OPENAI_API_KEY') else 'missing',
                'ACCESS_TOKEN': 'set' if os.getenv('ACCESS_TOKEN') else 'missing',
                'PHONE_NUMBER_ID': 'set' if os.getenv('PHONE_NUMBER_ID') else 'missing',
            }
        else:
            status['errors'].append('Voice processor not initialized')
        
        return jsonify(status), 200 if not status['errors'] else 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-tts', methods=['POST'])
def test_tts():
    """Test text-to-speech conversion"""
    try:
        data = request.get_json()
        text = data.get('text', 'Hello, this is a test of the voice system.')
        
        if not voice_processor:
            return jsonify({'error': 'Voice processor not available'}), 500
        
        # Try to convert text to speech
        try:
            audio_buffer = voice_processor.text_to_speech(text)
            return jsonify({
                'success': True,
                'text': text,
                'audio_size_bytes': len(audio_buffer) if audio_buffer else 0,
                'message': 'Text-to-speech conversion successful'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-media-download', methods=['POST'])
def test_media_download():
    """Test downloading media from WhatsApp"""
    try:
        data = request.get_json()
        media_id = data.get('media_id')
        
        if not media_id:
            return jsonify({'error': 'No media_id provided'}), 400
        
        if not voice_processor:
            return jsonify({'error': 'Voice processor not available'}), 500
        
        try:
            audio_buffer = voice_processor.download_whatsapp_media(media_id)
            return jsonify({
                'success': True,
                'media_id': media_id,
                'size_bytes': len(audio_buffer) if audio_buffer else 0,
                'message': 'Media download successful'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'hint': 'Make sure the media_id is valid and recent'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-send-voice', methods=['POST'])
def test_send_voice():
    """Test sending a voice message"""
    try:
        data = request.get_json()
        phone = data.get('phone', '27731863036')
        test_message = "Hello! This is a test voice message from Refiloe. If you can hear this, voice notes are working!"
        
        if not voice_processor:
            return jsonify({'error': 'Voice processor not available'}), 500
        
        try:
            # Convert to voice
            audio_buffer = voice_processor.text_to_speech(test_message)
            
            # Send voice note
            result = voice_processor.send_voice_note(phone, audio_buffer)
            
            return jsonify({
                'success': True,
                'phone': phone,
                'message': test_message,
                'whatsapp_response': result,
                'status': 'Voice message sent successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'hint': 'Check OPENAI_API_KEY and WhatsApp credentials'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-transcribe', methods=['POST'])
def test_transcribe():
    """Test transcribing audio"""
    try:
        # This would need an actual audio file upload
        # For now, just test if the method exists
        if not voice_processor:
            return jsonify({'error': 'Voice processor not available'}), 500
        
        if not hasattr(voice_processor, 'transcribe_audio'):
            return jsonify({'error': 'Transcribe method not available'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Transcription method available',
            'note': 'To fully test, send a voice note via WhatsApp'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-direct', methods=['POST', 'GET'])
def test_direct():
    """Test Refiloe directly without WhatsApp"""
    try:
        # Simulate an incoming message
        test_data = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "TEST",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "27730564882",
                            "phone_number_id": "671257819413918"
                        },
                        "messages": [{
                            "from": "27731863036",
                            "id": "test_message_123",
                            "timestamp": "1755424056",
                            "text": {
                                "body": "Test message - show my schedule"
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Process it through the webhook handler
        with app.test_request_context(json=test_data):
            from flask import request
            result = handle_message()
            
        return jsonify({
            "success": True,
            "webhook_response": result,
            "message": "Check your WhatsApp for Refiloe's response"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Add this test endpoint to app.py temporarily
@app.route('/test-send', methods=['GET'])
def test_send():
    """Test sending a message"""
    try:
        if whatsapp_service:
            result = whatsapp_service.send_message(
                "27731863036",  # Your number
                "Test from Refiloe! If you see this, sending works! 🎉"
            )
            return jsonify(result)
        return jsonify({"error": "WhatsApp service not initialized"})
    except Exception as e:
        return jsonify({"error": str(e)})
