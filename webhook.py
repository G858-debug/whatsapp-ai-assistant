from flask import Flask, request, jsonify
import os
import requests
import json
from anthropic import Anthropic
from openai import OpenAI
from datetime import datetime
import tempfile

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Initialize AI clients safely
anthropic_client = None
if ANTHROPIC_API_KEY:
    try:
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        print("✅ Anthropic client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Anthropic client: {e}")

# Initialize OpenAI client
openai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")

# Simple in-memory storage for client context (we'll upgrade this later)
client_contexts = {}

@app.route('/')
def home():
    return "Personal Trainer AI Assistant is running! 💪"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"Verification attempt - Mode: {mode}, Token: {token}")
    
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
        print("Received webhook data:", json.dumps(data, indent=2))
        
        # Check if this is a message
        if (data.get('entry') and 
            data['entry'][0].get('changes') and 
            data['entry'][0]['changes'][0].get('value', {}).get('messages')):
            
            messages = data['entry'][0]['changes'][0]['value']['messages']
            
            for message in messages:
                phone_number = message['from']
                message_id = message['id']
                timestamp = message.get('timestamp', str(int(datetime.now().timestamp())))
                
                # Handle text messages
                if 'text' in message:
                    message_text = message['text']['body']
                    print(f"Text message from {phone_number}: {message_text}")
                    
                    # Process with Claude AI
                    response = process_message_with_claude(phone_number, message_text, 'text')
                    send_whatsapp_message(phone_number, response)
                
                # Handle voice messages
                elif 'audio' in message or 'voice' in message:
                    print(f"Voice message from {phone_number}")
                    
                    # Get audio file
                    audio_id = message.get('audio', {}).get('id') or message.get('voice', {}).get('id')
                    
                    if audio_id:
                        # Download and transcribe audio
                        transcript = process_voice_message(audio_id)
                        if transcript:
                            print(f"Voice transcript: {transcript}")
                            
                            # Process with Claude AI
                            response = process_message_with_claude(phone_number, transcript, 'voice')
                            send_whatsapp_message(phone_number, f"🎤 I heard: {transcript}\n\n{response}")
                        else:
                            send_whatsapp_message(phone_number, "Sorry, I couldn't process your voice message. Please try again or send a text message.")
                    else:
                        send_whatsapp_message(phone_number, "Voice processing is being set up. Please send a text message for now.")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_message_with_claude(phone_number, message_text, message_type='text'):
    """Process message using Claude AI with personal trainer context"""
    
    if not anthropic_client:
        return "AI processing is being set up. Please try again later."
    
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
            'type': message_type
        })
        
        # Keep only last 10 messages for context
        if len(client_contexts[phone_number]['messages']) > 10:
            client_contexts[phone_number]['messages'] = client_contexts[phone_number]['messages'][-10:]
        
        # Build conversation history
        conversation_history = "\n".join([
            f"Client: {msg['message']}" for msg in client_contexts[phone_number]['messages'][-5:]
        ])
        
        # Create Claude prompt
        system_prompt = """You are an AI virtual assistant specifically designed for personal trainers and fitness professionals. Your role is to help with:

1. CLIENT SCHEDULING: Booking sessions, rescheduling, cancellations
2. BASIC INVOICING: Creating simple invoices, payment reminders
3. COLLECTIONS: Following up on overdue payments professionally
4. FINANCE REPORTING: Basic income tracking, client payment status
5. CLIENT COMMUNICATION: Professional responses, motivation, check-ins
6. WORKOUT PLANNING: Basic exercise suggestions (you're not replacing the trainer's expertise)

Key traits:
- Professional but friendly tone
- Focus on fitness/health industry
- Keep responses concise (WhatsApp appropriate)
- Ask clarifying questions when needed
- Be helpful with admin tasks
- Motivational when appropriate

If asked to do something outside your scope, politely redirect to what you can help with.

Current conversation context:
{conversation_history}

Respond to the latest message appropriately."""

        # Call Claude API
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,  # Keep responses concise for WhatsApp
            system=system_prompt.format(conversation_history=conversation_history),
            messages=[
                {"role": "user", "content": message_text}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Add AI response to context
        client_contexts[phone_number]['messages'].append({
            'timestamp': datetime.now().isoformat(),
            'message': ai_response,
            'type': 'ai_response'
        })
        
        return ai_response
        
    except Exception as e:
        print(f"Error with Claude API: {str(e)}")
        return "I'm having trouble processing your request right now. Please try again in a moment."

def process_voice_message(audio_id):
    """Download and transcribe voice message using OpenAI Whisper"""
    
    if not OPENAI_API_KEY:
        return None
    
    try:
        # Get audio file URL from WhatsApp
        media_url = get_whatsapp_media_url(audio_id)
        if not media_url:
            return None
        
        # Download audio file
        audio_response = requests.get(
            media_url,
            headers={'Authorization': f'Bearer {ACCESS_TOKEN}'}
        )
        
        if audio_response.status_code != 200:
            return None
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_file.write(audio_response.content)
            temp_file_path = temp_file.name
        
        # Transcribe with OpenAI Whisper
        if openai_client:
            with open(temp_file_path, 'rb') as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # You can change this or let it auto-detect
                )
        else:
            return "OpenAI client not available"
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return transcript.text
        
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        return None

def get_whatsapp_media_url(media_id):
    """Get download URL for WhatsApp media"""
    try:
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('url')
        return None
        
    except Exception as e:
        print(f"Error getting media URL: {str(e)}")
        return None

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
        'claude_api': 'connected' if anthropic_client else 'not configured',
        'openai_api': 'configured' if OPENAI_API_KEY else 'not configured',
        'whatsapp_api': 'configured' if ACCESS_TOKEN and PHONE_NUMBER_ID else 'not configured'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
