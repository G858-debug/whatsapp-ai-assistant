from flask import Flask, request, jsonify
import os
import requests
import json
from datetime import datetime, timedelta
import pytz
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from supabase import create_client, Client
import re

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase: {e}")

# South African timezone
SA_TZ = pytz.timezone('Africa/Johannesburg')

@app.route('/')
def home():
    return "Multi-Trainer AI Assistant Platform! 💪🤖👥"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge
    else:
        print("Webhook verification failed!")
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages for multi-trainer system"""
    try:
        data = request.get_json()
        print("=== WEBHOOK DATA ===")
        print(json.dumps(data, indent=2))
        
        # Check if this is a message
        if (data.get('entry') and 
            data['entry'][0].get('changes') and 
            data['entry'][0]['changes'][0].get('value', {}).get('messages')):
            
            messages = data['entry'][0]['changes'][0]['value']['messages']
            
            for message in messages:
                phone_number = message['from']
                message_id = message['id']
                
                # Handle text messages
                if 'text' in message:
                    message_text = message['text']['body']
                    print(f"Text message from {phone_number}: {message_text}")
                    
                    # Process message with multi-trainer logic
                    response = process_multi_trainer_message(phone_number, message_text)
                    send_whatsapp_message(phone_number, response)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_multi_trainer_message(phone_number, message_text):
    """Process message in multi-trainer context"""
    
    if not supabase:
        return "System is initializing. Please try again in a moment."
    
    try:
        # Log the message
        log_message(phone_number, message_text, 'incoming')
        
        # Determine who is messaging: trainer or client?
        sender_context = identify_sender(phone_number)
        
        if sender_context['type'] == 'trainer':
            return handle_trainer_message(sender_context, message_text)
        elif sender_context['type'] == 'client':
            return handle_client_message(sender_context, message_text)
        else:
            return handle_unknown_sender(phone_number, message_text)
    
    except Exception as e:
        print(f"Error processing multi-trainer message: {str(e)}")
        return "I'm having trouble processing your message. Please try again."

def identify_sender(phone_number):
    """Identify if sender is a trainer, client, or unknown"""
    
    try:
        # Check if it's a trainer
        trainer_result = supabase.table('trainers').select('*').eq('whatsapp', phone_number).execute()
        
        if trainer_result.data:
            return {
                'type': 'trainer',
                'data': trainer_result.data[0]
            }
        
        # Check if it's a client
        client_result = supabase.table('clients').select('*, trainers(*)').eq('whatsapp', phone_number).execute()
        
        if client_result.data:
            return {
                'type': 'client',
                'data': client_result.data[0]
            }
        
        # Unknown sender
        return {'type': 'unknown', 'data': None}
    
    except Exception as e:
        print(f"Error identifying sender: {str(e)}")
        return {'type': 'unknown', 'data': None}

def handle_trainer_message(trainer_context, message_text):
    """Handle messages from trainers (admin/management functions)"""
    
    trainer = trainer_context['data']
    message_lower = message_text.lower()
    
    # Trainer commands
    if any(word in message_lower for word in ['add client', 'new client', 'register client']):
        return handle_add_client_request(trainer, message_text)
    
    elif any(word in message_lower for word in ['my clients', 'list clients', 'show clients']):
        return get_trainer_clients(trainer['id'])
    
    elif any(word in message_lower for word in ['my schedule', 'today', 'tomorrow', 'bookings']):
        return get_trainer_schedule(trainer['id'])
    
    elif any(word in message_lower for word in ['help', 'commands', 'what can you do']):
        return get_trainer_help_menu()
    
    else:
        # Use Claude AI for general trainer assistance
        return process_trainer_ai_request(trainer, message_text)

def handle_client_message(client_context, message_text):
    """Handle messages from clients (booking, scheduling, etc.)"""
    
    client = client_context['data']
    trainer = client['trainers']
    message_lower = message_text.lower()
    
    # Client intents
    if any(word in message_lower for word in ['book', 'schedule', 'appointment', 'session']):
        return handle_client_booking(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['reschedule', 'move', 'change time']):
        return handle_client_reschedule(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['cancel', "can't make it", 'sick']):
        return handle_client_cancellation(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['available', 'free times', 'when']):
        return get_trainer_availability(trainer['id'], client)
    
    else:
        # Use Claude AI for general client assistance
        return process_client_ai_request(client, trainer, message_text)

def handle_unknown_sender(phone_number, message_text):
    """Handle messages from unknown senders"""
    
    message_lower = message_text.lower()
    
    if any(word in message_lower for word in ['trainer', 'register', 'sign up', 'join']):
        return """👋 Hi! Welcome to the AI Personal Training Assistant!

