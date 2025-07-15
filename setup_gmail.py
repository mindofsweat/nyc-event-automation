#!/usr/bin/env python3
"""
Setup script for Gmail API authentication.

This script helps you set up Gmail API access for the NYC Event Automation system.

Prerequisites:
1. Go to https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create credentials (OAuth 2.0 Client ID) for a desktop application
5. Download the credentials JSON file
6. Run this script with the path to your credentials file
"""

import os
import sys
import argparse
from pathlib import Path
import shutil

from loguru import logger


def setup_gmail_api(credentials_path: str):
    """Set up Gmail API authentication."""
    print("Gmail API Setup")
    print("=" * 50)
    
    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        print(f"\nError: Credentials file not found: {credentials_path}")
        print("\nPlease follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select an existing one")
        print("3. Enable the Gmail API")
        print("4. Go to 'Credentials' and create OAuth 2.0 Client ID")
        print("5. Choose 'Desktop app' as the application type")
        print("6. Download the credentials JSON file")
        print("7. Run this script again with the path to the downloaded file")
        return False
    
    # Copy credentials to project directory
    target_path = "credentials.json"
    if credentials_path != target_path:
        shutil.copy(credentials_path, target_path)
        print(f"\n✓ Credentials file copied to {target_path}")
    
    # Try to authenticate
    try:
        from email_service.email_client import GmailAPIClient
        
        print("\nAuthenticating with Gmail API...")
        print("A browser window will open for authentication.")
        print("Please log in with the Gmail account you want to use.")
        
        client = GmailAPIClient()
        
        print("\n✓ Authentication successful!")
        print("Gmail API is now set up and ready to use.")
        
        # Test by getting labels
        try:
            results = client.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            print(f"\nConnected to Gmail account with {len(labels)} labels.")
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"\nError during authentication: {e}")
        return False


def setup_imap_smtp():
    """Interactive setup for IMAP/SMTP configuration."""
    print("\nIMAP/SMTP Setup")
    print("=" * 50)
    
    print("\nFor Gmail with App Passwords:")
    print("1. Enable 2-factor authentication on your Google account")
    print("2. Go to https://myaccount.google.com/apppasswords")
    print("3. Generate an app password for 'Mail'")
    print("4. Use that password instead of your regular password")
    
    print("\nEnter your email configuration:")
    
    config = {
        'SMTP_HOST': input("SMTP Host [smtp.gmail.com]: ").strip() or "smtp.gmail.com",
        'SMTP_PORT': input("SMTP Port [587]: ").strip() or "587",
        'IMAP_HOST': input("IMAP Host [imap.gmail.com]: ").strip() or "imap.gmail.com",
        'IMAP_PORT': input("IMAP Port [993]: ").strip() or "993",
        'SMTP_USERNAME': input("Email address: ").strip(),
        'SMTP_PASSWORD': input("Password/App Password: ").strip(),
    }
    
    # Update .env file
    env_file = Path(".env")
    env_content = []
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    # Update or add configuration
    updated_keys = set()
    new_content = []
    
    for line in env_content:
        key = line.split('=')[0].strip()
        if key in config:
            new_content.append(f"{key}={config[key]}\n")
            updated_keys.add(key)
        else:
            new_content.append(line)
    
    # Add any missing keys
    for key, value in config.items():
        if key not in updated_keys:
            new_content.append(f"{key}={value}\n")
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_content)
    
    print("\n✓ Configuration saved to .env file")
    
    # Test connection
    print("\nTesting email connection...")
    try:
        from email_service.email_client import IMAPSMTPClient
        from dotenv import load_dotenv
        
        load_dotenv(override=True)
        client = IMAPSMTPClient()
        
        # Try to connect
        from imapclient import IMAPClient
        with IMAPClient(client.imap_host, port=client.imap_port) as imap:
            imap.login(client.username, client.password)
            imap.select_folder('INBOX')
            
        print("✓ Successfully connected to email server!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nPlease check your credentials and try again.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Set up email authentication for NYC Event Automation"
    )
    parser.add_argument(
        '--gmail-api',
        help="Path to Gmail API credentials JSON file",
        metavar="PATH"
    )
    parser.add_argument(
        '--imap-smtp',
        action='store_true',
        help="Set up IMAP/SMTP authentication"
    )
    
    args = parser.parse_args()
    
    if not args.gmail_api and not args.imap_smtp:
        print("NYC Event Automation - Email Setup")
        print("=" * 50)
        print("\nChoose authentication method:")
        print("1. Gmail API (recommended - more features)")
        print("2. IMAP/SMTP (works with any email provider)")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            creds_path = input("\nPath to Gmail API credentials file: ").strip()
            if creds_path:
                args.gmail_api = creds_path
        else:
            args.imap_smtp = True
    
    if args.gmail_api:
        success = setup_gmail_api(args.gmail_api)
    elif args.imap_smtp:
        success = setup_imap_smtp()
    else:
        print("No authentication method selected.")
        success = False
    
    if success:
        print("\n✓ Email setup completed successfully!")
        print("\nYou can now use:")
        print("  python main.py send-digest")
        print("  python main.py check-replies")
    else:
        print("\n✗ Email setup failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()