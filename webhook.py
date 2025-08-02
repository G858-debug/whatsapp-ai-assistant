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
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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

# Initialize scheduler for automated tasks
scheduler = BackgroundScheduler()
scheduler.start()

# South African timezone
SA_TZ = pytz.timezone('Africa/Johannesburg')

@app.route('/')
def home():
    return "Proactive Multi-Trainer AI Assistant! 💪🤖👥⚡"

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
    
    # Enhanced ADD CLIENT with automatic onboarding
    if message_lower.startswith('add client'):
        return process_add_client(trainer, message_text)
    
    elif any(word in message_lower for word in ['my clients', 'list clients', 'show clients']):
        return get_trainer_clients(trainer['id'])
    
    elif any(word in message_lower for word in ['my schedule', 'today', 'tomorrow', 'bookings']):
        return get_trainer_schedule(trainer['id'])
    
    elif any(word in message_lower for word in ['revenue', 'payments', 'money']):
        return get_trainer_revenue(trainer['id'])
    
    elif any(word in message_lower for word in ['send reminders', 'remind clients']):
        return trigger_manual_reminders(trainer['id'])
    
    elif any(word in message_lower for word in ['help', 'commands', 'what can you do']):
        return get_trainer_help_menu()
    
    else:
        # Use Claude AI for general trainer assistance
        return process_trainer_ai_request(trainer, message_text)

def process_add_client(trainer, message_text):
    """Process ADD CLIENT command with automatic onboarding"""
    
    try:
        # Parse client details from message
        lines = message_text.split('\n')
        client_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'name' in key:
                    client_data['name'] = value
                elif 'whatsapp' in key:
                    # Clean phone number
                    whatsapp = re.sub(r'[^\d]', '', value)
                    if whatsapp.startswith('0'):
                        whatsapp = '27' + whatsapp[1:]
                    client_data['whatsapp'] = whatsapp
                elif 'email' in key:
                    client_data['email'] = value
                elif 'package' in key:
                    client_data['package_type'] = value
        
        # Validate required fields
        if not all(k in client_data for k in ['name', 'whatsapp']):
            return """❌ Missing required information. Please use this format:

ADD CLIENT
Name: [Client Name]
WhatsApp: [Client Number]
Email: [Client Email]
Package: [4-pack / 8-pack / monthly]

Example:
ADD CLIENT
Name: Sarah Johnson  
WhatsApp: 0831234567
Email: sarah@email.com
Package: 8-pack"""
        
        # Set default sessions based on package
        sessions_map = {
            'single': 1,
            '4-pack': 4,
            '8-pack': 8,
            'monthly': 8
        }
        
        package = client_data.get('package_type', 'single').lower()
        sessions = sessions_map.get(package, 1)
        
        # Add client to database
        client_record = {
            'trainer_id': trainer['id'],
            'name': client_data['name'],
            'whatsapp': client_data['whatsapp'],
            'email': client_data.get('email'),
            'sessions_remaining': sessions,
            'package_type': package,
            'status': 'active'
        }
        
        result = supabase.table('clients').insert(client_record).execute()
        
        if result.data:
            client_id = result.data[0]['id']
            
            # Trigger automatic onboarding
            threading.Thread(
                target=send_client_onboarding,
                args=(client_data['whatsapp'], client_data['name'], trainer, sessions)
            ).start()
            
            return f"""✅ *Client Added Successfully!*

*{client_data['name']}* has been added to your client list.

📱 I'm now sending them a welcome message and will help them book their first session!

*Package:* {package.title()}
*Sessions:* {sessions}
*WhatsApp:* {client_data['whatsapp']}"""
        
        else:
            return "❌ Failed to add client. Please try again."
    
    except Exception as e:
        print(f"Error processing add client: {str(e)}")
        return "❌ Error adding client. Please check the format and try again."

