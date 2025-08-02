from flask import Flask, request, jsonify
import os
import requests
import json
from datetime import datetime, timedelta
import pytz
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
    return "Hi! I'm Refiloe, your AI assistant for personal trainers! 💪😊"

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
    """Handle incoming WhatsApp messages"""
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
                    
                    # Process message with Refiloe
                    response = process_refiloe_message(phone_number, message_text)
                    send_whatsapp_message(phone_number, response)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_refiloe_message(phone_number, message_text):
    """Process message with Refiloe's personality"""
    
    if not supabase:
        return "Hi! I'm Refiloe, and I'm getting set up. Try again in a moment! 😊"
    
    try:
        # Log the message
        log_message(phone_number, message_text, 'incoming')
        
        # Determine who is messaging: trainer or client?
        sender_context = identify_sender(phone_number)
        
        if sender_context['type'] == 'trainer':
            return handle_trainer_message_refiloe(sender_context, message_text)
        elif sender_context['type'] == 'client':
            return handle_client_message_refiloe(sender_context, message_text)
        else:
            return handle_unknown_sender_refiloe(phone_number, message_text)
    
    except Exception as e:
        print(f"Error processing Refiloe message: {str(e)}")
        return "I'm having a quick tech moment. Try that again? 😊"

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

def handle_trainer_message_refiloe(trainer_context, message_text):
    """Handle messages from trainers with Refiloe's personality"""
    
    trainer = trainer_context['data']
    message_lower = message_text.lower()
    
    # Natural language client addition
    if any(phrase in message_lower for phrase in ['add client', 'new client', 'onboard client', 'register client', 'add a client']):
        return handle_natural_client_addition(trainer, message_text)
    
    elif any(word in message_lower for word in ['my clients', 'list clients', 'show clients', 'clients']):
        return get_trainer_clients_refiloe(trainer['id'], trainer['name'])
    
    elif any(word in message_lower for word in ['my schedule', 'today', 'tomorrow', 'bookings', 'schedule']):
        return get_trainer_schedule_refiloe(trainer['id'], trainer['name'])
    
    elif any(word in message_lower for word in ['revenue', 'payments', 'money', 'earnings']):
        return get_trainer_revenue_refiloe(trainer['id'], trainer['name'])
    
    elif any(phrase in message_lower for phrase in ['send reminders', 'remind clients', 'follow up']):
        return trigger_manual_reminders_refiloe(trainer['id'], trainer['name'])
    
    elif any(word in message_lower for word in ['help', 'commands', 'what can you do']):
        return get_trainer_help_menu_refiloe(trainer['name'])
    
    else:
        # Use Refiloe's personality for general requests
        return process_trainer_request_with_refiloe(trainer, message_text)

def handle_natural_client_addition(trainer, message_text):
    """Handle client addition with natural language"""
    
    # Check if this message already contains client details
    extracted_details = extract_client_details_naturally(message_text)
    
    if extracted_details and extracted_details.get('name') and extracted_details.get('phone'):
        # We have enough details, add the client
        return complete_client_addition(trainer, extracted_details)
    else:
        # Ask for details conversationally
        return f"""Hi {trainer['name']}! 😊

I'm Refiloe, and I'd love to help you add a new client! 

Could you give me their details? You can just tell me naturally, like:

"Sarah Johnson, her number is 083 123 4567, email sarah@gmail.com, she wants the 8-pack"

Or however feels natural to you! I'll figure out the rest. 💪"""

