# Email Configuration Guide

This guide will help you set up email functionality for user verification in your scorecard application.

## Quick Start: Skip Email Verification (Development)

If you want to get started quickly without email verification:

1. In your `.env` file, set:
   ```env
   EMAIL_VERIFICATION_ENABLED=False
   ```

2. Users will be automatically verified upon registration (good for development/testing)

---

## Option 1: Gmail Setup (Recommended for Beginners)

### Step 1: Enable 2-Factor Authentication on Your Google Account

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Click on "2-Step Verification"
3. Follow the steps to enable it if not already enabled

### Step 2: Generate an App Password

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. You might need to sign in again
3. Select app: Choose "Mail"
4. Select device: Choose "Other (Custom name)" and type "Scorecard App"
5. Click "Generate"
6. **Copy the 16-character password** (it will look like: `xxxx xxxx xxxx xxxx`)

### Step 3: Update Your .env File

```env
# Email Configuration
EMAIL_VERIFICATION_ENABLED=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail-address@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # Paste the app password here
FROM_EMAIL=your-gmail-address@gmail.com
FROM_NAME=Cricket Scorecard
```

### Important Gmail Notes:
- Use your full Gmail address (e.g., `myname@gmail.com`)
- Use the 16-character app password, NOT your regular Gmail password
- Remove spaces from the app password when pasting

---

## Option 2: Other Email Providers

### Outlook/Hotmail

```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### Yahoo Mail

```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password  # Generate at account.yahoo.com
```

### Custom Domain / Business Email

Contact your email provider for SMTP settings. Common format:
```env
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-password
```

---

## Option 3: Third-Party Email Services (Production Recommended)

For production apps, use dedicated email services:

### SendGrid (Free tier: 100 emails/day)

1. Sign up at [SendGrid](https://sendgrid.com/)
2. Create an API key
3. Configuration:
   ```env
   EMAIL_SERVICE=sendgrid
   SENDGRID_API_KEY=your-api-key
   FROM_EMAIL=noreply@yourdomain.com
   ```

### Mailgun (Free tier: 5,000 emails/month for 3 months)

1. Sign up at [Mailgun](https://www.mailgun.com/)
2. Verify your domain
3. Get SMTP credentials
4. Configuration:
   ```env
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USER=postmaster@your-domain.mailgun.org
   SMTP_PASSWORD=your-mailgun-password
   ```

### Amazon SES (Very cheap, requires AWS account)

1. Sign up for AWS
2. Enable Amazon SES
3. Verify your email/domain
4. Get SMTP credentials

---

## Testing Your Email Configuration

### Create a Test Script

Save this as `server/test_email.py`:

```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def test_email():
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL')
    
    # Send test email to yourself
    to_email = input("Enter your email to receive test: ")
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = "Test Email from Cricket Scorecard App"
    
    body = """
    <html>
        <body>
            <h2>Email Configuration Test</h2>
            <p>If you're reading this, your email configuration is working! 🎉</p>
            <p>Your scorecard app is ready to send verification emails.</p>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        print(f"\nConnecting to {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        
        print("Logging in...")
        server.login(smtp_user, smtp_password)
        
        print("Sending email...")
        server.send_message(msg)
        server.quit()
        
        print("\n✓ Email sent successfully!")
        print(f"Check {to_email} for the test email.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nCommon issues:")
        print("- Check if 2FA is enabled and you're using an app password")
        print("- Verify SMTP host and port are correct")
        print("- Check if your email provider requires 'Less secure app access'")

if __name__ == "__main__":
    test_email()
```

### Run the Test

```bash
python server/test_email.py
```

---

## Troubleshooting

### "Authentication failed" Error
- **Gmail**: Make sure you're using an app password, not your regular password
- Verify 2FA is enabled
- Check that you copied the password correctly (no spaces)

### "Connection refused" Error
- Check SMTP_HOST is correct
- Try port 465 instead of 587 (and use SSL instead of TLS)
- Check firewall settings

### Emails Going to Spam
- Add a proper FROM_NAME in your .env
- Consider using a dedicated email service (SendGrid, Mailgun)
- Verify your domain's SPF and DKIM records

### Gmail Blocking Sign-in
1. Go to [Less Secure Apps](https://myaccount.google.com/lesssecureapps)
2. Enable "Allow less secure apps" (if using regular password)
3. Better: Use app passwords with 2FA

---

## Recommended Setup for Different Stages

### Development/Testing
- **Option**: Disable email verification
- **Config**: `EMAIL_VERIFICATION_ENABLED=False`
- **Pros**: Quick setup, no external dependencies
- **Cons**: Can't test email flow

### Staging/Demo
- **Option**: Gmail with app password
- **Config**: Use Gmail SMTP
- **Pros**: Free, easy setup
- **Cons**: Daily sending limits (500-2000 emails/day)

### Production
- **Option**: SendGrid, Mailgun, or Amazon SES
- **Config**: Dedicated email service
- **Pros**: High deliverability, analytics, no daily limits
- **Cons**: Requires account setup

---

## Next Steps

1. Choose which option works best for you
2. Update your `.env` file with the appropriate configuration
3. Run `python server/test_email.py` to verify it works
4. You're ready to go! 🚀
