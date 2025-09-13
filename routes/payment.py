from flask import Blueprint, render_template, redirect, url_for

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/checkout')
def checkout():
    return render_template('payment/checkout.html')

@payment_bp.route('/success')
def payment_success():
    return render_template('payment/success.html')

@payment_bp.route('/cancel')
def payment_cancel():
    return render_template('payment/cancel.html')