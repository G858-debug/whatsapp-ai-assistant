from flask import Flask, request, jsonify, render_template_string
import os
from datetime import datetime, timedelta
import pytz
import json
import atexit
import uuid
import re  # Added for sanitization
from apscheduler.schedulers.background import BackgroundScheduler

# Payment imports
from payment_manager import PaymentManager
from payment_integration import PaymentIntegration
from payfast_webhook import payfast_webhook_bp

# Import our modules
from config import Config
from utils.logger import ErrorLogger, log_info, log_error, log_warning
from utils.rate_limiter import RateLimiter
from utils.input_sanitizer import InputSanitizer  # NEW IMPORT
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
rate_limiter = None
input_sanitizer = None  # NEW VARIABLE

# Initialize payment system
payment_manager = None
payment_integration = None

# Initialize background scheduler for payments
payment_scheduler = BackgroundScheduler()

# Register PayFast webhook blueprint
app.register_blueprint(payfast_webhook_bp)

try:
    # Initialize database
    supabase = init_supabase(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    log_info("Database initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize database: {str(e)}")

# Initialize Rate Limiter
try:
    if supabase:
        rate_limiter = RateLimiter(config, supabase)
        log_info("Rate limiter initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize rate limiter: {str(e)}")
    rate_limiter = None

# NEW: Initialize Input Sanitizer
try:
    input_sanitizer = InputSanitizer(config)
    log_info("Input sanitizer initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize input sanitizer: {str(e)}")
    input_sanitizer = None

try:
    # Initialize payment system
    if supabase:
        payment_manager = PaymentManager()
        payment_integration = PaymentIntegration()
        log_info("Payment system initialized successfully")
except Exception as e:
    log_error(f"Failed to initialize payment system: {str(e)}")

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

log_info(f"Application initialized - Database: {supabase is not None}, WhatsApp: {whatsapp_service is not None}, Refiloe: {refiloe is not None}, Payments: {payment_manager is not None}, Rate Limiter: {rate_limiter is not None}, Sanitizer: {input_sanitizer is not None}")

# Register blueprints
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

# ============================================
# SCHEDULED TASKS WITH RATE LIMITER CLEANUP
# ============================================

def send_daily_payment_reminders():
    """Send daily payment reminders (runs at 9 AM daily)"""
    try:
        if payment_manager:
            log_info("Running daily payment reminders...")
            payment_manager.send_monthly_payment_reminders()
            log_info("Payment reminders sent successfully")
    except Exception as e:
        log_error(f"Error in payment reminder job: {str(e)}")

def cleanup_rate_limiter():
    """Clean up old rate limiter data (runs every 6 hours)"""
    if rate_limiter:
        try:
            rate_limiter.cleanup_old_data()
            log_info("Rate limiter cleanup completed")
        except Exception as e:
            log_error(f"Error during rate limiter cleanup: {str(e)}")

# Schedule the payment reminder job
if payment_manager:
    payment_scheduler.add_job(
        func=send_daily_payment_reminders,
        trigger="cron",
        hour=9,
        minute=0,
        id='payment_reminders',
        replace_existing=True
    )
    payment_scheduler.start()
    log_info("Payment scheduler started")

# Schedule rate limiter cleanup
if rate_limiter:
    payment_scheduler.add_job(
        func=cleanup_rate_limiter,
        trigger="interval",
        hours=6,
        id='rate_limiter_cleanup',
        replace_existing=True
    )
    log_info("Rate limiter cleanup scheduled")

# Shut down scheduler when app exits
atexit.register(lambda: payment_scheduler.shutdown() if payment_scheduler else None)

# ============================================
# HELPER FUNCTIONS FOR PAYMENTS
# ============================================

def get_user_info(phone: str):
    """Get user information from database"""
    try:
        if not supabase:
            return None
            
        # Check if trainer
        trainer = supabase.table('trainers').select('id').eq('whatsapp', phone).execute()
        if trainer.data:
            return {'type': 'trainer', 'id': trainer.data[0]['id']}
        
        # Check if client
        client = supabase.table('clients').select('id, trainer_id').eq('whatsapp', phone).execute()
        if client.data:
            return {'type': 'client', 'id': client.data[0]['id'], 'trainer_id': client.data[0].get('trainer_id')}
        
        return None
    except Exception as e:
        log_error(f"Error getting user info: {str(e)}")
        return None

def handle_payment_response(phone: str, response: dict):
    """Handle payment-related responses"""
    try:
        message = response.get('message', '')
        
        # Send WhatsApp response
        if whatsapp_service:
            whatsapp_service.send_message(phone, message)
            log_info(f"Payment response sent to {phone}")
        
        # Log the interaction
        if supabase:
            user_info = get_user_info(phone)
            supabase.table('messages').insert({
                'trainer_id': user_info['id'] if user_info and user_info['type'] == 'trainer' else None,
                'client_id': user_info['id'] if user_info and user_info['type'] == 'client' else None,
                'whatsapp_from': phone,
                'whatsapp_to': config.PHONE_NUMBER_ID if hasattr(config, 'PHONE_NUMBER_ID') else None,
                'message_text': message[:500],  # Limit message length
                'message_type': 'text',
                'direction': 'outgoing',
                'ai_intent': 'payment',
                'created_at': datetime.now().isoformat()
            }).execute()
            
    except Exception as e:
        log_error(f"Error handling payment response: {str(e)}")

# ============================================
# DATA DELETION FUNCTIONS
# ============================================

def process_data_deletion_request(deletion_request: dict):
    """Process a single data deletion request"""
    try:
        phone = deletion_request['phone']
        user_type = deletion_request['user_type']
        
        if user_type == 'client':
            # Delete client data
            # 1. Delete all messages
            supabase.table('messages').delete().eq('sender_phone', phone).execute()
            
            # 2. Delete all bookings
            supabase.table('bookings').delete().eq('client_phone', phone).execute()
            
            # 3. Delete all workouts and related data
            client = supabase.table('clients').select('id').eq('whatsapp', phone).execute()
            if client.data:
                client_id = client.data[0]['id']
                # Delete related data (only tables that exist)
                for table in ['workout_history', 'pending_workouts', 'fitness_assessments', 
                             'fitness_goals', 'physical_measurements', 'assessment_photos']:
                    try:
                        supabase.table(table).delete().eq('client_id', client_id).execute()
                    except:
                        pass  # Table might not exist
                
                # Delete payment tokens and requests
                supabase.table('client_payment_tokens').delete().eq('client_id', client_id).execute()
                supabase.table('payment_requests').delete().eq('client_id', client_id).execute()
            
            # 4. Delete client record
            supabase.table('clients').delete().eq('whatsapp', phone).execute()
            
        elif user_type == 'trainer':
            # Delete trainer data
            trainer = supabase.table('trainers').select('id').eq('whatsapp', phone).execute()
            if trainer.data:
                trainer_id = trainer.data[0]['id']
                
                # Notify all clients
                clients = supabase.table('clients').select('whatsapp').eq('trainer_id', trainer_id).execute()
                for client in clients.data:
                    notify_msg = (
                        "⚠️ *Important Notice*\n\n"
                        "Your trainer has closed their Refiloe account. "
                        "Your training data has been preserved, but you'll need to find a new trainer.\n\n"
                        "Contact support if you need assistance."
                    )
                    if whatsapp_service:
                        whatsapp_service.send_message(client['whatsapp'], notify_msg)
                
                # Delete trainer's data
                supabase.table('trainers').delete().eq('id', trainer_id).execute()
                # Mark clients as orphaned instead of deleting
                supabase.table('clients').update({'trainer_id': None}).eq('trainer_id', trainer_id).execute()
        
        # Update request status
        supabase.table('data_deletion_requests').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }).eq('id', deletion_request['id']).execute()
        
        # Send confirmation
        completion_msg = (
            "✅ *Data Deletion Complete*\n\n"
            f"Dear {deletion_request['full_name']},\n\n"
            "Your data has been successfully deleted from Refiloe as requested.\n\n"
            f"Deletion ID: {deletion_request['id'][:8].upper()}\n"
            f"Completed on: {datetime.now().strftime('%d %B %Y')}\n\n"
            "Thank you for using Refiloe. We're sorry to see you go."
        )
        if whatsapp_service:
            whatsapp_service.send_message(phone, completion_msg)
        
        log_info(f"Completed data deletion for {phone}")
        return True
        
    except Exception as e:
        log_error(f"Error processing deletion {deletion_request['id']}: {str(e)}")
        # Mark as failed
        supabase.table('data_deletion_requests').update({
            'status': 'failed',
            'error': str(e)
        }).eq('id', deletion_request['id']).execute()
        return False