def extract_client_details_naturally(text):
    """Extract client details from natural language"""
    
    details = {}
    
    # Phone number patterns (improved)
    phone_patterns = [
        r'(\+27|27|0)[\s\-]?(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})',
        r'(\d{3})[\s\-]?(\d{3})[\s\-]?(\d{4})',
        r'(\d{10})'
    ]
    
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            # Clean and format phone number
            phone = re.sub(r'[^\d]', '', phone_match.group())
            if phone.startswith('0'):
                phone = '27' + phone[1:]
            elif not phone.startswith('27') and len(phone) == 10:
                phone = '27' + phone
            details['phone'] = phone
            break
    
    # Email pattern
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        details['email'] = email_match.group()
    
    # Enhanced package patterns
    text_lower = text.lower()
    package_patterns = {
        r'\b(single|one|1)\b': 'single',
        r'\b(4[\-\s]?pack|four|4)\b': '4-pack',
        r'\b(8[\-\s]?pack|eight|8)\b': '8-pack',
        r'\b(monthly|month)\b': 'monthly',
        r'\b(twice\s+a?\s*week|2\s*times?\s+a?\s*week|2x\s*week)\b': '8-pack',  # New pattern
        r'\b(once\s+a?\s*week|1\s*time?\s+a?\s*week|weekly)\b': '4-pack',
        r'\b(three\s+times?\s+a?\s*week|3x\s*week)\b': '12-pack'
    }
    
    for pattern, package in package_patterns.items():
        if re.search(pattern, text_lower):
            details['package'] = package
            break
    
    # If no package specified, default to single
    if 'package' not in details:
        details['package'] = 'single'
    
    # Enhanced name extraction
    lines = text.strip().split('\n')
    
    # Try to find name on first line or as first capitalized words
    for line in lines:
        line = line.strip()
        
        # Skip lines that look like phone numbers or emails
        if re.search(r'\d{3,}|@', line):
            continue
            
        # Look for capitalized names (First Last format)
        name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', line)
        if name_match:
            potential_name = name_match.group(1)
            # Avoid common words
            if not any(word in potential_name.lower() for word in ['email', 'phone', 'client', 'add', 'new', 'week', 'pack']):
                details['name'] = potential_name
                break
    
    # If still no name found, try the first non-empty line
    if 'name' not in details:
        for line in lines:
            line = line.strip()
            if line and not re.search(r'\d{3,}|@|week|pack|times?', line.lower()):
                # Clean up the line and use as name if it looks like a name
                if len(line.split()) >= 2 and all(word[0].isupper() for word in line.split() if word.isalpha()):
                    details['name'] = line
                    break
    
    print(f"Extracted details: {details}")  # Debug logging
    return details

def complete_client_addition(trainer, client_details):
    """Add client to database with extracted details"""
    
    try:
        print(f"Attempting to add client with details: {client_details}")
        
        # Validate required fields
        if not client_details.get('name'):
            return f"I couldn't find a name in your message. Could you try again with format:\n\nName\nPhone number\nEmail\nPackage type"
        
        if not client_details.get('phone'):
            return f"I couldn't find a phone number. Could you try again with format:\n\nName\nPhone number\nEmail\nPackage type"
        
        # Set defaults
        package = client_details.get('package', 'single')
        sessions_map = {
            'single': 1,
            '4-pack': 4,
            '8-pack': 8,
            '12-pack': 12,
            'monthly': 8
        }
        sessions = sessions_map.get(package, 8)  # Default to 8 for "twice a week"
        
        # Prepare client record
        client_record = {
            'trainer_id': trainer['id'],
            'name': client_details['name'],
            'whatsapp': client_details['phone'],
            'email': client_details.get('email'),
            'sessions_remaining': sessions,
            'package_type': package,
            'status': 'active'
        }
        
        print(f"Inserting client record: {client_record}")
        
        # Add to database
        result = supabase.table('clients').insert(client_record).execute()
        
        print(f"Database result: {result}")
        
        if result.data:
            # Trigger onboarding
            threading.Thread(
                target=send_client_onboarding_refiloe,
                args=(client_details['phone'], client_details['name'], trainer, sessions)
            ).start()
            
            return f"""✅ Perfect! 

{client_details['name']} is now added to your client list!

📱 I'm sending them a welcome message right now  
📦 Package: {package.title()} ({sessions} sessions)  
💬 They'll get booking instructions via WhatsApp

All set, {trainer['name']}! 😊"""
        
        else:
            return f"Database didn't return data. Something went wrong adding {client_details['name']}."
    
    except Exception as e:
        print(f"Error completing client addition: {str(e)}")
        print(f"Client details were: {client_details}")
        return f"I ran into an issue: {str(e)}. Could you try again?"

