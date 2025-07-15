"""
Email sender module for sending digests and outreach emails.
"""

import os
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from .email_client import get_email_client, EmailClient
from .digest import DigestGenerator, DigestTracker
from data_store import EventCollection

load_dotenv()


class EmailSender:
    """Handles sending of email digests and outreach emails."""
    
    def __init__(self, email_client: Optional[EmailClient] = None):
        self.client = email_client or get_email_client()
        self.photographer_email = os.getenv('PHOTOGRAPHER_EMAIL', 'contact@keithmorse.com')
        
    def send_digest(self, events: EventCollection, 
                   max_events: int = 20,
                   test_mode: bool = False) -> bool:
        """
        Send email digest to photographer.
        
        Args:
            events: Collection of events to include
            max_events: Maximum number of events to include
            test_mode: If True, only generate but don't send
            
        Returns:
            True if sent successfully
        """
        # Generate digest
        generator = DigestGenerator()
        tracker = DigestTracker()
        
        # Filter to only new events
        new_events = tracker.filter_new_events(events)
        
        if len(new_events) == 0:
            logger.info("No new events to send")
            return False
            
        # Generate digest content
        digest = generator.generate_digest(new_events, max_events=max_events)
        
        if test_mode:
            # Save for preview only
            saved_files = generator.save_digest(digest)
            logger.info(f"Test mode: Digest saved to {saved_files}")
            return True
            
        # Send email
        success = self.client.send_email(
            to=self.photographer_email,
            subject=digest['subject'],
            html_body=digest['html_body'],
            text_body=digest['text_body']
        )
        
        if success:
            # Mark events as sent
            event_ids = [event.event_id for event in new_events]
            tracker.mark_events_sent(event_ids, datetime.now())
            
            # Log the sending
            self._log_sent_email(
                recipient=self.photographer_email,
                subject=digest['subject'],
                event_count=digest['event_count'],
                email_type='digest'
            )
            
            logger.info(f"Digest sent successfully to {self.photographer_email}")
        else:
            logger.error("Failed to send digest")
            
        return success
    
    def send_outreach_email(self, recipient: str, subject: str,
                          html_body: str, text_body: str,
                          event_name: str) -> bool:
        """
        Send outreach email to event organizer.
        
        Args:
            recipient: Email address of the organizer
            subject: Email subject
            html_body: HTML version of email
            text_body: Plain text version
            event_name: Name of the event for logging
            
        Returns:
            True if sent successfully
        """
        # Add CAN-SPAM compliance footer if not present
        if "unsubscribe" not in text_body.lower():
            text_body += "\n\n--\nTo unsubscribe from future emails, please reply with 'UNSUBSCRIBE'."
            
        if "unsubscribe" not in html_body.lower():
            html_body += """
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; 
                        font-size: 12px; color: #666; text-align: center;">
                To unsubscribe from future emails, please reply with 'UNSUBSCRIBE'.
            </div>
            """
        
        # Send email
        success = self.client.send_email(
            to=recipient,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        if success:
            # Log the sending
            self._log_sent_email(
                recipient=recipient,
                subject=subject,
                event_name=event_name,
                email_type='outreach'
            )
            
            logger.info(f"Outreach email sent to {recipient} for event: {event_name}")
        else:
            logger.error(f"Failed to send outreach email to {recipient}")
            
        return success
    
    def _log_sent_email(self, recipient: str, subject: str,
                       email_type: str, event_count: int = None,
                       event_name: str = None):
        """Log sent email to tracking file."""
        log_dir = Path("data/email_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"sent_emails_{datetime.now().strftime('%Y%m')}.csv"
        
        # Create CSV header if file doesn't exist
        if not log_file.exists():
            with open(log_file, 'w') as f:
                f.write("timestamp,type,recipient,subject,event_count,event_name\n")
        
        # Append log entry
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            event_count = event_count or ""
            event_name = event_name or ""
            
            # Escape fields for CSV
            subject = subject.replace('"', '""')
            event_name = event_name.replace('"', '""')
            
            f.write(f'{timestamp},{email_type},"{recipient}","{subject}",{event_count},"{event_name}"\n')


class EmailMonitor:
    """Monitor and process email replies."""
    
    def __init__(self, email_client: Optional[EmailClient] = None):
        self.client = email_client or get_email_client()
        
    def check_replies(self, hours_back: int = 24) -> List[Dict]:
        """
        Check for replies in the last N hours.
        
        Args:
            hours_back: How many hours back to check
            
        Returns:
            List of reply dictionaries
        """
        from datetime import timedelta
        
        since_date = datetime.now() - timedelta(hours=hours_back)
        
        # Check for digest replies
        digest_replies = self.client.get_replies(
            subject_contains="NYC Event Leads",
            since_date=since_date
        )
        
        # Check for unsubscribe requests
        unsubscribe_replies = self._check_unsubscribe_requests(digest_replies)
        
        if unsubscribe_replies:
            logger.warning(f"Found {len(unsubscribe_replies)} unsubscribe requests")
            self._process_unsubscribes(unsubscribe_replies)
            
        # Filter out unsubscribe requests from normal replies
        event_replies = [
            reply for reply in digest_replies
            if not self._is_unsubscribe_request(reply['body'])
        ]
        
        logger.info(f"Found {len(event_replies)} event selection replies")
        
        return event_replies
    
    def _check_unsubscribe_requests(self, replies: List[Dict]) -> List[Dict]:
        """Check for unsubscribe requests in replies."""
        unsubscribe_replies = []
        
        for reply in replies:
            if self._is_unsubscribe_request(reply['body']):
                unsubscribe_replies.append(reply)
                
        return unsubscribe_replies
    
    def _is_unsubscribe_request(self, body: str) -> bool:
        """Check if email body contains unsubscribe request."""
        unsubscribe_keywords = ['unsubscribe', 'stop', 'remove me', 'opt out']
        body_lower = body.lower()
        
        return any(keyword in body_lower for keyword in unsubscribe_keywords)
    
    def _process_unsubscribes(self, unsubscribe_replies: List[Dict]):
        """Process unsubscribe requests."""
        # For now, just log them
        # In production, you would update a database or file
        
        unsubscribe_file = Path("data/unsubscribed.txt")
        unsubscribe_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(unsubscribe_file, 'a') as f:
            for reply in unsubscribe_replies:
                f.write(f"{datetime.now().isoformat()},{reply['from']}\n")
                logger.info(f"Processed unsubscribe request from {reply['from']}")