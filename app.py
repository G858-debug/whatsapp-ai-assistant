from flask import Flask
from config import Config
from app_core import setup_app_core
from app_routes import setup_routes

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Setup core services and models (THIS IS CRITICAL!)
app, scheduler = setup_app_core(app)

# Setup basic routes
setup_routes(app)

# Import and register blueprints
from routes.calendar import calendar_bp
from routes.payment import payment_bp
from routes.webhooks import webhooks_bp
from payfast_webhook import payfast_webhook_bp

# Register blueprints with correct prefixes
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(payment_bp, url_prefix='/payment')
app.register_blueprint(webhooks_bp)  # NO PREFIX - webhook should be at /webhook
app.register_blueprint(payfast_webhook_bp)  # PayFast at /webhooks/payfast

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
