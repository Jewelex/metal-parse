# utils/send_email.py - HTML Report Embed in Body
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def send_metal_rate_report(run_folder, recipient_emails):
    """
    Send email with HTML report embedded in body + attachment
    """
    
    print("\n📧 Preparing to send email via SMTP...")
    
    # Load SMTP settings from .env
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.office365.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SENDER_EMAIL = os.getenv('SMTP_EMAIL')
    SENDER_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ SMTP credentials not found in .env file!")
        return False
    
    if isinstance(recipient_emails, str):
        recipients = [recipient_emails]
    else:
        recipients = recipient_emails
    
    try:
        # Connect to SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Create email
        msg = MIMEMultipart('alternative')  # 'alternative' allows both plain and HTML
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"Metal Rates Report - {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
        
        # Read the HTML report
        report_path = run_folder / "rates_table.html"
        html_content = ""
        
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            print(f"  📖 Loaded: rates_table.html")
        else:
            # Fallback HTML if report not found
            html_content = f"""
            <html>
            <body>
                <h2>Metal Rates Report</h2>
                <p>Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
                <p>Report file attached.</p>
            </body>
            </html>
            """
        
        # Plain text version (for email clients that don't support HTML)
        plain_text = f"""
        Metal Rates Report
        Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
        
        Full HTML report is embedded in this email.
        
        Regards,
        Metal Rate Bot
        """
        
        # Attach both plain and HTML versions
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Also attach the HTML file separately (optional)
        if report_path.exists():
            with open(report_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename=rates_table.html')
                msg.attach(part)
            print(f"  📎 Attached: rates_table.html")
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"\n✅ Email sent with HTML report embedded!")
        print(f"   📧 To: {', '.join(recipients)}")
        return True
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


if __name__ == "__main__":
    from pathlib import Path
    
    base_folder = Path(r"C:\Users\Aman.gupta\Downloads\metal-rate-bot\scraper_output")
    if base_folder.exists():
        folders = [f for f in base_folder.iterdir() if f.is_dir()]
        if folders:
            latest = max(folders, key=lambda f: f.stat().st_ctime)
            send_metal_rate_report(latest, ["swaraj.borse@jewelexindia.com"])