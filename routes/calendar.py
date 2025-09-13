from flask import Blueprint, render_template

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/')
def calendar():
    return render_template('calendar.html')