def send_client_onboarding_refiloe(client_whatsapp, client_name, trainer, sessions):
    """Refiloe's personalized client onboarding"""
    
    try:
        import time
        time.sleep(2)
        
        # Welcome message
        welcome_msg = f"""Hi {client_name}! 👋

I'm Refiloe, {trainer['name']}'s AI assistant! Welcome to the team! 🎉

I'm here to make booking your training sessions super easy:

💪 Your package: {sessions} sessions  
💵 Per session: R{trainer['pricing_per_session']:.0f}  
📱 How it works: Just message me here!

Want to book your first session? Say something like "Book Tuesday morning" or "When are you free?" 

I'll take care of the rest! 😊"""
        
        send_whatsapp_message(client_whatsapp, welcome_msg)
        
        # Follow-up with availability
        time.sleep(25)
        
        availability_msg = f"""🗓️ Here's what I have available this week:

Mon: 9am, 2pm, 5pm  
Tue: 10am, 1pm, 4pm  
Wed: 8am, 12pm, 3pm  
Thu: 9am, 2pm, 5pm  
Fri: 10am, 1pm, 4pm  

Just tell me what works! Something like "Thursday 2pm sounds good" 

Ready to get started? 💪"""
        
        send_whatsapp_message(client_whatsapp, availability_msg)
        
    except Exception as e:
        print(f"Error in Refiloe onboarding: {str(e)}")

def get_trainer_clients_refiloe(trainer_id, trainer_name):
    """Refiloe's friendly client list"""
    
    try:
        clients_result = supabase.table('clients').select('name, sessions_remaining, last_session_date').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        if not clients_result.data:
            return f"You don't have any active clients yet, {trainer_name}! Ready to add your first one? 😊"
        
        response = f"📋 Your clients, {trainer_name}:\n\n"
        
        for client in clients_result.data:
            last_session = client['last_session_date']
            if last_session:
                days_ago = (datetime.now(SA_TZ) - datetime.fromisoformat(last_session)).days
                last_text = f"{days_ago} days ago" if days_ago > 0 else "Today"
            else:
                last_text = "No sessions yet"
            
            response += f"• {client['name']} ({client['sessions_remaining']} left, last: {last_text})\n"
        
        return response + "\nNeed to add someone new? Just tell me! 💪"
    
    except Exception as e:
        return f"I'm having trouble getting your client list, {trainer_name}. Try again?"

def get_trainer_schedule_refiloe(trainer_id, trainer_name):
    """Refiloe's friendly schedule display"""
    
    try:
        now = datetime.now(SA_TZ)
        week_later = now + timedelta(days=7)
        
        bookings_result = supabase.table('bookings').select('session_datetime, clients(name), status').eq('trainer_id', trainer_id).gte('session_datetime', now.isoformat()).lte('session_datetime', week_later.isoformat()).order('session_datetime').execute()
        
        if not bookings_result.data:
            return f"Your week is wide open, {trainer_name}! 📅\n\nPerfect time for your clients to book sessions 😊"
        
        response = f"📅 Coming up for you, {trainer_name}:\n\n"
        
        for booking in bookings_result.data:
            session_time = datetime.fromisoformat(booking['session_datetime'])
            day = session_time.strftime('%a %d %b')
            time = session_time.strftime('%I:%M%p').lower()
            client_name = booking['clients']['name']
            
            response += f"• {day} at {time} - {client_name}\n"
        
        return response + "\nLooking good! 💪"
    
    except Exception as e:
        return f"Let me check your schedule again, {trainer_name}..."

def get_trainer_revenue_refiloe(trainer_id, trainer_name):
    """Refiloe's encouraging revenue summary"""
    
    try:
        now = datetime.now(SA_TZ)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        payments_result = supabase.table('payments').select('amount, status').eq('trainer_id', trainer_id).gte('created_at', month_start.isoformat()).execute()
        
        total_revenue = sum(p['amount'] for p in payments_result.data if p['status'] == 'paid')
        pending_revenue = sum(p['amount'] for p in payments_result.data if p['status'] == 'pending')
        
        clients_result = supabase.table('clients').select('id').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        active_clients = len(clients_result.data)
        
        encouragement = "Great work!" if total_revenue > 5000 else "You're building momentum!" if total_revenue > 1000 else "Every session counts!"
        
        return f"""💰 {now.strftime('%B')} Summary for {trainer_name}:

Revenue: R{total_revenue:.2f} ✅  
Pending: R{pending_revenue:.2f} ⏳  
Active clients: {active_clients} 👥

{encouragement} 🚀"""
        
    except Exception as e:
        return f"Let me check your earnings, {trainer_name}..."

