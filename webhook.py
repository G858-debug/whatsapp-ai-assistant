from flask import Flask, request, jsonify
import os
import requests
import json
from datetime import datetime, timedelta
import pytz
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import re

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

# Simple in-memory storage
client_contexts = {}

# Google Calendar setup
calendar_service = None
if GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_CALENDAR_ID:
    try:
        # Parse the JSON from environment variable
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Build the service
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("✅ Google Calendar service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Google Calendar: {e}")

# South African timezone
SA_TZ = pytz.timezone('Africa/Johannesburg')

@app.route('/')
def home():
    return "Personal Trainer AI Assistant with Calendar Integration! 💪📅"

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
                    
                    # Check if this is a calendar-related request
                    response = process_calendar_request(phone_number, message_text)
                    send_whatsapp_message(phone_number, response)
                
                # Handle voice messages (placeholder)
                elif 'audio' in message or 'voice' in message:
                    print(f"Voice message from {phone_number}")
                    send_whatsapp_message(phone_number, "Voice processing with calendar integration coming soon! Please send a text message.")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_calendar_request(phone_number, message_text):
    """Process message with calendar integration and Claude AI"""
    
    try:
        # Get or create client context
        if phone_number not in client_contexts:
            client_contexts[phone_number] = {
                'messages': [],
                'client_info': {},
                'created_at': datetime.now().isoformat()
            }
        
        # Add message to context
        client_contexts[phone_number]['messages'].append({
            'timestamp': datetime.now().isoformat(),
            'message': message_text,
            'type': 'user'
        })
        
        # Detect calendar-related requests
        calendar_intent = detect_calendar_intent(message_text)
        
        if calendar_intent:
            return handle_calendar_action(phone_number, message_text, calendar_intent)
        else:
            return process_with_claude_ai(phone_number, message_text)
    
    except Exception as e:
        print(f"Error processing calendar request: {str(e)}")
        return "I'm having trouble accessing the calendar right now. Please try again in a moment."

def detect_calendar_intent(message_text):
    """Detect if message is calendar-related and what action is needed"""
    message_lower = message_text.lower()
    
    # Booking keywords
    booking_keywords = ['book', 'schedule', 'appointment', 'session', 'available', 'availability', 'free time']
    
    # Rescheduling keywords  
    reschedule_keywords = ['reschedule', 'move', 'change', 'different time', 'switch']
    
    # Cancellation keywords
    cancel_keywords = ['cancel', 'cancelled', 'can\'t make it', 'sick', 'emergency']
    
    # Check availability keywords
    availability_keywords = ['when are you free', 'what times', 'available times', 'open slots']
    
    if any(keyword in message_lower for keyword in booking_keywords):
        return 'booking'
    elif any(keyword in message_lower for keyword in reschedule_keywords):
        return 'reschedule'
    elif any(keyword in message_lower for keyword in cancel_keywords):
        return 'cancel'
    elif any(keyword in message_lower for keyword in availability_keywords):
        return 'availability'
    
    return None

def handle_calendar_action(phone_number, message_text, intent):
    """Handle specific calendar actions"""
    
    if not calendar_service:
        return "Calendar integration is being set up. For now, I can help with general scheduling advice!"
    
    try:
        if intent == 'availability':
            return get_available_times()
        
        elif intent == 'booking':
            # For now, show availability and ask for confirmation
            available_times = get_available_times()
            return f"I'd love to help you book a session! Here are my available times:\n\n{available_times}\n\nWhich time works best for you?"
        
        elif intent == 'reschedule':
            available_times = get_available_times()
            return f"I can help you reschedule! Here are my available times:\n\n{available_times}\n\nWhich new time would you prefer?"
        
        elif intent == 'cancel':
            return "I understand you need to cancel. Could you tell me which session you'd like to cancel? (Day and time)\n\nI can also help you reschedule if you'd like!"
        
        else:
            return process_with_claude_ai(phone_number, message_text)
    
    except Exception as e:
        print(f"Error handling calendar action: {str(e)}")
        return "I'm having trouble with the calendar right now. Let me help you with general scheduling advice instead!"