# ============================================
# ROUTES
# ============================================

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
                .payment-status { padding: 10px; background: #fff3e0; border-radius: 5px; color: #e65100; margin-top: 10px; }
                .security-status { padding: 10px; background: #e3f2fd; border-radius: 5px; color: #1565c0; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 I'm Refiloe</h1>
                <p>Your AI assistant for personal trainers</p>
                <div class="status">✅ System Online</div>
                <div class="payment-status">💳 Payment System Active</div>
                <div class="security-status">🔒 Security Active (Rate Limiting + Input Sanitization)</div>
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
    """Handle incoming WhatsApp messages with sanitization, rate limiting, and payment integration"""
    try:
        data = request.get_json()
        
        # SECURITY CHECK 1: Verify webhook signature
        if whatsapp_service and not whatsapp_service.verify_webhook_signature(request):
            log_error("Invalid webhook signature")
            return 'Unauthorized', 401
        
        # SECURITY CHECK 2: Check webhook IP rate limit
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if rate_limiter and not rate_limiter.check_webhook_rate(client_ip):
            log_warning(f"Webhook rate limit exceeded for IP {client_ip}")
            return 'Too Many Requests', 429
        
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
                                    warning_needed = False
                                    
                                    # SECURITY CHECK 3: Sanitize phone number
                                    if input_sanitizer and phone_number:
                                        sanitized_phone, phone_valid = input_sanitizer.sanitize_phone_number(phone_number)
                                        if not phone_valid:
                                            log_warning(f"Invalid phone number format: {phone_number}")
                                            continue
                                        phone_number = sanitized_phone
                                    
                                    # Check for duplicates
                                    if whatsapp_service and whatsapp_service.is_duplicate_message(message_id):
                                        log_info(f"Duplicate message {message_id} - skipping")
                                        continue
                                    
                                    # SECURITY CHECK 4: Apply rate limiting based on message type
                                    if rate_limiter:
                                        # Determine actual message type for rate limiting
                                        if message_type == 'audio' or 'audio' in message:
                                            check_type = 'voice'
                                        else:
                                            check_type = 'text'
                                        
                                        allowed, error_message = rate_limiter.check_message_rate(
                                            phone_number, 
                                            check_type
                                        )
                                        
                                        if not allowed:
                                            # Send rate limit message
                                            if whatsapp_service:
                                                whatsapp_service.send_message(phone_number, error_message)
                                            log_warning(f"Rate limited message from {phone_number}: {error_message}")
                                            continue
                                        
                                        # Check if we should send a warning
                                        if rate_limiter.should_send_warning(phone_number):
                                            warning_needed = True
                                    
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
                                                
                                                # SECURITY CHECK 5: Sanitize transcribed text
                                                if input_sanitizer and message_text:
                                                    sanitized_text, is_safe, warnings = input_sanitizer.sanitize_message(
                                                        message_text, 
                                                        phone_number
                                                    )
                                                    
                                                    if not is_safe:
                                                        log_error(f"Blocked unsafe voice message from {phone_number}")
                                                        if whatsapp_service:
                                                            whatsapp_service.send_message(
                                                                phone_number,
                                                                "⚠️ Your voice message contained invalid content. Please try again."
                                                            )
                                                        continue
                                                    
                                                    message_text = sanitized_text
                                                
                                                should_reply_with_voice = True
                                                
                                            except Exception as e:
                                                log_error(f"Voice processing error: {str(e)}")
                                                log_error(f"Error type: {type(e).__name__}")
                                                log_error(f"Full error details: {e}", exc_info=True)
                                                
                                                if whatsapp_service:
                                                    whatsapp_service.send_message(
                                                        phone_number,
                                                        f"🎤 I had trouble processing your voice note. Please try typing instead."
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
                                        raw_message = message.get('text', {}).get('body', '')
                                        
                                        # SECURITY CHECK 6: Sanitize message text
                                        if input_sanitizer:
                                            sanitized_text, is_safe, warnings = input_sanitizer.sanitize_message(
                                                raw_message, 
                                                phone_number
                                            )
                                            
                                            # Log any warnings
                                            for warning in warnings:
                                                log_warning(f"Sanitization warning for {phone_number}: {warning}")
                                            
                                            # Block if unsafe
                                            if not is_safe:
                                                log_error(f"Blocked unsafe message from {phone_number}")
                                                
                                                # Log to database for security audit
                                                if supabase:
                                                    try:
                                                        supabase.table('security_audit_log').insert({
                                                            'event_type': 'blocked_message',
                                                            'phone_number': phone_number,
                                                            'details': {
                                                                'warnings': warnings,
                                                                'message_preview': raw_message[:100]
                                                            },
                                                            'created_at': datetime.now().isoformat()
                                                        }).execute()
                                                    except:
                                                        pass  # Don't break if audit log doesn't exist
                                                
                                                # Send warning to user
                                                if whatsapp_service:
                                                    whatsapp_service.send_message(
                                                        phone_number,
                                                        "⚠️ Your message contained invalid content and was blocked for security reasons. Please try again with a different message."
                                                    )
                                                continue
                                            
                                            message_text = sanitized_text
                                        else:
                                            message_text = raw_message
                                        
                                        log_info(f"Sanitized message: {message_text[:50]}...")
                                        
                                        # Check for data deletion request via WhatsApp
                                        if message_text.upper().strip() == "DELETE MY DATA":
                                            # Handle data deletion request
                                            user_info = get_user_info(phone_number)
                                            if user_info:
                                                deletion_request = {
                                                    'id': str(uuid.uuid4()),
                                                    'user_type': user_info['type'],
                                                    'full_name': 'WhatsApp User',
                                                    'phone': phone_number,
                                                    'reason': 'Requested via WhatsApp',
                                                    'status': 'pending',
                                                    'requested_at': datetime.now().isoformat(),
                                                    'process_by': (datetime.now() + timedelta(days=30)).isoformat(),
                                                    'ip_address': 'WhatsApp'
                                                }
                                                
                                                # Store in database
                                                supabase.table('data_deletion_requests').insert(deletion_request).execute()
                                                
                                                # Send confirmation
                                                confirmation_msg = (
                                                    "📋 *Data Deletion Request Received*\n\n"
                                                    "We've received your request to delete your data from Refiloe. "
                                                    "Your request will be processed within 30 days as per data protection regulations.\n\n"
                                                    f"Request ID: {deletion_request['id'][:8].upper()}\n"
                                                    f"Requested on: {datetime.now().strftime('%d %B %Y')}\n\n"
                                                    "You'll receive another message once the deletion is complete.\n\n"
                                                    "If you change your mind, please contact us immediately."
                                                )
                                                whatsapp_service.send_message(phone_number, confirmation_msg)
                                                continue
                                            else:
                                                whatsapp_service.send_message(
                                                    phone_number,
                                                    "❌ We couldn't find your account. Please make sure you're using the registered WhatsApp number."
                                                )
                                                continue
                                    
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
                                    
                                    # SECURITY CHECK 7: Special handling for payment messages
                                    if message_text and payment_integration:
                                        payment_keywords = ['pay', 'payment', 'invoice', 'bill', 'charge']
                                        if any(keyword in message_text.lower() for keyword in payment_keywords):
                                            # Additional rate limiting for payment requests
                                            if rate_limiter:
                                                allowed, error_msg = rate_limiter.check_payment_rate(phone_number)
                                                if not allowed:
                                                    if whatsapp_service:
                                                        whatsapp_service.send_message(phone_number, error_msg)
                                                    continue
                                            
                                            # Extract and sanitize amount if present
                                            amount_match = re.search(r'R?\s*(\d+(?:\.\d{2})?)', message_text)
                                            if amount_match and input_sanitizer:
                                                amount_str = amount_match.group(1)
                                                sanitized_amount, amount_valid = input_sanitizer.sanitize_amount(amount_str)
                                                
                                                if not amount_valid:
                                                    if whatsapp_service:
                                                        whatsapp_service.send_message(
                                                            phone_number,
                                                            "💰 Invalid amount format. Please use format like: R100 or R100.50"
                                                        )
                                                    continue
                                        
                                        user_info = get_user_info(phone_number)
                                        
                                        if user_info:
                                            # Check if it's a payment-related message
                                            payment_response = payment_integration.process_payment_message(
                                                phone_number,
                                                message_text,
                                                user_info['type'],
                                                user_info['id']
                                            )
                                            
                                            if payment_response:
                                                # Handle payment response
                                                log_info(f"Payment command processed: {payment_response.get('type')}")
                                                handle_payment_response(phone_number, payment_response)
                                                
                                                # Send warning if needed after payment processing
                                                if warning_needed and whatsapp_service:
                                                    whatsapp_service.send_message(
                                                        phone_number, 
                                                        config.RATE_LIMIT_WARNING_MESSAGE
                                                    )
                                                continue  # Skip regular Refiloe processing
                                    
                                    # Process with Refiloe if not a payment command
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
                                                message_text=message_text,  # This is now sanitized
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
                                                
                                                # Send warning message if needed after successful processing
                                                if warning_needed and whatsapp_service:
                                                    whatsapp_service.send_message(
                                                        phone_number, 
                                                        config.RATE_LIMIT_WARNING_MESSAGE
                                                    )
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

# ============================================
# ADMIN ENDPOINTS
# ============================================

@app.route('/admin/sanitization-stats', methods=['GET'])
def get_sanitization_stats():
    """Get sanitization statistics (admin only)"""
    try:
        # Check admin authorization
        auth_token = request.headers.get('X-Admin-Token')
        if auth_token != os.environ.get('ADMIN_TOKEN'):
            return jsonify({'error': 'Unauthorized'}), 401
        
        if input_sanitizer:
            stats = input_sanitizer.get_sanitization_stats()
            return jsonify(stats), 200
        else:
            return jsonify({'error': 'Sanitizer not initialized'}), 500
            
    except Exception as e:
        log_error(f"Error getting sanitization stats: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500

# ============================================
# DATA DELETION ROUTES
# ============================================

@app.route('/data-deletion')
def data_deletion_page():
    """Serve the data deletion request page"""
    return """
    <html>
        <head>
            <title>Data Deletion - Refiloe</title>
            <meta http-equiv="refresh" content="0; url=https://refiloeradebe.co.za/data-deletion/">
            <style>
                body { font-family: Arial; padding: 40px; text-align: center; }
                .container { max-width: 600px; margin: 0 auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Data Deletion Request</h1>
                <p>Redirecting to data deletion page...</p>
                <p>If you're not redirected, <a href="https://refiloeradebe.co.za/data-deletion/">click here</a>.</p>
            </div>
        </body>
    </html>
    """

@app.route('/api/data-deletion', methods=['POST'])
def handle_data_deletion():
    """Handle data deletion requests from the web form"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('fullName') or not data.get('phone') or not data.get('userType'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Sanitize inputs
        if input_sanitizer:
            # Sanitize phone number
            phone = data['phone'].replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+27' + phone[1:]
                elif phone.startswith('27'):
                    phone = '+' + phone
                else:
                    phone = '+27' + phone
            
            sanitized_phone, phone_valid = input_sanitizer.sanitize_phone_number(phone)
            if not phone_valid:
                return jsonify({'error': 'Invalid phone number'}), 400
            phone = sanitized_phone
            
            # Sanitize name
            sanitized_name, name_valid = input_sanitizer.sanitize_name(data['fullName'])
            if not name_valid:
                return jsonify({'error': 'Invalid name'}), 400
            full_name = sanitized_name
        else:
            # Fallback if sanitizer not available
            phone = data['phone']
            full_name = data['fullName']
        
        # Create deletion request record
        deletion_request = {
            'id': str(uuid.uuid4()),
            'user_type': data['userType'],
            'full_name': full_name,
            'email': data.get('email'),
            'phone': phone,
            'reason': data.get('reason', '')[:500],  # Limit reason length
            'status': 'pending',
            'requested_at': datetime.now().isoformat(),
            'process_by': (datetime.now() + timedelta(days=30)).isoformat(),
            'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr)
        }
        
        # Store in Supabase
        result = supabase.table('data_deletion_requests').insert(deletion_request).execute()
        
        # Log the request
        log_info(f"Data deletion request received: {deletion_request['id']} for {phone}")
        
        # Send WhatsApp confirmation
        if whatsapp_service:
            confirmation_msg = (
                "📋 *Data Deletion Request Received*\n\n"
                f"Dear {full_name},\n\n"
                "We've received your request to delete your data from Refiloe. "
                "Your request will be processed within 30 days as per data protection regulations.\n\n"
                f"Request ID: {deletion_request['id'][:8].upper()}\n"
                f"Requested on: {datetime.now().strftime('%d %B %Y')}\n\n"
                "You'll receive another message once the deletion is complete.\n\n"
                "If you change your mind, please contact us immediately."
            )
            whatsapp_service.send_message(phone, confirmation_msg)
        
        # Notify trainer if applicable
        if data['userType'] == 'client':
            client_result = supabase.table('clients').select('trainer_id').eq('whatsapp', phone).execute()
            if client_result.data:
                trainer_id = client_result.data[0]['trainer_id']
                trainer_result = supabase.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
                
                if trainer_result.data:
                    trainer_phone = trainer_result.data[0]['whatsapp']
                    trainer_msg = (
                        "⚠️ *Client Data Deletion Request*\n\n"
                        f"Client {full_name} has requested data deletion.\n"
                        f"Phone: {phone}\n\n"
                        "Their data will be deleted within 30 days. "
                        "Please download any important records if needed."
                    )
                    whatsapp_service.send_message(trainer_phone, trainer_msg)
        
        return jsonify({
            'success': True,
            'message': 'Deletion request submitted successfully',
            'request_id': deletion_request['id'][:8].upper()
        }), 200
        
    except Exception as e:
        log_error(f"Error processing deletion request: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500

@app.route('/api/process-deletions', methods=['POST'])
def process_pending_deletions():
    """Admin endpoint to process pending deletion requests"""
    try:
        # Check for admin authorization
        auth_token = request.headers.get('X-Admin-Token')
        if auth_token != os.environ.get('ADMIN_TOKEN'):
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Get all pending deletion requests that are due
        due_date = datetime.now().isoformat()
        pending = supabase.table('data_deletion_requests').select('*').eq(
            'status', 'pending'
        ).lte('process_by', due_date).execute()
        
        processed_count = 0
        failed_count = 0
        
        for request_data in pending.data:
            if process_data_deletion_request(request_data):
                processed_count += 1
            else:
                failed_count += 1
        
        return jsonify({
            'success': True,
            'processed': processed_count,
            'failed': failed_count
        }), 200
        
    except Exception as e:
        log_error(f"Error in deletion processing: {str(e)}")
        return jsonify({'error': 'Processing failed'}), 500

# ============================================
# PAYMENT SPECIFIC ROUTES
# ============================================

@app.route('/payment/success', methods=['GET'])
def payment_success():
    """PayFast payment success redirect"""
    return """
    <html>
        <head>
            <title>Payment Successful - Refiloe</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }
                .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #4CAF50; }
                .emoji { font-size: 48px; margin: 20px 0; }
                .message { color: #666; margin: 20px 0; line-height: 1.6; }
                .button { display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">✅</div>
                <h1>Payment Successful!</h1>
                <div class="message">
                    Your payment has been processed successfully.<br>
                    You'll receive a confirmation on WhatsApp shortly.
                </div>
                <p>You can close this window and return to WhatsApp.</p>
                <a href="https://wa.me/" class="button">Open WhatsApp</a>
            </div>
        </body>
    </html>
    """

@app.route('/payment/cancel', methods=['GET'])
def payment_cancel():
    """PayFast payment cancelled redirect"""
    return """
    <html>
        <head>
            <title>Payment Cancelled - Refiloe</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }
                .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #f44336; }
                .emoji { font-size: 48px; margin: 20px 0; }
                .message { color: #666; margin: 20px 0; line-height: 1.6; }
                .button { display: inline-block; padding: 12px 30px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">❌</div>
                <h1>Payment Cancelled</h1>
                <div class="message">
                    Your payment was cancelled.<br>
                    No charges have been made to your account.
                </div>
                <p>You can try again or contact your trainer for assistance.</p>
                <a href="https://wa.me/" class="button">Return to WhatsApp</a>
            </div>
        </body>
    </html>
    """

@app.route('/payment/token-success', methods=['GET'])
def token_success():
    """PayFast token creation success"""
    return """
    <html>
        <head>
            <title>Payment Method Saved - Refiloe</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }
                .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #4CAF50; }
                .emoji { font-size: 48px; margin: 20px 0; }
                .message { color: #666; margin: 20px 0; line-height: 1.6; }
                .features { text-align: left; margin: 30px auto; max-width: 300px; }
                .feature { margin: 10px 0; color: #666; }
                .button { display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">💳</div>
                <h1>Payment Method Saved!</h1>
                <div class="message">
                    Your card has been securely saved with PayFast.
                </div>
                <div class="features">
                    <div class="feature">✅ Quick payments via WhatsApp</div>
                    <div class="feature">✅ No need to enter card details again</div>
                    <div class="feature">✅ Secure and encrypted</div>
                    <div class="feature">✅ You approve each payment</div>
                </div>
                <p>You can close this window.</p>
                <a href="https://wa.me/" class="button">Back to WhatsApp</a>
            </div>
        </body>
    </html>
    """

@app.route('/payment/dashboard/<trainer_id>', methods=['GET'])
def payment_dashboard(trainer_id):
    """Simple payment dashboard for trainers"""
    try:
        if not supabase:
            return "Database not connected", 500
            
        # Get dashboard data using the view
        dashboard = supabase.from_('trainer_payment_dashboard').select('*').eq(
            'trainer_id', trainer_id
        ).single().execute()
        
        if dashboard.data:
            plan_color = '#4CAF50' if dashboard.data.get('plan_name') == 'Professional' else '#FF9800'
            return f"""
            <html>
                <head>
                    <title>Payment Dashboard - Refiloe</title>
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                            padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            margin: 0;
                        }}
                        .container {{
                            max-width: 1200px;
                            margin: 0 auto;
                        }}
                        h1 {{ 
                            color: white; 
                            margin-bottom: 30px;
                            font-size: 32px;
                        }}
                        h2 {{ 
                            color: white;
                            font-weight: 300;
                            margin-top: 0;
                        }}
                        .stats-grid {{ 
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                            gap: 20px;
                            margin-bottom: 30px;
                        }}
                        .stat {{ 
                            background: white;
                            padding: 25px;
                            border-radius: 10px;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            transition: transform 0.2s;
                        }}
                        .stat:hover {{
                            transform: translateY(-5px);
                            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
                        }}
                        .stat h3 {{ 
                            margin: 0; 
                            color: #666;
                            font-size: 14px;
                            text-transform: uppercase;
                            letter-spacing: 1px;
                        }}
                        .stat p {{ 
                            margin: 10px 0 0 0; 
                            font-size: 28px; 
                            font-weight: bold;
                            color: #333;
                        }}
                        .stat.plan {{ background: {plan_color}; }}
                        .stat.plan h3, .stat.plan p {{ color: white; }}
                        .revenue {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                        .revenue h3, .revenue p {{ color: white; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>💳 Payment Dashboard</h1>
                        <h2>{dashboard.data.get('trainer_name', 'Trainer')}</h2>
                        
                        <div class="stats-grid">
                            <div class="stat plan">
                                <h3>Current Plan</h3>
                                <p>{dashboard.data.get('plan_name', 'Starter')}</p>
                            </div>
                            
                            <div class="stat">
                                <h3>Total Clients</h3>
                                <p>{dashboard.data.get('total_clients', 0)}</p>
                            </div>
                            
                            <div class="stat">
                                <h3>Payment Methods Saved</h3>
                                <p>{dashboard.data.get('clients_with_tokens', 0)}</p>
                            </div>
                            
                            <div class="stat">
                                <h3>Pending Payments</h3>
                                <p>{dashboard.data.get('pending_payments', 0)}</p>
                            </div>
                            
                            <div class="stat">
                                <h3>Paid This Month</h3>
                                <p>{dashboard.data.get('paid_this_month', 0)}</p>
                            </div>
                            
                            <div class="stat revenue">
                                <h3>Revenue This Month</h3>
                                <p>R{dashboard.data.get('revenue_this_month', 0) or 0:.2f}</p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """
        else:
            return """
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Dashboard Not Found</h1>
                    <p>Please check the trainer ID and try again.</p>
                </body>
            </html>
            """, 404
            
    except Exception as e:
        log_error(f"Dashboard error: {str(e)}")
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>Error Loading Dashboard</h1>
                <p>{str(e)}</p>
            </body>
        </html>
        """, 500

@app.route('/health')
def health_check():
    """Health check endpoint with security status"""
    try:
        # Get sanitizer stats if available
        if input_sanitizer:
            sanitizer_stats = input_sanitizer.get_sanitization_stats()
            sanitizer_status = {
                'status': 'active',
                'messages_processed': sanitizer_stats['total_processed'],
                'threats_blocked': sanitizer_stats['blocked_total'],
                'block_rate': f"{sanitizer_stats['block_rate']:.2f}%"
            }
        else:
            sanitizer_status = {'status': 'not initialized'}
        
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
                'payment_manager': 'initialized' if payment_manager else 'not initialized',
                'payment_integration': 'initialized' if payment_integration else 'not initialized',
                'payment_scheduler': 'running' if payment_scheduler and payment_scheduler.running else 'stopped',
                'rate_limiter': 'active' if rate_limiter else 'not initialized',
                'input_sanitizer': 'active' if input_sanitizer else 'not initialized',  # NEW
                'ai_model': config.AI_MODEL if hasattr(config, 'AI_MODEL') else 'not configured',
            },
            'version': '3.3.0',  # Updated version with input sanitization
            'errors_today': logger.get_error_count_today() if logger else 0,
            'security_features': {
                'rate_limiting': config.ENABLE_RATE_LIMITING if hasattr(config, 'ENABLE_RATE_LIMITING') else False,
                'webhook_verification': True,
                'input_sanitization': sanitizer_status,  # NEW
                'message_rate_limit': config.MESSAGE_RATE_LIMIT if hasattr(config, 'MESSAGE_RATE_LIMIT') else 0,
                'payment_rate_limit': config.PAYMENT_REQUEST_RATE_LIMIT if hasattr(config, 'PAYMENT_REQUEST_RATE_LIMIT') else 0,
            },
            'payment_features': {
                'tokenization': True,
                'subscriptions': True,
                'auto_payments': True,
                'reminders': payment_scheduler.running if payment_scheduler else False
            },
            'privacy_features': {
                'data_deletion': True,
                'popia_compliant': True,
                'gdpr_ready': True
            }
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