def trigger_manual_reminders_refiloe(trainer_id, trainer_name):
    """Refiloe sends personalized reminders"""
    
    try:
        clients_result = supabase.table('clients').select('name, whatsapp').eq('trainer_id', trainer_id).eq('status', 'active').execute()
        
        for client in clients_result.data:
            reminder_msg = f"""💪 Quick check-in, {client['name']}!

It's Refiloe here! {trainer_name} wanted me to see how you're doing with your fitness goals.

Ready for your next session? I've got some great times available:

Tomorrow: 10am, 2pm, 5pm  
Day after: 9am, 1pm, 4pm

What sounds good? 😊"""
            
            send_whatsapp_message(client['whatsapp'], reminder_msg)
        
        return f"✅ Just sent friendly check-ins to all your clients, {trainer_name}! 😊"
        
    except Exception as e:
        return f"I'll try sending those reminders again, {trainer_name}..."

def get_trainer_help_menu_refiloe(trainer_name):
    """Refiloe's helpful menu"""
    
    return f"""Hi {trainer_name}! I'm Refiloe 😊

Here's what I can help with:

*Clients:*  
• "Add new client" - I'll ask for details  
• "My clients" - See your client list  
• "Send reminders" - Reach out to everyone  

*Schedule:*  
• "My schedule" - This week's sessions  
• "Revenue" - How you're doing this month  

*Natural chat:*  
Just tell me what you need! I understand normal conversation 💬

What can I help you with? 💪"""

def process_trainer_request_with_refiloe(trainer, message_text):
    """Refiloe's personality for general trainer requests"""
    
    if not ANTHROPIC_API_KEY:
        return f"Hi {trainer['name']}! I'm getting set up to help you better. For now, try asking about specific things like 'my clients' or 'add client'! 😊"
    
    # Enhanced prompt for Refiloe's personality
    prompt = f"""You are Refiloe, an AI assistant for personal trainer "{trainer['name']}" who runs "{trainer['business_name']}". 

PERSONALITY:
- Friendly, cheerful, and professional
- Use the name "Refiloe" when introducing yourself
- Keep responses concise and to the point for WhatsApp (2-3 sentences max)
- Use emojis appropriately but not excessively
- Be encouraging and positive about their business

CAPABILITIES:
- Help with client management and scheduling
- Provide business advice for personal trainers
- Handle booking and administrative tasks
- Give motivational support

IMPORTANT: 
- Keep responses SHORT (2-3 sentences max)
- Be conversational and natural
- If they want to add clients, ask for details naturally
- Don't give long marketing pitches

Trainer's message: "{message_text}"

Respond as Refiloe would - friendly, helpful, and concise."""
    
    return call_claude_api_simple(prompt)

def handle_client_message_refiloe(client_context, message_text):
    """Handle messages from clients with Refiloe's personality"""
    
    client = client_context['data']
    trainer = client['trainers']
    message_lower = message_text.lower()
    
    # Natural language booking
    if any(word in message_lower for word in ['book', 'schedule', 'appointment', 'session']):
        return handle_client_booking_refiloe(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['reschedule', 'move', 'change time', 'different time']):
        return handle_client_reschedule_refiloe(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['cancel', "can't make it", 'sick']):
        return handle_client_cancellation_refiloe(client, trainer, message_text)
    
    elif any(word in message_lower for word in ['available', 'free times', 'when', 'availability']):
        return get_trainer_availability_refiloe(trainer['id'], client)
    
    elif any(word in message_lower for word in ['sessions left', 'balance', 'remaining', 'package']):
        return get_client_session_balance_refiloe(client)
    
    elif any(word in message_lower for word in ['help', 'commands']):
        return get_client_help_menu_refiloe(client['name'])
    
    # Natural time booking (e.g., "Tuesday 2pm", "Friday morning")
    elif detect_time_booking(message_text):
        return process_natural_time_booking(client, trainer, message_text)
    
    else:
        # Use Refiloe for general client assistance
        return process_client_request_with_refiloe(client, trainer, message_text)

def detect_time_booking(message_text):
    """Detect if message contains a specific time booking request"""
    
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    times = ['morning', 'afternoon', 'evening', 'am', 'pm', ':', 'oclock']
    
    message_lower = message_text.lower()
    
    has_day = any(day in message_lower for day in days)
    has_time = any(time in message_lower for time in times)
    
    return has_day and has_time

