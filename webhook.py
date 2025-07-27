from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Environment variables (set in Railway)
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'your_verify_token_here')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', 'your_access_token_here')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID', 'your_phone_number_id')

@app.route('/')
def home():
    return "WhatsApp AI Assistant Webhook is running!"

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
        print("Received webhook data:", data)
        
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
                    
                    # Echo the message back (for testing)
                    response_text = f"I received your message: {message_text}"
                    send_whatsapp_message(phone_number, response_text)
                
                # Handle voice messages (we'll expand this later)
                elif 'audio' in message:
                    print(f"Audio message from {phone_number}")
                    send_whatsapp_message(phone_number, "I received your voice message! (Voice processing coming soon)")
                
                elif 'voice' in message:
                    print(f"Voice message from {phone_number}")
                    send_whatsapp_message(phone_number, "I received your voice note! (Voice processing coming soon)")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
