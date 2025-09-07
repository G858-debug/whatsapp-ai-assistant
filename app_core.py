import os
import json
import traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from supabase import create_client
from dotenv import load_dotenv
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import all services and models
from services.whatsapp import WhatsAppService
from services.refiloe import RefiloeService
# [Keep all other imports from original]

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Setup logger
logger = setup_logger()

# Validate configuration
try:
    Config.validate()
    log_info("Configuration validated successfully")
except ValueError as e:
    log_error(f"Configuration error: {str(e)}")
    raise

# Initialize Supabase client
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

# Initialize all services
whatsapp_service = WhatsAppService(Config, supabase, logger)
# [Keep all other service initializations]

# Initialize background scheduler and tasks
scheduler = BackgroundScheduler(timezone=pytz.timezone(Config.TIMEZONE))

def send_daily_reminders():
    """Send daily workout and payment reminders"""
    try:
        log_info("Running daily reminders task")
        results = scheduler_service.check_and_send_reminders()
        log_info(f"Daily reminders completed: {results}")
    except Exception as e:
        log_error(f"Error in daily reminders task: {str(e)}")

# [Keep other scheduler functions]

# Schedule background tasks
scheduler.add_job(
    send_daily_reminders,
    CronTrigger(hour=8, minute=0),
    id='daily_reminders',
    replace_existing=True
)

scheduler.start()
log_info("Background scheduler started")

@app.route('/')
def home():
    """Home page"""
    return jsonify({
        "status": "active",
        "service": "Refiloe AI Assistant",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        supabase.table('trainers').select('id').limit(1).execute()
        db_status = "connected"
    except:
        db_status = "error"
    
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    })