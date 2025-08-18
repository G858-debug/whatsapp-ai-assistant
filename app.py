from flask import Flask, request, jsonify
import os
from datetime import datetime
import pytz
import json
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

# Payment imports
from payment_manager import PaymentManager
from payment_integration import PaymentIntegration
from payfast_webhook import payfast_webhook_bp

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

log_info(f"Application initialized - Database: {supabase is not None}, WhatsApp: {whatsapp_service is not None}, Refiloe: {refiloe is not None}, Payments: {payment_manager is not None}")

# Register blueprints
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

# ============================================
# SCHEDULED PAYMENT TASKS
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
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 I'm Refiloe</h1>
                <p>Your AI assistant for personal trainers</p>
                <div class="status">✅ System Online</div>
                <div class="payment-status">💳 Payment System Active</div>
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
    """Handle incoming WhatsApp messages with payment integration"""
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
                                    
                                    # Process with payment integration FIRST
                                    if message_text and payment_integration:
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
    """Health check endpoint with payment status"""
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
                'payment_manager': 'initialized' if payment_manager else 'not initialized',
                'payment_integration': 'initialized' if payment_integration else 'not initialized',
                'payment_scheduler': 'running' if payment_scheduler and payment_scheduler.running else 'stopped',
                'ai_model': config.AI_MODEL if hasattr(config, 'AI_MODEL') else 'not configured',
            },
            'version': '3.0.0',  # Updated version with payments
            'errors_today': logger.get_error_count_today() if logger else 0,
            'payment_features': {
                'tokenization': True,
                'subscriptions': True,
                'auto_payments': True,
                'reminders': payment_scheduler.running if payment_scheduler else False
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
