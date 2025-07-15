# Email Setup Guide

This guide explains how to set up email functionality for the NYC Event Automation system.

## Overview

The system supports two methods for email integration:

1. **Gmail API** (Recommended) - More features, better reliability
2. **IMAP/SMTP** - Works with any email provider

## Option 1: Gmail API Setup

### Prerequisites

1. A Gmail account
2. Access to Google Cloud Console

### Steps

1. **Enable Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Search for "Gmail API" and enable it

2. **Create Credentials**
   - Go to Credentials → Create Credentials → OAuth 2.0 Client ID
   - Choose "Desktop app" as application type
   - Download the credentials JSON file

3. **Run Setup Script**
   ```bash
   python setup_gmail.py --gmail-api path/to/credentials.json
   ```

4. **Authenticate**
   - A browser window will open
   - Log in with your Gmail account
   - Grant permissions to the app

### Benefits
- No password storage needed
- Better security with OAuth
- Access to Gmail-specific features
- More reliable than IMAP

## Option 2: IMAP/SMTP Setup

### For Gmail

1. **Enable 2-Factor Authentication**
   - Go to your Google Account settings
   - Security → 2-Step Verification → Turn on

2. **Generate App Password**
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and generate password
   - Save this password (you won't see it again)

3. **Run Setup Script**
   ```bash
   python setup_gmail.py --imap-smtp
   ```

4. **Enter Configuration**
   - SMTP Host: smtp.gmail.com
   - SMTP Port: 587
   - IMAP Host: imap.gmail.com
   - IMAP Port: 993
   - Email: your-email@gmail.com
   - Password: [App password from step 2]

### For Other Providers

Common settings:

**Outlook/Hotmail:**
- SMTP: smtp.office365.com:587
- IMAP: outlook.office365.com:993

**Yahoo:**
- SMTP: smtp.mail.yahoo.com:587
- IMAP: imap.mail.yahoo.com:993

## Testing Your Setup

After configuration, test with:

```bash
# Generate test digest (without sending)
python main.py send-digest --test

# Check for replies
python main.py check-replies
```

## Environment Variables

The following variables are set in `.env`:

```env
# For Gmail API
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json

# For IMAP/SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
IMAP_HOST=imap.gmail.com
IMAP_PORT=993

# Photographer details
PHOTOGRAPHER_EMAIL=contact@keithmorse.com
```

## Troubleshooting

### Gmail API Issues

1. **"Credentials file not found"**
   - Make sure you downloaded the OAuth credentials
   - Check the file path is correct

2. **"Access blocked" error**
   - Ensure Gmail API is enabled in Cloud Console
   - Check OAuth consent screen is configured

### IMAP/SMTP Issues

1. **"Authentication failed"**
   - For Gmail: Use app password, not regular password
   - Check 2FA is enabled
   - Verify "Less secure app access" if needed

2. **"Connection refused"**
   - Check firewall settings
   - Verify port numbers
   - Try with/without SSL/TLS

## Security Notes

- Never commit credentials to git
- Store app passwords securely
- Regularly rotate credentials
- Monitor for unauthorized access

## Next Steps

Once email is configured:

1. Run `python main.py scrape` to collect events
2. Run `python main.py send-digest` to send digest
3. Run `python main.py check-replies` to monitor responses
4. Run `python main.py send-outreach` to contact organizers