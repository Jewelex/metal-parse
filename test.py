# test_smtp_final.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_smtp_with_app_password():
    """Test SMTP with App Password"""
    
    # SMTP Settings
    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    
    # Your credentials
    EMAIL = "aman.gupta@jewelexindia.com"
    APP_PASSWORD = "xmjqscgsrxzpdrdb"  # 🔑 Yahan paste kar
    
    # Send to yourself for testing
    TO_EMAIL = "swaraj.borse@jewelexindia.com"
    
    print("="*50)
    print("Testing SMTP with App Password")
    print("="*50)
    
    try:
        # Connect
        print("\n1️⃣ Connecting to smtp.office365.com...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        print("   ✅ Connected!")
        
        # Start TLS
        print("\n2️⃣ Starting TLS encryption...")
        server.starttls()
        print("   ✅ TLS started!")
        
        # Login with App Password
        print(f"\n3️⃣ Logging in as {EMAIL}...")
        server.login(EMAIL, APP_PASSWORD)
        print("   ✅ Login successful!")
        
        # Create email
        print("\n4️⃣ Creating test email...")
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = TO_EMAIL
        msg['Subject'] = "✅ SMTP Test Successful "
        
        body = f"""
        Hello Raja ji,

        "aiso sent lagaiyo more raja chhati fhat jaye dushman ki....."
        
        
        
        ✅ SMTP connection is working perfectly!
        ✅ App Password authentication successful!
        
        Timestamp: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
        
        Now you can send real metal rate reports automatically!
        
        Regards,
        Metal Rate Bot
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Send
        print("5️⃣ Sending email...")
        server.send_message(msg)
        print("   ✅ Email sent successfully!")
        
        # Close
        print("\n6️⃣ Closing connection...")
        server.quit()
        print("   ✅ Done!")
        
        print("\n" + "="*50)
        print("🎉 SUCCESS! SMTP is working with App Password!")
        print(f"📧 Test email sent to: {TO_EMAIL}")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_smtp_with_app_password()