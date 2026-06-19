# telegram_bot.py
import requests
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot for sending loan application notifications"""
    
    def __init__(self):
        self.token = Config.TELEGRAM_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = Config.TELEGRAM_ENABLED
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, message, parse_mode='HTML'):
        """Send a message to Telegram"""
        if not self.enabled:
            logger.warning("Telegram bot is not configured")
            return None
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Telegram request timed out")
            return None
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return None
    
    def send_application(self, data):
        """Send formatted loan application to Telegram"""
        if not self.enabled:
            return None
        
        message = self._format_application(data)
        return self.send_message(message)
    
    def send_status_update(self, application_id, status, message=""):
        """Send status update notification"""
        if not self.enabled:
            return None
        
        status_emoji = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
        status_text = status.upper()
        
        msg = f"""
{status_emoji} <b>LOAN STATUS UPDATE</b>
━━━━━━━━━━━━━━━━━━━━━

📋 Application ID: {application_id}
📊 Status: <b>{status_text}</b>
📝 Message: {message if message else 'No additional information'}

━━━━━━━━━━━━━━━━━━━━━
"""
        return self.send_message(msg)
    
    def send_quick_notification(self, message):
        """Send quick notification"""
        if not self.enabled:
            return None
        return self.send_message(f"🔔 {message}")
    
    def _format_application(self, data):
        """Format application data for Telegram"""
        # Calculate interest
        amount = data.get('loan_amount', 0)
        if amount <= 10000:
            interest_rate = 5
            months = 1
        elif amount <= 30000:
            interest_rate = 8
            months = 3
        else:
            interest_rate = 12
            months = 6
        
        interest = amount * (interest_rate / 100)
        total = amount + interest
        
        message = f"""
📋 <b>NEW LOAN APPLICATION</b>
━━━━━━━━━━━━━━━━━━━━━

👤 <b>Personal Information</b>
• Full Name: {data.get('first_name', 'N/A')} {data.get('last_name', 'N/A')}
• Phone: +254 {data.get('phone', 'N/A')}
• Email: {data.get('email', 'N/A')}
• ID Number: {data.get('national_id', 'N/A')}
• Gender: {data.get('gender', 'N/A')}
• Date of Birth: {data.get('dob', 'N/A')}

💰 <b>Loan Details</b>
• Amount: KES {amount:,.2f}
• Interest Rate: {interest_rate}%
• Interest Amount: KES {interest:,.2f}
• Total Repayment: KES {total:,.2f}
• Term: {months} month(s)

🕐 <b>Application Information</b>
• Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Application ID: {data.get('application_id', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━
<b>Status: ⏳ Pending Review</b>

📱 <b>Support</b>
Phone: {Config.SUPPORT_PHONE}
Email: {Config.SUPPORT_EMAIL}
"""
        return message

# Singleton instance
telegram_bot = TelegramBot()