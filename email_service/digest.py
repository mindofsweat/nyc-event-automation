"""
Email digest generator for NYC events.
"""

from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import os
from loguru import logger

from data_store import EventCollection, EventModel


class DigestGenerator:
    """Generate formatted email digests from event collections."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path("templates")
        
    def generate_digest(self, events: EventCollection, 
                       digest_date: Optional[datetime] = None,
                       max_events: Optional[int] = None) -> Dict[str, str]:
        """
        Generate email digest with formatted events.
        
        Returns dict with 'subject', 'html_body', and 'text_body'.
        """
        digest_date = digest_date or datetime.now()
        
        # Filter to upcoming events only
        upcoming_events = events.get_upcoming(from_date=digest_date)
        
        # Sort by date
        upcoming_events.sort(key=lambda e: e.date)
        
        # Limit number of events if specified
        if max_events and len(upcoming_events) > max_events:
            upcoming_events = upcoming_events[:max_events]
            
        # Generate subject
        subject = self._generate_subject(digest_date, len(upcoming_events))
        
        # Generate both HTML and text versions
        html_body = self._generate_html_body(upcoming_events, digest_date)
        text_body = self._generate_text_body(upcoming_events, digest_date)
        
        return {
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'event_count': len(upcoming_events)
        }
    
    def _generate_subject(self, date: datetime, event_count: int) -> str:
        """Generate email subject line."""
        date_str = date.strftime("%B %d")
        return f"NYC Event Leads - {date_str} ({event_count} new events)"
    
    def _generate_html_body(self, events: List[EventModel], date: datetime) -> str:
        """Generate HTML version of the digest."""
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <meta charset="utf-8">',
            '  <style>',
            '    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }',
            '    .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }',
            '    .container { max-width: 800px; margin: 0 auto; padding: 20px; }',
            '    .event { border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }',
            '    .event-number { font-weight: bold; color: #2c3e50; font-size: 18px; }',
            '    .event-title { font-size: 16px; font-weight: bold; margin: 10px 0; }',
            '    .event-details { color: #666; margin: 5px 0; }',
            '    .event-link { color: #3498db; text-decoration: none; }',
            '    .event-link:hover { text-decoration: underline; }',
            '    .instructions { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }',
            '    .footer { text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }',
            '  </style>',
            '</head>',
            '<body>',
            '  <div class="header">',
            f'    <h1>NYC Event Opportunities</h1>',
            f'    <p>{date.strftime("%A, %B %d, %Y")}</p>',
            '  </div>',
            '  <div class="container">',
            '    <div class="instructions">',
            '      <p><strong>Hello Keith,</strong></p>',
            '      <p>Here are the latest NYC events that might interest you for photography opportunities.</p>',
            '      <p><strong>To select events:</strong> Reply to this email with the numbers of events you\'d like to pursue (e.g., "1, 3, 5").</p>',
            '    </div>',
        ]
        
        if not events:
            html_parts.extend([
                '    <p>No new events found for this period.</p>',
            ])
        else:
            html_parts.append('    <div class="events">')
            
            for i, event in enumerate(events, 1):
                event_html = self._format_event_html(event, i)
                html_parts.append(event_html)
                
            html_parts.append('    </div>')
        
        html_parts.extend([
            '    <div class="footer">',
            '      <p>This email was automatically generated by the NYC Event Automation System.</p>',
            '      <p>To stop receiving these emails, please reply with "UNSUBSCRIBE".</p>',
            '    </div>',
            '  </div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def _format_event_html(self, event: EventModel, number: int) -> str:
        """Format a single event as HTML."""
        date_str = event.date.strftime("%a, %b %d at %I:%M %p")
        
        html = f'''
        <div class="event">
            <div class="event-number">#{number}</div>
            <div class="event-title">{event.name}</div>
            <div class="event-details">📅 {date_str}</div>
            <div class="event-details">📍 {event.location}</div>'''
        
        if event.description:
            # Truncate description if too long
            desc = event.description[:200] + '...' if len(event.description) > 200 else event.description
            html += f'\n            <div class="event-details">📝 {desc}</div>'
            
        html += f'''
            <div class="event-details">🔗 <a href="{event.source_url}" class="event-link">View Event</a></div>
            <div class="event-details">Source: {event.source}</div>
        </div>'''
        
        return html
    
    def _generate_text_body(self, events: List[EventModel], date: datetime) -> str:
        """Generate plain text version of the digest."""
        lines = [
            f"NYC EVENT LEADS - {date.strftime('%B %d, %Y')}",
            "=" * 50,
            "",
            "Hello Keith,",
            "",
            "Here are the latest NYC events that might interest you for photography opportunities.",
            "",
            "TO SELECT EVENTS: Reply with the numbers of events you'd like to pursue (e.g., '1, 3, 5').",
            "",
            "-" * 50,
            ""
        ]
        
        if not events:
            lines.append("No new events found for this period.")
        else:
            for i, event in enumerate(events, 1):
                event_text = self._format_event_text(event, i)
                lines.append(event_text)
                lines.append("")  # Empty line between events
        
        lines.extend([
            "-" * 50,
            "",
            "This email was automatically generated by the NYC Event Automation System.",
            "To stop receiving these emails, please reply with 'UNSUBSCRIBE'.",
        ])
        
        return '\n'.join(lines)
    
    def _format_event_text(self, event: EventModel, number: int) -> str:
        """Format a single event as plain text."""
        date_str = event.date.strftime("%a, %b %d at %I:%M %p")
        
        lines = [
            f"#{number} - {event.name}",
            f"Date: {date_str}",
            f"Location: {event.location}",
        ]
        
        if event.description:
            # Truncate description if too long
            desc = event.description[:200] + '...' if len(event.description) > 200 else event.description
            lines.append(f"Description: {desc}")
            
        lines.extend([
            f"Link: {event.source_url}",
            f"Source: {event.source}",
            "-" * 30
        ])
        
        return '\n'.join(lines)
    
    def save_digest(self, digest: Dict[str, str], output_dir: Path = None) -> Dict[str, Path]:
        """Save digest to files for testing/preview."""
        output_dir = output_dir or Path("data/digests")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        saved_files = {}
        
        # Save HTML version
        html_file = output_dir / f"digest_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(digest['html_body'])
        saved_files['html'] = html_file
        
        # Save text version
        text_file = output_dir / f"digest_{timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Subject: {digest['subject']}\n\n{digest['text_body']}")
        saved_files['text'] = text_file
        
        logger.info(f"Saved digest files: {saved_files}")
        return saved_files


class DigestTracker:
    """Track which events have been included in previous digests."""
    
    def __init__(self, tracking_file: Path = Path("data/digest_tracking.json")):
        self.tracking_file = tracking_file
        self._load_tracking_data()
        
    def _load_tracking_data(self):
        """Load tracking data from file."""
        if self.tracking_file.exists():
            import json
            with open(self.tracking_file, 'r') as f:
                self.tracking_data = json.load(f)
        else:
            self.tracking_data = {
                'sent_events': {},  # event_id -> digest_date
                'digest_history': []  # List of digest metadata
            }
    
    def save_tracking_data(self):
        """Save tracking data to file."""
        import json
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking_data, f, indent=2, default=str)
    
    def mark_events_sent(self, event_ids: List[str], digest_date: datetime):
        """Mark events as sent in a digest."""
        date_str = digest_date.isoformat()
        for event_id in event_ids:
            self.tracking_data['sent_events'][event_id] = date_str
            
        # Add to digest history
        self.tracking_data['digest_history'].append({
            'date': date_str,
            'event_count': len(event_ids),
            'event_ids': event_ids
        })
        
        self.save_tracking_data()
    
    def filter_new_events(self, events: EventCollection) -> EventCollection:
        """Filter out events that have already been sent."""
        new_events = EventCollection()
        
        for event in events:
            if event.event_id not in self.tracking_data['sent_events']:
                new_events.add(event, check_duplicates=False)
                
        return new_events
    
    def get_last_digest_date(self) -> Optional[datetime]:
        """Get the date of the last digest sent."""
        if self.tracking_data['digest_history']:
            last_digest = self.tracking_data['digest_history'][-1]
            return datetime.fromisoformat(last_digest['date'])
        return None