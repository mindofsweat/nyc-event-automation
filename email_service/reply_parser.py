"""
Reply parser for extracting event selections from photographer emails.
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json

from loguru import logger
from data_store import EventCollection, StorageManager
from .digest import DigestTracker


class ReplyParser:
    """Parse photographer replies to extract event selections."""
    
    def __init__(self):
        self.digest_tracker = DigestTracker()
        self.storage_manager = StorageManager()
        
    def parse_reply(self, reply_body: str, reply_date: Optional[datetime] = None) -> List[int]:
        """
        Parse reply body to extract event numbers.
        
        Args:
            reply_body: The email body text
            reply_date: When the reply was sent (for matching to digest)
            
        Returns:
            List of event numbers (1-based) that were selected
        """
        # Clean up the reply body
        cleaned_body = self._clean_reply_body(reply_body)
        
        # Try different parsing strategies
        event_numbers = []
        
        # Strategy 1: Look for comma-separated numbers (e.g., "1, 3, 5")
        numbers = self._extract_comma_separated_numbers(cleaned_body)
        if numbers:
            event_numbers.extend(numbers)
            
        # Strategy 2: Look for individual numbers on separate lines
        if not event_numbers:
            numbers = self._extract_numbers_on_lines(cleaned_body)
            if numbers:
                event_numbers.extend(numbers)
                
        # Strategy 3: Look for number patterns with context (e.g., "events 1 and 3")
        if not event_numbers:
            numbers = self._extract_numbers_with_context(cleaned_body)
            if numbers:
                event_numbers.extend(numbers)
        
        # Remove duplicates and sort
        event_numbers = sorted(list(set(event_numbers)))
        
        logger.info(f"Parsed event selections: {event_numbers}")
        return event_numbers
    
    def _clean_reply_body(self, body: str) -> str:
        """Clean up email body by removing quotes and signatures."""
        lines = body.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip quoted lines (starting with >)
            if line.strip().startswith('>'):
                continue
                
            # Skip signature lines
            if line.strip() == '--' or line.strip().startswith('Sent from'):
                break
                
            # Skip lines that look like email headers
            if any(header in line for header in ['From:', 'To:', 'Subject:', 'Date:']):
                continue
                
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)
    
    def _extract_comma_separated_numbers(self, text: str) -> List[int]:
        """Extract numbers from comma-separated format."""
        # Look for patterns like "1, 3, 5" or "1,3,5" or "1, 3 and 5"
        patterns = [
            r'(\d+(?:\s*,\s*\d+)*(?:\s+and\s+\d+)?)',  # Numbers with commas and optional 'and'
            r'(\d+(?:\s*,\s*\d+)+)',  # Just comma-separated
        ]
        
        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Extract individual numbers
                nums = re.findall(r'\d+', match)
                numbers.extend([int(n) for n in nums if 1 <= int(n) <= 50])  # Reasonable range
                
        return numbers
    
    def _extract_numbers_on_lines(self, text: str) -> List[int]:
        """Extract numbers that appear on individual lines."""
        numbers = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lines that are just numbers or numbers with punctuation
            if re.match(r'^\d+[.\):]?\s*$', line):
                num = int(re.findall(r'\d+', line)[0])
                if 1 <= num <= 50:  # Reasonable range
                    numbers.append(num)
                    
        return numbers
    
    def _extract_numbers_with_context(self, text: str) -> List[int]:
        """Extract numbers mentioned with context words."""
        numbers = []
        
        # Look for patterns like "event 1", "number 3", "#5", etc.
        context_patterns = [
            r'(?:event|number|#)\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)\s+(?:event|one)',
            r'interested\s+in\s+(\d+)',
            r'select\s+(\d+)',
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                num = int(match)
                if 1 <= num <= 50:  # Reasonable range
                    numbers.append(num)
                    
        return numbers
    
    def get_selected_events(self, event_numbers: List[int], 
                          digest_date: Optional[datetime] = None) -> EventCollection:
        """
        Get the actual event objects based on selected numbers.
        
        Args:
            event_numbers: List of selected event numbers (1-based)
            digest_date: Date of the digest (to find the right events)
            
        Returns:
            EventCollection of selected events
        """
        # Get the most recent digest info
        if not digest_date:
            digest_date = self.digest_tracker.get_last_digest_date()
            
        if not digest_date:
            logger.warning("No digest date found, using latest events")
            events = self.storage_manager.load_latest()
        else:
            # Load events from around the digest date
            events = self.storage_manager.load_latest()
            
        # Get upcoming events (same logic as digest generation)
        upcoming = events.get_upcoming(from_date=digest_date)
        upcoming.sort(key=lambda e: e.date)
        
        # Select events based on numbers (1-based indexing)
        selected = EventCollection()
        for num in event_numbers:
            if 1 <= num <= len(upcoming):
                selected.add(upcoming[num - 1], check_duplicates=False)
            else:
                logger.warning(f"Event number {num} out of range (max: {len(upcoming)})")
                
        return selected
    
    def save_selections(self, selected_events: EventCollection, reply_from: str):
        """Save the photographer's selections for tracking."""
        selections_file = Path("data/selections.json")
        selections_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing selections
        if selections_file.exists():
            with open(selections_file, 'r') as f:
                selections = json.load(f)
        else:
            selections = []
            
        # Add new selection
        selection_entry = {
            'date': datetime.now().isoformat(),
            'from': reply_from,
            'event_ids': [event.event_id for event in selected_events],
            'event_names': [event.name for event in selected_events],
            'status': 'pending_outreach'
        }
        
        selections.append(selection_entry)
        
        # Save back
        with open(selections_file, 'w') as f:
            json.dump(selections, f, indent=2, default=str)
            
        logger.info(f"Saved {len(selected_events)} event selections")


