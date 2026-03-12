#!/usr/bin/env python3
"""
Email Configuration Test Script
Tests your SMTP email settings to ensure they work correctly
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_config():
    """Test email configuration by sending a test email"""
    
    # Get configuration from .env
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL')
    from_name = os.getenv('FROM_NAME', 'Cricket Scorecard')
    
    print("=" * 70)
    print("Email Configuration Test")
    print("=" * 70)
    print()
    
    # Validate configuration
    print("Configuration:")
    print(f"  SMTP Host: {smtp_host}")
    print(f"  SMTP Port: {smtp_port}")
    print(f"  SMTP User: {smtp_user}")
    print(f"  From Email: {from_email}")
    print(f"  From Name: {from_name}")
    print()
    
    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email]):
        print("❌ Error: Missing email configuration in .env file")
        print("\nPlease update your .env file with:")
        print("  - SMTP_HOST")
        print("  - SMTP_PORT")
        print("  - SMTP_USER")
        print("  - SMTP_PASSWORD")
        print("  - FROM_EMAIL")
        print("\nSee EMAIL_SETUP_GUIDE.md for detailed instructions")
        return
    
    # Get recipient email
    to_email = input("Enter email address to receive test message: ").strip()
    
    if not to_email or '@' not in to_email:
        print("❌ Invalid email address")
        return
    
    # Create test email
    msg = MIMEMultipart('alternative')
    msg['From'] = f'{from_name} <{from_email}>'
    msg['To'] = to_email
    msg['Subject'] = "Test Email from Cricket Scorecard App ✓"
    
    # HTML body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #ec008c 0%, #ff6b00 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 10px;
                margin-top: 20px;
            }}
            .success {{
                color: #28a745;
                font-size: 48px;
                margin: 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏏 Cricket Scorecard</h1>
            <p>Email Configuration Test</p>
        </div>
        <div class="content">
            <p class="success">✓</p>
            <h2>Success!</h2>
            <p>If you're reading this email, your SMTP configuration is working correctly! 🎉</p>
            <p>Your Cricket Scorecard application is now ready to send:</p>
            <ul>
                <li>Account verification emails</li>
                <li>Password reset emails</li>
                <li>Notification emails</li>
            </ul>
            <p><strong>Configuration Details:</strong></p>
            <ul>
                <li>SMTP Host: {smtp_host}</li>
                <li>SMTP Port: {smtp_port}</li>
                <li>From: {from_email}</li>
            </ul>
        </div>
        <div class="footer">
            <p>This is an automated test email from your Cricket Scorecard application.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text alternative
    text_body = f"""
    Cricket Scorecard - Email Configuration Test
    
    SUCCESS!
    
    If you're reading this email, your SMTP configuration is working correctly!
    
    Your Cricket Scorecard application is now ready to send:
    - Account verification emails
    - Password reset emails
    - Notification emails
    
    Configuration Details:
    - SMTP Host: {smtp_host}
    - SMTP Port: {smtp_port}
    - From: {from_email}
    
    This is an automated test email from your Cricket Scorecard application.
    """
    
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    
    # Send email
    print()
    print("-" * 70)
    
    try:
        print(f"Connecting to {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        
        print("Starting TLS encryption...")
        server.starttls()
        
        print("Authenticating...")
        server.login(smtp_user, smtp_password)
        
        print("Sending test email...")
        server.send_message(msg)
        server.quit()
        
        print()
        print("=" * 70)
        print("✓ EMAIL SENT SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nCheck your inbox at: {to_email}")
        print("(Don't forget to check spam folder if you don't see it)")
        print()
        
    except smtplib.SMTPAuthenticationError:
        print()
        print("=" * 70)
        print("❌ AUTHENTICATION FAILED")
        print("=" * 70)
        print()
        print("Common solutions:")
        print("  1. Gmail users: Use an App Password, not your regular password")
        print("     • Enable 2FA: https://myaccount.google.com/security")
        print("     • Create App Password: https://myaccount.google.com/apppasswords")
        print()
        print("  2. Check that SMTP_USER and SMTP_PASSWORD are correct in .env")
        print()
        print("  3. Some providers require 'Less secure app access'")
        print()
        
    except smtplib.SMTPConnectError:
        print()
        print("=" * 70)
        print("❌ CONNECTION FAILED")
        print("=" * 70)
        print()
        print(f"Could not connect to {smtp_host}:{smtp_port}")
        print()
        print("Common solutions:")
        print("  1. Check SMTP_HOST is correct in .env")
        print("  2. Check SMTP_PORT (try 465 for SSL or 587 for TLS)")
        print("  3. Check firewall/antivirus settings")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"\n{type(e).__name__}: {e}")
        print()
        print("Troubleshooting:")
        print("  • Check all values in your .env file")
        print("  • See EMAIL_SETUP_GUIDE.md for detailed setup instructions")
        print("  • Verify your email provider's SMTP settings")
        print()

if __name__ == "__main__":
    test_email_config()