def send_client_onboarding(client_whatsapp, client_name, trainer, sessions):
    """Send automated onboarding sequence to new client"""
    
    try:
        # Wait a moment to avoid rate limiting
        import time
        time.sleep(2)
        
        # Welcome message
        welcome_msg = f"""👋 Hi {client_name}!

Welcome to {trainer['business_name'] or trainer['name']}'s personal training! 

I'm your AI assistant and I'll help you:
✅ Book training sessions
✅ Reschedule when needed  
✅ Track your progress
✅ Handle payments

*Your Package:* {sessions} sessions
*Price per session:* R{trainer['pricing_per_session']:.0f}

Ready to book your first session? Just reply with "BOOK SESSION" and I'll show you available times! 💪"""
        
        send_whatsapp_message(client_whatsapp, welcome_msg)
        
        # Follow-up after 30 seconds with availability
        time.sleep(30)
        
        availability_msg = f"""📅 *Available Times This Week:*

**Monday:** 9am, 2pm, 5pm
**Tuesday:** 10am, 1pm, 4pm  
**Wednesday:** 8am, 12pm, 3pm
**Thursday:** 9am, 2pm, 5pm
**Friday:** 10am, 1pm, 4pm

Which day and time works best for your first session?

You can also ask:
• "When are you free?" - See more times
• "What about next week?" - Future availability  
• "Help" - See all commands

Looking forward to your first workout! 🏋️‍♀️"""
        
        send_whatsapp_message(client_whatsapp, availability_msg)
        
        # Update client record with onboarding completion
        supabase.table('clients').update({
            'next_session_due': (datetime.now(SA_TZ) + timedelta(days=1)).isoformat()
        }).eq('whatsapp', client_whatsapp).execute()
        
    except Exception as e:
        print(f"Error in client onboarding: {str(e)}")

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
    
    elif any(word in message_lower for word in ['sessions left', 'balance', 'remaining']):
        return get_client_session_balance(client)
    
    elif any(word in message_lower for word in ['help', 'commands']):
        return get_client_help_menu(client['name'])
    
    else:
        # Use Claude AI for general client assistance
        return process_client_ai_request(client, trainer, message_text)

def handle_client_booking(client, trainer, message_text):
    """Handle client booking request with real-time availability"""
    
    try:
        # Check if they have sessions remaining
        if client['sessions_remaining'] <= 0:
            return f"""Hi {client['name']}! 

You've used all your sessions from your {client['package_type']} package. 

To book more sessions, please:
1. Contact {trainer['name']} about purchasing a new package
2. Or pay for individual sessions at R{trainer['pricing_per_session']:.0f} each

Would you like me to let {trainer['name']} know you're interested in more sessions? 💪"""
        
        return f"""Hi {client['name']}! 👋

Perfect! I'd love to help you book a session with {trainer['name']}.

📅 *Available Times This Week:*

**Monday:** 9am, 2pm, 5pm
**Tuesday:** 10am, 1pm, 4pm  
**Wednesday:** 8am, 12pm, 3pm
**Thursday:** 9am, 2pm, 5pm
**Friday:** 10am, 1pm, 4pm
**Saturday:** 9am, 12pm

*Example:* Just say "Tuesday 2pm" or "Friday morning"

*Your package:* {client['sessions_remaining']} sessions remaining
*Price:* Included in your {client['package_type']} package

Which time works best for you? 🏋️‍♀️"""
    
    except Exception as e:
        print(f"Error handling client booking: {str(e)}")
        return f"Hi {client['name']}! I'd love to help you book a session. Let me check availability..."

def get_client_session_balance(client):
    """Get client's session balance and package info"""
    
    return f"""📊 *Your Session Summary:*

*Name:* {client['name']}
*Package:* {client['package_type'].title()}
*Sessions Remaining:* {client['sessions_remaining']}

*Last Session:* {client['last_session_date'].split('T')[0] if client['last_session_date'] else 'None yet'}

Ready to book your next session? Just say "BOOK SESSION"! 💪"""

def get_client_help_menu(client_name):
    """Get help menu for clients"""
    
    return f"""🤖 *Hi {client_name}! Here's what I can help with:*

**Booking:**
• "Book session" - See available times
• "Tuesday 2pm" - Book specific time
• "When are you free?" - Check availability

**Managing Sessions:**
• "Reschedule" - Move existing booking
• "Cancel session" - Cancel booking
• "My sessions" - See upcoming bookings

**Account Info:**
• "Sessions left" - Check your balance
• "My package" - Package details

**General:**
• Just ask naturally! I understand context.

What would you like to do? 😊"""

def get_trainer_revenue(trainer_id):
    """Get trainer revenue summary"""
    
    try:
        # Get this month's revenue
        now = datetime.now(SA_TZ)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        payments_result = supabase.table('payments').select('amount, status').eq('trainer_id', trainer_id).gte('created_at', month_start.isoformat()).execute()
        
        total_revenue = sum(p['amount'] for p in payments_result.data if p['status'] == 'paid')
        pending_revenue = sum(p['amount'] for p in payments_result.data if p['status'] == 'pending')
        
        # Get active clients count
        clients_result = supabase.table('clients').select('id').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        active_clients = len(clients_result.data)
        
        return f"""💰 *Revenue Summary - {now.strftime('%B %Y')}*

*This Month:*
• Revenue Received: R{total_revenue:.2f}
• Pending Payments: R{pending_revenue:.2f}
• Total Potential: R{total_revenue + pending_revenue:.2f}

*Business Stats:*
• Active Clients: {active_clients}
• Average per Client: R{(total_revenue/active_clients) if active_clients > 0 else 0:.2f}

*Quick Actions:*
• "Send payment reminders" - Follow up on overdue
• "Client stats" - Detailed client analytics"""
        
    except Exception as e:
        print(f"Error getting trainer revenue: {str(e)}")
        return "Having trouble accessing revenue data. Please try again."