To register as a trainer:
1. Visit our website: [coming soon]
2. Or reply with: "REGISTER TRAINER [Your Name] [Your Email]"

Example: "REGISTER TRAINER John Smith john@email.com"

For existing trainers, your clients can start booking immediately once you've added them to the system!"""
    
    else:
        return """👋 Hi! I'm an AI assistant for personal trainers.

If you're a **personal trainer**, I can help you:
• Manage client bookings
• Handle scheduling automatically  
• Track payments and sessions

If you're a **client**, your trainer needs to add you to the system first.

Reply "TRAINER" if you want to register as a trainer!"""

def handle_add_client_request(trainer, message_text):
    """Help trainer add a new client"""
    
    return f"""To add a new client, please provide their details in this format:

*ADD CLIENT*
Name: [Client Name]
WhatsApp: [Client WhatsApp Number]
Email: [Client Email]
Package: [4-pack / 8-pack / monthly / single]

Example:
ADD CLIENT
Name: Sarah Johnson
WhatsApp: 0831234567
Email: sarah@email.com
Package: 8-pack

I'll then contact them directly to start booking sessions! 📱"""

def get_trainer_clients(trainer_id):
    """Get list of trainer's clients"""
    
    try:
        clients_result = supabase.table('clients').select('name, whatsapp, sessions_remaining, status, last_session_date').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        if not clients_result.data:
            return "You don't have any active clients yet. Use 'ADD CLIENT' to get started!"
        
        response = "📋 *Your Active Clients:*\n\n"
        
        for client in clients_result.data:
            last_session = client['last_session_date']
            last_session_text = f"Last: {datetime.fromisoformat(last_session).strftime('%d %b')}" if last_session else "No sessions yet"
            
            response += f"• *{client['name']}*\n"
            response += f"  Sessions left: {client['sessions_remaining']}\n"
            response += f"  {last_session_text}\n\n"
        
        return response
    
    except Exception as e:
        print(f"Error getting trainer clients: {str(e)}")
        return "Having trouble accessing client list. Please try again."

def get_trainer_schedule(trainer_id):
    """Get trainer's upcoming bookings"""
    
    try:
        # Get next 7 days of bookings
        now = datetime.now(SA_TZ)
        week_later = now + timedelta(days=7)
        
        bookings_result = supabase.table('bookings').select('session_datetime, clients(name), session_type, status').eq('trainer_id', trainer_id).gte('session_datetime', now.isoformat()).lte('session_datetime', week_later.isoformat()).order('session_datetime').execute()
        
        if not bookings_result.data:
            return "📅 No upcoming sessions in the next 7 days.\n\nYour calendar is free for new bookings!"
        
        response = "📅 *Your Upcoming Sessions:*\n\n"
        
        for booking in bookings_result.data:
            session_time = datetime.fromisoformat(booking['session_datetime'])
            day = session_time.strftime('%A, %d %B')
            time = session_time.strftime('%I:%M %p')
            client_name = booking['clients']['name']
            
            response += f"• *{day}*\n"
            response += f"  {time} - {client_name}\n"
            response += f"  Status: {booking['status'].title()}\n\n"
        
        return response
    
    except Exception as e:
        print(f"Error getting trainer schedule: {str(e)}")
        return "Having trouble accessing your schedule. Please try again."

def get_trainer_help_menu():
    """Get help menu for trainers"""
    
    return """🤖 *AI Assistant Commands:*

**Client Management:**
• "Add client" - Add new client
• "My clients" - List active clients  
• "Client stats" - Client analytics

**Scheduling:**
• "My schedule" - Upcoming sessions
• "Today" - Today's sessions
• "Availability" - Free time slots

**Business:**
• "Revenue" - Payment summary
• "Settings" - Update preferences

**General:**
• Just type naturally! I understand context and can help with scheduling, client communication, and business tasks.

What would you like help with? 💪"""

def handle_client_booking(client, trainer, message_text):
    """Handle client booking request"""
    
    return f"""Hi {client['name']}! 👋

I'd love to help you book a session with {trainer['business_name'] or trainer['name']}.

Let me check available times... 

*Available this week:*
• Monday 10am, 2pm, 4pm
• Tuesday 9am, 11am, 3pm  
• Wednesday 8am, 1pm, 5pm
• Thursday 10am, 2pm, 4pm
• Friday 9am, 12pm, 3pm

Which time works best for you?

(Sessions are R{trainer['pricing_per_session']:.0f} each. You have {client['sessions_remaining']} sessions remaining.) 💪"""

