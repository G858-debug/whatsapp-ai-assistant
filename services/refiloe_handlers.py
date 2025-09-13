from services.registration.client_registration import handle_client_registration_flow
from services.registration.edit_handlers import handle_client_profile_update_flow
from services.payment_commands import handle_payment_request_flow
from services.calendar_service import handle_calendar_request_flow
from services.gamification_manager import handle_gamification_request_flow
from services.habits import handle_habits_request_flow

def handle_whatsapp_message(data):
    message = data['messages'][0]['text']['body']
    refiloe = Refiloe()
    refiloe.handle_message(message)

def handle_client_registration(message):
    handle_client_registration_flow(message)

def handle_client_profile_update(message):
    handle_client_profile_update_flow(message)

def handle_payment_request(message):
    handle_payment_request_flow(message)

def handle_calendar_request(message):
    handle_calendar_request_flow(message)

def handle_gamification_request(message):
    handle_gamification_request_flow(message)

def handle_habits_request(message):
    handle_habits_request_flow(message)