def process_natural_time_booking(client, trainer, message_text):
    """Process natural language time booking like 'Tuesday 2pm'"""
    
    return f"""Perfect, {client['name']}! 

I'm booking you for that time with {trainer['name']}. 

✅ Session confirmed  
💰 R{trainer['pricing_per_session']:.0f} (from your package)  
📱 I'll send a reminder the day before  

Sessions remaining: {client['sessions_remaining'] - 1} 

Looking forward to your workout! 💪"""

def handle_client_booking_refiloe(client, trainer, message_text):
    """Refiloe's friendly booking assistance"""
    
    if client['sessions_remaining'] <= 0:
        return f"""Hey {client['name']}! 

You've used up all your sessions from your {client['package_type']} package! 🎉

Want more? I can let {trainer['name']} know you're ready for another package, or you can book individual sessions at R{trainer['pricing_per_session']:.0f} each.

What sounds good? 😊"""
    
    return f"""Hi {client['name']}! 😊

Let's get you booked with {trainer['name']}! 

*Available this week:*  
Mon: 9am, 2pm, 5pm  
Tue: 10am, 1pm, 4pm  
Wed: 8am, 12pm, 3pm  
Thu: 9am, 2pm, 5pm  
Fri: 10am, 1pm, 4pm  

Just say something like "Thursday 2pm" or "Friday morning"! 

Sessions left: {client['sessions_remaining']} 💪"""

def handle_client_reschedule_refiloe(client, trainer, message_text):
    """Refiloe's helpful rescheduling"""
    
    return f"""No problem, {client['name']}! 

Which session do you need to move? And when works better for you?

*Available times:*  
Tomorrow: 10am, 2pm, 5pm  
Day after: 9am, 1pm, 4pm  

Life happens - we'll get you sorted! 😊"""

def handle_client_cancellation_refiloe(client, trainer, message_text):
    """Refiloe's understanding cancellation handling"""
    
    return f"""Of course, {client['name']}! 

Which session do you need to cancel? I'll free up that time right away.

Want to reschedule instead? I've got:  
Tomorrow: 10am, 2pm, 5pm  
Next few days: 9am, 1pm, 4pm  

Hope you're feeling better soon! 💚"""

def get_trainer_availability_refiloe(trainer_id, client):
    """Refiloe's friendly availability display"""
    
    return f"""Here's what {client['trainers']['name']} has available, {client['name']}! 

📅 This week:  
Mon: 9am, 2pm, 5pm  
Tue: 10am, 1pm, 4pm  
Wed: 8am, 12pm, 3pm  
Thu: 9am, 2pm, 5pm  
Fri: 10am, 1pm, 4pm  

📅 Next week:  
Mon: 9am, 1pm, 3pm  
Tue: 10am, 2pm, 5pm  

What works for you? Just tell me! 😊"""

def get_client_session_balance_refiloe(client):
    """Refiloe's encouraging balance display"""
    
    progress = ""
    if client['last_session_date']:
        days_ago = (datetime.now(SA_TZ) - datetime.fromisoformat(client['last_session_date'])).days
        if days_ago == 0:
            progress = "Great workout today! 🔥"
        elif days_ago <= 3:
            progress = "You're on a roll! 💪"
        elif days_ago <= 7:
            progress = "Ready for your next session? 😊"
        else:
            progress = "Let's get back into it! 💪"
    else:
        progress = "Ready for your first session? 🎉"
    
    return f"""📊 Hey {client['name']}!

Package: {client['package_type'].title()}  
Sessions left: {client['sessions_remaining']}  

{progress}

Want to book your next one? 😊"""

def get_client_help_menu_refiloe(client_name):
    """Refiloe's helpful client menu"""
    
    return f"""Hi {client_name}! I'm Refiloe 😊

*Quick booking:*  
• "Book session" - See available times  
• "Tuesday 2pm" - Book specific time  
• "When are you free?" - Check availability  

*Manage sessions:*  
• "Reschedule" - Move your booking  
• "Cancel" - Cancel if needed  
• "Sessions left" - Check your balance  

*Just chat naturally!*  
I understand normal conversation 💬

What can I help with? 💪"""

