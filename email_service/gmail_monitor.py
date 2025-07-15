"""
Enhanced Gmail monitor that properly handles conversation threads.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import base64
from email.utils import parsedate_to_datetime

from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class GmailThreadMonitor:
    """Monitor Gmail for replies in conversation threads."""
    
    def __init__(self, gmail_service):
        self.service = gmail_service
        self.photographer_email = os.getenv('PHOTOGRAPHER_EMAIL', 'contact@keithmorse.com')
        
    def get_digest_threads(self, hours_back: int = 48) -> List[Dict]:
        """Get all threads containing digest emails from recent hours."""
        since_date = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        timestamp = int(since_date.timestamp())
        
        # Search for threads with NYC Event digests
        query = f'after:{timestamp} (subject:NYC OR subject:Event) to:{self.photographer_email}'
        
        try:
            results = self.service.users().threads().list(
                userId='me',
                q=query,
                maxResults=20
            ).execute()
            
            threads = results.get('threads', [])
            return threads
            
        except Exception as e:
            logger.error(f"Error searching threads: {e}")
            return []
    
    def get_thread_replies(self, thread_id: str, after_date: datetime) -> List[Dict]:
        """Get all replies in a thread after a certain date."""
        replies = []
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = thread.get('messages', [])
            
            # Find the digest email and subsequent replies
            digest_found = False
            digest_timestamp = None
            
            for msg in messages:
                headers = {h['name']: h['value'] 
                         for h in msg['payload']['headers']}
                
                from_email = headers.get('From', '')
                subject = headers.get('Subject', '')
                
                # Check if this is the digest email
                if not digest_found and 'NYC Event' in subject and self.photographer_email in headers.get('To', ''):
                    digest_found = True
                    try:
                        digest_timestamp = parsedate_to_datetime(headers.get('Date', ''))
                    except:
                        digest_timestamp = after_date
                    logger.debug(f"Found digest email: {subject} at {digest_timestamp}")
                    continue
                
                # If we found the digest, look for replies after it
                if digest_found:
                    try:
                        msg_date = parsedate_to_datetime(headers.get('Date', ''))
                        
                        # Make dates timezone-aware for comparison
                        if not msg_date.tzinfo:
                            msg_date = msg_date.replace(tzinfo=timezone.utc)
                        if not digest_timestamp.tzinfo:
                            digest_timestamp = digest_timestamp.replace(tzinfo=timezone.utc)
                        if not after_date.tzinfo:
                            after_date = after_date.replace(tzinfo=timezone.utc)
                        
                        logger.debug(f"Checking message from {from_email} at {msg_date}")
                        
                        # Check if this message is from the photographer and after the digest
                        if (self.photographer_email in from_email and 
                            msg_date > digest_timestamp and 
                            msg_date > after_date):
                            
                            logger.info(f"Found reply from {from_email}!")
                            
                            # This is a reply!
                            body = self._extract_body(msg['payload'])
                            
                            replies.append({
                                'id': msg['id'],
                                'thread_id': thread_id,
                                'from': from_email,
                                'subject': subject,
                                'date': headers.get('Date', ''),
                                'body': body,
                                'is_reply': True
                            })
                            
                    except Exception as e:
                        logger.debug(f"Error parsing message date: {e}")
                        
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            
        return replies
    
    def _extract_body(self, payload) -> str:
        """Extract text body from message payload."""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        elif payload.get('body', {}).get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']).decode('utf-8', errors='ignore')
                
        return body
    
    def check_for_replies(self, hours_back: int = 48) -> List[Dict]:
        """Check for new replies to digest emails."""
        since_date = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        all_replies = []
        
        # Get threads with digests
        threads = self.get_digest_threads(hours_back)
        logger.info(f"Found {len(threads)} threads to check")
        
        # Check each thread for replies
        for thread in threads:
            thread_id = thread['id']
            replies = self.get_thread_replies(thread_id, since_date)
            
            if replies:
                logger.info(f"Found {len(replies)} replies in thread {thread_id}")
                all_replies.extend(replies)
                
        return all_replies