def trigger_manual_reminders(trainer_id):
    """Manually trigger reminders for a trainer's clients"""
    
    try:
        # Get clients who need reminders
        clients_result = supabase.table('clients').select('name, whatsapp').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        reminder_count = 0
        for client in clients_result.data:
            # Send session reminder
            reminder_msg = f"""⏰ *Session Reminder*

Hi {client['name']}! 

It's been a while since your last session. Ready to get back into your fitness routine?

I have these times available:
• Tomorrow: 10am, 2pm, 5pm
• Day after: 9am, 1pm, 4pm

Which works better for you? 💪

(Reply "Not ready yet" if you need more time)"""
            
            send_whatsapp_message(client['whatsapp'], reminder_msg)
            reminder_count += 1
        
        return f"✅ Sent session reminders to {reminder_count} clients!"
        
    except Exception as e:
        print(f"Error sending manual reminders: {str(e)}")
        return "Having trouble sending reminders. Please try again."

# Rest of the functions remain the same as previous version...
# (get_trainer_clients, get_trainer_schedule, get_trainer_help_menu, etc.)

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
• "Add client" - Add new client (auto-onboards!)
• "My clients" - List active clients  
• "Send reminders" - Manual reminder blast

**Scheduling:**
• "My schedule" - Upcoming sessions
• "Today" - Today's sessions
• "Revenue" - Financial summary

**Automated Features:**
• Clients get welcomed automatically
• Session reminders sent weekly
• Payment follow-ups handled
• Booking requests processed 24/7

**General:**
• Just type naturally! I understand context and can help with all aspects of your training business.

What would you like help with? 💪"""

def get_trainer_availability(trainer_id, client):
    """Get real-time trainer availability"""
    
    return f"""Hi {client['name']}! Here are the available times:

📅 *Available Sessions:*

**This Week:**
• Monday: 9am, 2pm, 5pm
• Tuesday: 10am, 1pm, 4pm
• Wednesday: 8am, 12pm, 3pm  
• Thursday: 9am, 2pm, 5pm
• Friday: 10am, 1pm, 4pm
• Saturday: 9am, 12pm

**Next Week:**
• Monday: 9am, 1pm, 3pm
• Tuesday: 10am, 2pm, 5pm

*Sessions remaining:* {client['sessions_remaining']}

Just tell me which day and time works! 🕐"""

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
• Manage client bookings automatically
• Handle scheduling 24/7  
• Send automated reminders
• Track payments and sessions

If you're a **client**, your trainer needs to add you to the system first.

Reply "TRAINER" if you want to register as a trainer!"""

# Utility functions...
def process_trainer_ai_request(trainer, message_text):
    """Process trainer request with Claude AI"""
    
    if not ANTHROPIC_API_KEY:
        return "AI processing is being configured. Please use specific commands for now."
    
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
        'scheduler': 'running' if scheduler.running else 'stopped',
        'version': 'proactive_v1'
    })

# Automated reminder functions
def send_daily_reminders():
    """Send daily reminders to clients who need sessions"""
    
    if not supabase:
        return
    
    try:
        # Get clients who haven't had a session in 7+ days
        week_ago = (datetime.now(SA_TZ) - timedelta(days=7)).isoformat()
        
        clients_result = supabase.table('clients').select('*, trainers(*)').eq('status', 'active').lt('last_session_date', week_ago).execute()
        
        for client in clients_result.data:
            trainer = client['trainers']
            
            reminder_msg = f"""💪 *Stay Strong, {client['name']}!*

It's been a week since your last session with {trainer['name']}. 

Ready to get back on track? I have these times available:

📅 *Tomorrow:*
• 9am, 2pm, 5pm

📅 *This Week:*  
• Tuesday: 10am, 1pm, 4pm
• Wednesday: 8am, 12pm, 3pm
• Thursday: 9am, 2pm, 5pm

*Sessions remaining:* {client['sessions_remaining']}

Which time works for you? 🏋️‍♀️

(Reply "Remind me later" if you need more time)"""
            
            send_whatsapp_message(client['whatsapp'], reminder_msg)
            
        print(f"Sent daily reminders to {len(clients_result.data)} clients")
        
    except Exception as e:
        print(f"Error sending daily reminders: {str(e)}")