def get_available_times():
    """Get available time slots from Google Calendar"""
    
    if not calendar_service or not GOOGLE_CALENDAR_ID:
        return "Calendar system is being configured."
    
    try:
        # Get events for the next 7 days
        now = datetime.now(SA_TZ)
        end_time = now + timedelta(days=7)
        
        events_result = calendar_service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Generate available slots (simple version)
        available_slots = generate_available_slots(events, now, end_time)
        
        if available_slots:
            return format_available_times(available_slots)
        else:
            return "I'm fully booked for the next 7 days. Let me check if I can fit you in somewhere or we can look at next week!"
    
    except Exception as e:
        print(f"Error getting available times: {str(e)}")
        return "Having trouble checking my calendar. Could you call me or try again in a few minutes?"

def generate_available_slots(existing_events, start_date, end_date):
    """Generate available 1-hour slots during business hours"""
    
    # Business hours: 6 AM to 8 PM, Monday to Saturday
    business_hours = {
        0: (6, 20),   # Monday
        1: (6, 20),   # Tuesday  
        2: (6, 20),   # Wednesday
        3: (6, 20),   # Thursday
        4: (6, 20),   # Friday
        5: (8, 16),   # Saturday (shorter hours)
        6: None       # Sunday (closed)
    }
    
    available_slots = []
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    while current_date < end_date:
        day_of_week = current_date.weekday()
        
        if business_hours[day_of_week]:  # If we work this day
            start_hour, end_hour = business_hours[day_of_week]
            
            for hour in range(start_hour, end_hour):
                slot_start = current_date.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(hours=1)
                
                # Skip past times
                if slot_start <= datetime.now(SA_TZ):
                    continue
                
                # Check if slot conflicts with existing events
                is_available = True
                for event in existing_events:
                    event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                    event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
                    
                    if (slot_start < event_end and slot_end > event_start):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot_start)
                
                # Limit to 10 slots to avoid overwhelming the client
                if len(available_slots) >= 10:
                    return available_slots
        
        current_date += timedelta(days=1)
    
    return available_slots

def format_available_times(slots):
    """Format available time slots for WhatsApp message"""
    
    if not slots:
        return "No available times found."
    
    formatted_times = []
    
    for slot in slots[:8]:  # Show max 8 options
        day_name = slot.strftime('%A')
        date = slot.strftime('%d %B')
        time = slot.strftime('%I:%M %p')
        
        formatted_times.append(f"• {day_name} {date} at {time}")
    
    response = "📅 *Available Times:*\n\n"
    response += "\n".join(formatted_times)
    response += "\n\nJust tell me which time works for you!"
    
    return response

def process_with_claude_ai(phone_number, message_text):
    """Process with Claude AI for non-calendar requests"""
    
    if not ANTHROPIC_API_KEY:
        return "Hi! I'm your AI assistant for personal trainers. I can help with scheduling, invoicing, and client management!"
    
    try:
        # Build conversation history
        conversation_history = "\n".join([
            f"Client: {msg['message']}" for msg in client_contexts[phone_number]['messages'][-3:]
            if msg['type'] == 'user'
        ])
        
        # Call Claude API directly
        claude_url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # Enhanced prompt with calendar context
        prompt = f"""You are an AI assistant for personal trainers with calendar integration. Help with:

- SCHEDULING: I can check real availability and book sessions
- INVOICING: Create invoices, payment reminders
- CLIENT MANAGEMENT: Professional communication, motivation
- ADMIN TASKS: Task management, business advice

I have access to Google Calendar for real-time scheduling.

Recent conversation: {conversation_history}

Client message: "{message_text}"

Respond helpfully and mention calendar features when relevant."""
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 250,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(claude_url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['content'][0]['text']
            
            # Add AI response to context
            client_contexts[phone_number]['messages'].append({
                'timestamp': datetime.now().isoformat(),
                'message': ai_response,
                'type': 'assistant'
            })
            
            return ai_response
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
            return "I'm here to help with your training business and scheduling! What can I assist you with?"
    
    except Exception as e:
        print(f"Error with Claude AI: {str(e)}")
        return "I'm ready to help with scheduling, client management, and your training business!"

def send_whatsapp_message(phone_number, message_text):
    """Send message back to WhatsApp"""
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
        'google_calendar': 'connected' if calendar_service else 'not configured',
        'version': 'calendar_integrated'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
