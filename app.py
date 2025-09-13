from flask import Flask
from config import Config
from routes.dashboard import dashboard_bp
from routes.calendar import calendar_bp
from routes.payment import payment_bp
from routes.webhooks import webhooks_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(calendar_bp, url_prefix='/calendar')
app.register_blueprint(payment_bp, url_prefix='/payment')
app.register_blueprint(webhooks_bp, url_prefix='/webhooks')

if __name__ == '__main__':
    app.run()