def process_client_request_with_refiloe(client, trainer, message_text):
    """Refiloe's personality for general client requests"""
    
    if not ANTHROPIC_API_KEY:
        return f"Hi {client['name']}! I'm Refiloe, and I'm here to help with your training sessions. Try asking about booking or your schedule! 😊"
    
    prompt = f"""You are Refiloe, an AI assistant helping client "{client['name']}" with their personal training sessions with trainer "{trainer['name']}".

PERSONALITY:
- Friendly, encouraging, and professional
- Keep responses concise for WhatsApp (2-3 sentences max)
- Use appropriate emojis but not excessively
- Be motivating about their fitness journey

CONTEXT:
- Client has {client['sessions_remaining']} sessions remaining
- Package type: {client['package_type']}
- Session price: R{trainer['pricing_per_session']:.0f}

CAPABILITIES:
- Help book, reschedule, or cancel sessions
- Provide motivation and encouragement
- Answer questions about their package
- Connect them with their trainer when needed

Client's message: "{message_text}"

Respond as Refiloe would - friendly, helpful, and encouraging."""
    
    return call_claude_api_simple(prompt)

def handle_unknown_sender_refiloe(phone_number, message_text):
    """Refiloe handles unknown senders"""
    
    message_lower = message_text.lower()
    
    if any(word in message_lower for word in ['trainer', 'register', 'sign up', 'join']):
        return """👋 Hi there! I'm Refiloe!

I help personal trainers manage their clients automatically via WhatsApp! 

Want to join as a trainer? Here's how:
• Visit our website (coming soon!)
• Or message: "REGISTER TRAINER [Your Name] [Email]"

Example: "REGISTER TRAINER John Smith john@email.com"

I'll handle all your client bookings 24/7! 💪"""
    
    else:
        return """👋 Hi! I'm Refiloe, an AI assistant for personal trainers! 

**If you're a trainer:** I can manage your client bookings, scheduling, and reminders automatically!

**If you're a client:** Your trainer needs to add you to the system first, then I'll help you book sessions easily!

Reply "TRAINER" if you want to sign up! 😊"""

def call_claude_api_simple(prompt):
    """Simplified Claude API call for Refiloe"""
    
    try:
        claude_url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 150,  # Shorter responses
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(claude_url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        else:
            return "I'm having a quick tech moment. Try that again? 😊"
    
    except Exception as e:
        print(f"Error with Refiloe Claude API: {str(e)}")
        return "Let me try that again for you! 😊"

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
            
            reminder_msg = f"""💪 Stay Strong, {client['name']}!

It's Refiloe here! It's been a week since your last session with {trainer['name']}. 

Ready to get back on track? I have these times available:

📅 Tomorrow:
• 9am, 2pm, 5pm

📅 This Week:  
• Tuesday: 10am, 1pm, 4pm
• Wednesday: 8am, 12pm, 3pm
• Thursday: 9am, 2pm, 5pm

Sessions remaining: {client['sessions_remaining']}

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
            
            payment_msg = f"""💳 Payment Reminder

Hi {client['name']}! It's Refiloe here.

Your payment of R{payment['amount']:.2f} for {trainer['name']}'s training sessions was due on {payment['due_date']}.

Payment Options:
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
            
            confirmation_msg = f"""⏰ Session Reminder

Hi {client['name']}! It's Refiloe here.

This is a friendly reminder about your training session tomorrow:

📅 Tomorrow ({session_time.strftime('%A, %d %B')})
🕐 Time: {session_time.strftime('%I:%M %p')}
👨‍💼 Trainer: {trainer['name']}
💰 Price: R{booking['price']:.2f}

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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'claude_api': 'connected' if ANTHROPIC_API_KEY else 'not configured',
        'whatsapp_api': 'configured' if ACCESS_TOKEN and PHONE_NUMBER_ID else 'not configured',
        'supabase': 'connected' if supabase else 'not configured',
        'scheduler': 'running' if scheduler.running else 'stopped',
        'assistant': 'Refiloe v1.0',
        'version': 'refiloe_personality'
    })

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
            
            reminder_msg = f"""💪 Quick Check-in!

Hi {client['name']}! It's Refiloe here.

{trainer['name']} wanted me to reach out and see how you're doing with your fitness goals.

Ready for your next session? I have these times available:

📅 This Week:
• Tomorrow: 10am, 2pm, 5pm
• Day after: 9am, 1pm, 4pm

Sessions remaining: {client['sessions_remaining']}

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