def get_trainer_availability(trainer_id, client):
    """Get real-time trainer availability"""
    
    # This would integrate with Google Calendar
    return f"""Hi {client['name']}! Here are the available times for this week:

📅 *Available Sessions:*

**This Week:**
• Monday: 10am, 2pm, 4pm
• Tuesday: 9am, 11am, 3pm
• Wednesday: 8am, 1pm, 5pm  
• Thursday: 10am, 2pm, 4pm
• Friday: 9am, 12pm, 3pm

**Next Week:**
• Monday: 9am, 1pm, 3pm
• Tuesday: 10am, 2pm, 5pm

Just tell me which day and time works for you! 🕐"""

def process_trainer_ai_request(trainer, message_text):
    """Process trainer request with Claude AI"""
    
    if not ANTHROPIC_API_KEY:
        return "AI processing is being configured. Please use specific commands for now."
    
    # Claude AI integration for trainer assistance
    prompt = f"""You are an AI assistant for personal trainer "{trainer['name']}" who runs "{trainer['business_name']}". 

Help with:
- Business advice and strategies
- Client management guidance  
- Scheduling optimization
- Revenue and growth tips
- Professional communication

Trainer's message: "{message_text}"

Respond as their business assistant with actionable advice."""
    
    return call_claude_api(prompt)

def process_client_ai_request(client, trainer, message_text):
    """Process client request with Claude AI"""
    
    if not ANTHROPIC_API_KEY:
        return f"Hi {client['name']}! I'm here to help with booking sessions. What would you like to schedule?"
    
    # Claude AI integration for client assistance
    prompt = f"""You are an AI assistant helping client "{client['name']}" communicate with their personal trainer "{trainer['name']}".

You can help with:
- Booking and scheduling sessions
- Rescheduling appointments
- Fitness motivation and encouragement
- General questions about their training

Client's message: "{message_text}"

Respond professionally as the trainer's assistant, being helpful and motivating."""
    
    return call_claude_api(prompt)

def call_claude_api(prompt):
    """Call Claude API with given prompt"""
    
    try:
        claude_url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 300,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(claude_url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        else:
            return "I'm having trouble with AI processing. Please try again."
    
    except Exception as e:
        print(f"Error calling Claude API: {str(e)}")
        return "AI assistance temporarily unavailable. Please try again."

def log_message(phone_number, message_text, direction):
    """Log message to database"""
    
    if not supabase:
        return
    
    try:
        # Determine trainer and client IDs based on phone number
        sender_context = identify_sender(phone_number)
        
        trainer_id = None
        client_id = None
        
        if sender_context['type'] == 'trainer':
            trainer_id = sender_context['data']['id']
        elif sender_context['type'] == 'client':
            client_id = sender_context['data']['id']
            trainer_id = sender_context['data']['trainer_id']
        
        supabase.table('messages').insert({
            'trainer_id': trainer_id,
            'client_id': client_id,
            'whatsapp_from': phone_number if direction == 'incoming' else 'system',
            'whatsapp_to': 'system' if direction == 'incoming' else phone_number,
            'message_text': message_text,
            'direction': direction
        }).execute()
    
    except Exception as e:
        print(f"Error logging message: {str(e)}")

def send_whatsapp_message(phone_number, message_text):
    """Send message back to WhatsApp and log it"""
    
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("Missing ACCESS_TOKEN or PHONE_NUMBER_ID")
        return
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'to': phone_number,
        'text': {'body': message_text}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"WhatsApp API response: {response.status_code} - {response.text}")
        
        # Log outgoing message
        log_message(phone_number, message_text, 'outgoing')
        
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return None

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'claude_api': 'connected' if ANTHROPIC_API_KEY else 'not configured',
        'whatsapp_api': 'configured' if ACCESS_TOKEN and PHONE_NUMBER_ID else 'not configured',
        'supabase': 'connected' if supabase else 'not configured',
        'version': 'multi_trainer_v1'
    })

# Admin endpoints for adding trainers (temporary - will be replaced with web dashboard)
@app.route('/add_trainer', methods=['POST'])
def add_trainer():
    """Add a new trainer (temporary endpoint)"""
    
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        data = request.get_json()
        
        trainer_data = {
            'name': data['name'],
            'whatsapp': data['whatsapp'],
            'email': data['email'],
            'business_name': data.get('business_name', data['name']),
            'pricing_per_session': data.get('pricing_per_session', 300.00)
        }
        
        result = supabase.table('trainers').insert(trainer_data).execute()
        
        return jsonify({
            'success': True,
            'trainer_id': result.data[0]['id'],
            'message': f"Trainer {data['name']} added successfully!"
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
