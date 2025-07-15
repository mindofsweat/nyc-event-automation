"""
Outreach email generator and sender for event organizers.
"""

import os
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import re

from loguru import logger
from jinja2 import Template

from data_store.models import EventModel
from .sender import EmailSender


class OutreachGenerator:
    """Generate personalized outreach emails for event organizers."""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.html_template = self._load_template("outreach_template.html")
        self.text_template = self._load_template("outreach_template.txt")
        
    def _load_template(self, filename: str) -> Template:
        """Load email template from file."""
        template_path = self.template_dir / filename
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        with open(template_path, 'r') as f:
            return Template(f.read())
            
    def generate_outreach_email(self, event: EventModel, 
                               organizer_name: Optional[str] = None,
                               organizer_email: Optional[str] = None) -> Dict[str, str]:
        """
        Generate personalized outreach email for an event.
        
        Args:
            event: Event details
            organizer_name: Name of the organizer (if known)
            organizer_email: Email of the organizer (if known)
            
        Returns:
            Dictionary with email content
        """
        # Extract organizer info from event if not provided
        if not organizer_email:
            # First check if event has contact_email
            if event.contact_email:
                organizer_email = event.contact_email
            else:
                organizer_email = self._extract_email_from_event(event)
            
        if not organizer_name:
            organizer_name = self._extract_organizer_name(event)
            
        if not organizer_email:
            logger.warning(f"No organizer email found for event: {event.name}")
            return None
            
        # Prepare template variables
        template_vars = {
            'organizer_name': organizer_name or "there",
            'event_name': event.name,
            'event_date': event.date.strftime('%B %d, %Y'),
            'event_location': event.location or "NYC",
        }
        
        # Generate email content
        html_body = self.html_template.render(**template_vars)
        text_body = self.text_template.render(**template_vars)
        
        # Create subject line
        subject = f"Photography Services for {event.name}"
        
        return {
            'to': organizer_email,
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'event_name': event.name,
            'event_id': event.event_id
        }
        
    def _extract_email_from_event(self, event: EventModel) -> Optional[str]:
        """Try to extract organizer email from event details."""
        # Check if email is in the event object
        if hasattr(event, 'organizer_email') and event.organizer_email:
            return event.organizer_email
            
        # Try to find email in description
        if event.description:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            matches = re.findall(email_pattern, event.description)
            if matches:
                return matches[0]
                
        # Try to find email in URL if it's a contact form
        if event.source_url and 'contact' in event.source_url.lower():
            # Extract domain for generic contact
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', event.source_url)
            if domain_match:
                domain = domain_match.group(1)
                # Common patterns
                return f"info@{domain}"
                
        return None
        
    def _extract_organizer_name(self, event: EventModel) -> Optional[str]:
        """Try to extract organizer name from event details."""
        # Check if organizer is in the event object
        if hasattr(event, 'organizer') and event.organizer:
            return event.organizer
            
        # Try to extract from event name or description
        # This is a simplified approach - in production you might use NLP
        if "presented by" in event.name.lower():
            parts = event.name.lower().split("presented by")
            if len(parts) > 1:
                return parts[1].strip().title()
                
        return None


class OutreachSender:
    """Send outreach emails to event organizers."""
    
    def __init__(self, email_sender: Optional[EmailSender] = None):
        self.email_sender = email_sender or EmailSender()
        self.generator = OutreachGenerator()
        self.sent_log_file = Path("data/outreach_sent.json")
        
    def send_outreach_for_events(self, events: List[EventModel], 
                                test_mode: bool = False) -> Dict[str, List[str]]:
        """
        Send outreach emails for selected events.
        
        Args:
            events: List of events to send outreach for
            test_mode: If True, generate but don't send emails
            
        Returns:
            Dictionary with sent and failed event IDs
        """
        sent_events = []
        failed_events = []
        
        # Load previously sent events
        sent_history = self._load_sent_history()
        
        for event in events:
            # Skip if already sent
            if event.event_id in sent_history:
                logger.info(f"Skipping {event.name} - already sent")
                continue
                
            # Generate email
            email_data = self.generator.generate_outreach_email(event)
            
            if not email_data:
                logger.warning(f"Could not generate email for {event.name} - no contact info")
                failed_events.append(event.event_id)
                continue
                
            if test_mode:
                # In test mode, just log what would be sent
                logger.info(f"TEST MODE - Would send to: {email_data['to']}")
                logger.info(f"  Subject: {email_data['subject']}")
                logger.info(f"  Event: {event.name}")
                sent_events.append(event.event_id)
            else:
                # Send the email
                success = self.email_sender.send_outreach_email(
                    recipient=email_data['to'],
                    subject=email_data['subject'],
                    html_body=email_data['html_body'],
                    text_body=email_data['text_body'],
                    event_name=event.name
                )
                
                if success:
                    sent_events.append(event.event_id)
                    self._record_sent(event.event_id, email_data['to'])
                else:
                    failed_events.append(event.event_id)
                    
        logger.info(f"Outreach complete: {len(sent_events)} sent, {len(failed_events)} failed")
        
        return {
            'sent': sent_events,
            'failed': failed_events
        }
        
    def _load_sent_history(self) -> set:
        """Load history of sent outreach emails."""
        if not self.sent_log_file.exists():
            return set()
            
        try:
            with open(self.sent_log_file, 'r') as f:
                data = json.load(f)
                return set(data.get('sent_events', []))
        except Exception as e:
            logger.error(f"Error loading sent history: {e}")
            return set()
            
    def _record_sent(self, event_id: str, recipient: str):
        """Record that an outreach email was sent."""
        # Load existing data
        if self.sent_log_file.exists():
            with open(self.sent_log_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'sent_events': [], 'details': []}
            
        # Add this event
        if event_id not in data['sent_events']:
            data['sent_events'].append(event_id)
            
        data['details'].append({
            'event_id': event_id,
            'recipient': recipient,
            'sent_at': datetime.now().isoformat()
        })
        
        # Save
        self.sent_log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.sent_log_file, 'w') as f:
            json.dump(data, f, indent=2)


def load_selected_events() -> List[EventModel]:
    """Load events that were selected by the photographer."""
    selections_file = Path("data/selections.json")
    
    if not selections_file.exists():
        logger.warning("No selected events found")
        return []
        
    try:
        with open(selections_file, 'r') as f:
            selections = json.load(f)
            
        # Load the events data to get full event details
        from data_store import StorageManager
        storage_manager = StorageManager()
        all_events = storage_manager.load_latest(format="json")
        
        # Create a mapping of event IDs to EventModel objects
        event_map = {event.event_id: event for event in all_events}
        
        # Collect all unique selected event IDs
        selected_event_ids = set()
        for selection in selections:
            selected_event_ids.update(selection.get('event_ids', []))
            
        # Get the EventModel objects for selected events
        selected_events = []
        for event_id in selected_event_ids:
            if event_id in event_map:
                selected_events.append(event_map[event_id])
            else:
                logger.warning(f"Event ID {event_id} not found in events data")
                
        logger.info(f"Loaded {len(selected_events)} selected events")
        return selected_events
        
    except Exception as e:
        logger.error(f"Error loading selected events: {e}")
        return []