class ReplyProcessor:
    """Process replies and prepare for outreach."""
    
    def __init__(self):
        self.parser = ReplyParser()
        
    def process_reply(self, reply: Dict) -> Optional[EventCollection]:
        """
        Process a single reply and return selected events.
        
        Args:
            reply: Reply dict with 'from', 'subject', 'date', 'body'
            
        Returns:
            EventCollection of selected events or None
        """
        logger.info(f"Processing reply from {reply['from']}")
        
        # Parse the reply body
        event_numbers = self.parser.parse_reply(reply['body'])
        
        if not event_numbers:
            logger.warning("No event selections found in reply")
            return None
            
        # Get the selected events
        selected_events = self.parser.get_selected_events(event_numbers)
        
        if len(selected_events) == 0:
            logger.warning("No valid events found for selected numbers")
            return None
            
        # Save the selections
        self.parser.save_selections(selected_events, reply['from'])
        
        logger.info(f"Successfully processed {len(selected_events)} event selections")
        return selected_events
    
    def get_pending_selections(self) -> List[Dict]:
        """Get all pending event selections for outreach."""
        selections_file = Path("data/selections.json")
        
        if not selections_file.exists():
            return []
            
        with open(selections_file, 'r') as f:
            selections = json.load(f)
            
        # Filter to pending selections
        pending = [s for s in selections if s['status'] == 'pending_outreach']
        
        return pending
    
    def mark_selection_processed(self, selection_date: str):
        """Mark a selection as processed after sending outreach."""
        selections_file = Path("data/selections.json")
        
        if not selections_file.exists():
            return
            
        with open(selections_file, 'r') as f:
            selections = json.load(f)
            
        # Update status
        for selection in selections:
            if selection['date'] == selection_date:
                selection['status'] = 'outreach_sent'
                selection['processed_date'] = datetime.now().isoformat()
                
        # Save back
        with open(selections_file, 'w') as f:
            json.dump(selections, f, indent=2, default=str)