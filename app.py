from flask import Flask, request, jsonify
from config import Config
from services.refiloe import Refiloe
from services.refiloe_handlers import handle_whatsapp_message

app = Flask(__name__)
app.config.from_object(Config)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    handle_whatsapp_message(data)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run()