"""
Email client for sending and receiving emails via Gmail API or IMAP/SMTP.
"""

import os
import base64
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl

from loguru import logger
from dotenv import load_dotenv

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    logger.warning("Gmail API libraries not available. Using IMAP/SMTP only.")

# IMAP imports
from imapclient import IMAPClient

load_dotenv()


class EmailClient:
    """Base email client interface."""
    
    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send an email."""
        raise NotImplementedError
        
    def get_replies(self, subject_contains: str, since_date: Optional[datetime] = None) -> List[Dict]:
        """Get email replies matching criteria."""
        raise NotImplementedError


class GmailAPIClient(EmailClient):
    """Gmail API client for sending and receiving emails."""
    
    # If modifying these scopes, delete the token file.
    SCOPES = ['https://www.googleapis.com/auth/gmail.send',
              'https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_file: str = "credentials.json",
                 token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self._authenticate()
        
    def _authenticate(self):
        """Authenticate and return Gmail service object."""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
                
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Please follow the Gmail API setup instructions."
                    )
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
                
        return build('gmail', 'v1', credentials=creds)
    
    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send an email using Gmail API."""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['Subject'] = subject
            
            # Add both text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully. Message ID: {send_message['id']}")
            return True
            
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return False
            
    def get_replies(self, subject_contains: str, since_date: Optional[datetime] = None) -> List[Dict]:
        """Get email replies matching criteria."""
        try:
            # Build query - more flexible to catch replies
            query_parts = []
            
            # Look for subject in various formats
            subject_terms = subject_contains.split()
            subject_query = ' OR '.join([f'subject:{term}' for term in subject_terms])
            query_parts.append(f'({subject_query})')
            
            if since_date:
                # Gmail uses epoch timestamp
                timestamp = int(since_date.timestamp())
                query_parts.append(f'after:{timestamp}')
                
            query = ' '.join(query_parts)
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50  # Get more results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get unique threads
            thread_ids = set()
            for msg in messages:
                thread_ids.add(msg.get('threadId'))
            
            replies = []
            processed_ids = set()
            
            # Process each thread
            for thread_id in thread_ids:
                try:
                    thread = self.service.users().threads().get(
                        userId='me',
                        id=thread_id
                    ).execute()
                    
                    # Look at all messages in thread
                    thread_messages = thread.get('messages', [])
                    
                    # Process messages in chronological order
                    for message in thread_messages:
                        msg_id = message['id']
                        if msg_id in processed_ids:
                            continue
                            
                        processed_ids.add(msg_id)
                        
                        # Check if this is after our date cutoff
                        reply_data = self._parse_message(message)
                        if reply_data:
                            # Parse date to check if it's recent enough
                            try:
                                from email.utils import parsedate_to_datetime
                                msg_date = parsedate_to_datetime(reply_data['date'])
                                if since_date and msg_date < since_date:
                                    continue
                            except:
                                pass
                            
                            replies.append(reply_data)
                            
                except Exception as e:
                    logger.error(f"Error processing thread {thread_id}: {e}")
                    
            return replies
            
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return []
            
    def _parse_message(self, message: Dict) -> Optional[Dict]:
        """Parse Gmail message into standard format."""
        try:
            headers = {header['name']: header['value'] 
                      for header in message['payload']['headers']}
            
            # Get body
            body = self._get_message_body(message['payload'])
            
            return {
                'id': message['id'],
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'body': body
            }
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
            
    def _get_message_body(self, payload: Dict) -> str:
        """Extract body from Gmail message payload."""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']).decode('utf-8')
                
        return body


class IMAPSMTPClient(EmailClient):
    """IMAP/SMTP client for sending and receiving emails."""
    
    def __init__(self):
        # Load configuration from environment
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.username = os.getenv('SMTP_USERNAME')
        self.password = os.getenv('SMTP_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError(
                "SMTP_USERNAME and SMTP_PASSWORD must be set in environment"
            )
            
    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send an email using SMTP."""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.username
            message['To'] = to
            message['Subject'] = subject
            
            # Add both text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(message)
                
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
            
    def get_replies(self, subject_contains: str, since_date: Optional[datetime] = None) -> List[Dict]:
        """Get email replies matching criteria using IMAP."""
        replies = []
        
        try:
            # Connect to IMAP server
            with IMAPClient(self.imap_host, port=self.imap_port, use_uid=True) as client:
                client.login(self.username, self.password)
                client.select_folder('INBOX')
                
                # Build search criteria
                criteria = ['NOT', 'DELETED']
                
                if since_date:
                    criteria.extend(['SINCE', since_date.date()])
                    
                if subject_contains:
                    criteria.extend(['SUBJECT', subject_contains])
                    
                # Search for messages
                messages = client.search(criteria)
                
                # Fetch message data
                if messages:
                    response = client.fetch(messages, ['RFC822', 'FLAGS', 'INTERNALDATE'])
                    
                    for msg_id, data in response.items():
                        email_message = self._parse_imap_message(data)
                        if email_message and subject_contains.lower() in email_message['subject'].lower():
                            replies.append(email_message)
                            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            
        return replies
        
    def _parse_imap_message(self, data: Dict) -> Optional[Dict]:
        """Parse IMAP message data."""
        try:
            import email
            
            raw_email = data[b'RFC822']
            email_message = email.message_from_bytes(raw_email)
            
            # Extract body
            body = ''
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                
            return {
                'from': email_message.get('From', ''),
                'subject': email_message.get('Subject', ''),
                'date': email_message.get('Date', ''),
                'body': body
            }
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None


def get_email_client(use_gmail_api: bool = None) -> EmailClient:
    """
    Get appropriate email client based on configuration.
    
    If use_gmail_api is None, it will check for Gmail API credentials first,
    then fall back to IMAP/SMTP.
    """
    if use_gmail_api is None:
        # Auto-detect based on available credentials
        if GMAIL_API_AVAILABLE and os.path.exists("credentials.json"):
            use_gmail_api = True
        else:
            use_gmail_api = False
            
    if use_gmail_api:
        if not GMAIL_API_AVAILABLE:
            raise ImportError(
                "Gmail API libraries not installed. "
                "Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        return GmailAPIClient()
    else:
        return IMAPSMTPClient()