def send_payment_reminders():
    """Send payment reminders for overdue amounts"""
    
    if not supabase:
        return
    
    try:
        # Get overdue payments
        today = datetime.now(SA_TZ).date()
        
        payments_result = supabase.table('payments').select('*, clients(*), trainers(*)').eq('status', 'pending').lt('due_date', today.isoformat()).execute()
        
        for payment in payments_result.data:
            client = payment['clients']
            trainer = payment['trainers']
            
            payment_msg = f"""💳 *Payment Reminder*

Hi {client['name']}!

Your payment of R{payment['amount']:.2f} for {trainer['name']}'s training sessions was due on {payment['due_date']}.

*Payment Options:*
• Cash at your next session
• EFT: [Bank details would go here]
• Card payment: [Link would go here]

Please let me know when you've made the payment so I can update your account.

Thanks! 😊"""
            
            send_whatsapp_message(client['whatsapp'], payment_msg)
            
        print(f"Sent payment reminders for {len(payments_result.data)} overdue payments")
        
    except Exception as e:
        print(f"Error sending payment reminders: {str(e)}")

def send_session_confirmations():
    """Send 24-hour session confirmations"""
    
    if not supabase:
        return
    
    try:
        # Get sessions happening tomorrow
        tomorrow = (datetime.now(SA_TZ) + timedelta(days=1)).date()
        day_after = tomorrow + timedelta(days=1)
        
        bookings_result = supabase.table('bookings').select('*, clients(*), trainers(*)').eq('status', 'scheduled').gte('session_datetime', tomorrow.isoformat()).lt('session_datetime', day_after.isoformat()).execute()
        
        for booking in bookings_result.data:
            client = booking['clients']
            trainer = booking['trainers']
            session_time = datetime.fromisoformat(booking['session_datetime'])
            
            confirmation_msg = f"""⏰ *Session Reminder*

Hi {client['name']}!

This is a friendly reminder about your training session tomorrow:

📅 *Tomorrow ({session_time.strftime('%A, %d %B')})*
🕐 *Time:* {session_time.strftime('%I:%M %p')}
👨‍💼 *Trainer:* {trainer['name']}
💰 *Price:* R{booking['price']:.2f}

Reply:
• "CONFIRM" - if you're coming
• "RESCHEDULE" - if you need to change time
• "CANCEL" - if you can't make it

See you tomorrow! 💪"""
            
            send_whatsapp_message(client['whatsapp'], confirmation_msg)
            
        print(f"Sent session confirmations for {len(bookings_result.data)} upcoming sessions")
        
    except Exception as e:
        print(f"Error sending session confirmations: {str(e)}")

# Schedule automated tasks
try:
    # Daily reminders at 9 AM
    scheduler.add_job(
        func=send_daily_reminders,
        trigger=CronTrigger(hour=9, minute=0, timezone=SA_TZ),
        id='daily_reminders',
        name='Send daily session reminders',
        replace_existing=True
    )
    
    # Payment reminders at 10 AM on weekdays
    scheduler.add_job(
        func=send_payment_reminders,
        trigger=CronTrigger(hour=10, minute=0, day_of_week='0-4', timezone=SA_TZ),
        id='payment_reminders',
        name='Send payment reminders',
        replace_existing=True
    )
    
    # Session confirmations at 6 PM
    scheduler.add_job(
        func=send_session_confirmations,
        trigger=CronTrigger(hour=18, minute=0, timezone=SA_TZ),
        id='session_confirmations',
        name='Send 24h session confirmations',
        replace_existing=True
    )
    
    print("✅ Automated reminder schedules configured")
    
except Exception as e:
    print(f"❌ Error setting up automated schedules: {e}")

# Admin endpoints
@app.route('/add_trainer', methods=['POST'])
def add_trainer():
    """Add a new trainer"""
    
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

@app.route('/trigger_reminders/<trainer_id>')
def trigger_reminders_endpoint(trainer_id):
    """Manually trigger reminders for a specific trainer"""
    
    try:
        # Get trainer's clients
        clients_result = supabase.table('clients').select('*, trainers(*)').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        sent_count = 0
        for client in clients_result.data:
            trainer = client['trainers']
            
            reminder_msg = f"""💪 *Quick Check-in!*

Hi {client['name']}! 

{trainer['name']} wanted me to reach out and see how you're doing with your fitness goals.

Ready for your next session? I have these times available:

📅 *This Week:*
• Tomorrow: 10am, 2pm, 5pm
• Day after: 9am, 1pm, 4pm

*Sessions remaining:* {client['sessions_remaining']}

Which works better for you? 🏋️‍♀️"""
            
            send_whatsapp_message(client['whatsapp'], reminder_msg)
            sent_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Sent reminders to {sent_count} clients'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Handle shutdown gracefully
import atexit
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
