"""
Enhanced event data models with validation and utilities.
"""

from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import hashlib
import re
from loguru import logger


@dataclass
class EventModel:
    """Enhanced event model with validation and utilities."""
    
    name: str
    date: datetime
    location: str
    source_url: str
    contact_email: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    event_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate and process event data after initialization."""
        # Clean and validate data
        self.name = self._clean_text(self.name)
        self.location = self._clean_text(self.location)
        
        if self.description:
            self.description = self._clean_text(self.description)
            
        # Generate unique ID if not provided
        if not self.event_id:
            self.event_id = self.generate_id()
            
        # Extract contact email from description if not provided
        if not self.contact_email and self.description:
            self.contact_email = self._extract_email(self.description)
    
    def generate_id(self) -> str:
        """Generate a unique ID for the event based on key fields."""
        # Create a unique identifier from name, date, and location
        id_string = f"{self.name}|{self.date.date()}|{self.location}"
        return hashlib.md5(id_string.encode()).hexdigest()[:12]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text fields."""
        if not text:
            return text
        # Remove excessive whitespace
        text = ' '.join(text.split())
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        return text.strip()
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "name": self.name,
            "date": self.date.isoformat(),
            "location": self.location,
            "source_url": self.source_url,
            "contact_email": self.contact_email,
            "description": self.description,
            "source": self.source,
            "scraped_at": self.scraped_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EventModel':
        """Create EventModel from dictionary."""
        # Parse dates
        date = datetime.fromisoformat(data['date'])
        scraped_at = datetime.fromisoformat(data.get('scraped_at', datetime.now().isoformat()))
        
        return cls(
            name=data['name'],
            date=date,
            location=data['location'],
            source_url=data['source_url'],
            contact_email=data.get('contact_email'),
            description=data.get('description'),
            source=data.get('source'),
            scraped_at=scraped_at,
            event_id=data.get('event_id')
        )
    
    def to_csv_row(self) -> List[str]:
        """Convert event to CSV row."""
        return [
            self.event_id,
            self.name,
            self.date.strftime('%Y-%m-%d %H:%M:%S'),
            self.location,
            self.source_url,
            self.contact_email or '',
            self.description or '',
            self.source or '',
            self.scraped_at.strftime('%Y-%m-%d %H:%M:%S')
        ]
    
    @classmethod
    def csv_headers(cls) -> List[str]:
        """Get CSV headers."""
        return [
            'event_id',
            'name',
            'date',
            'location',
            'source_url',
            'contact_email',
            'description',
            'source',
            'scraped_at'
        ]
    
    def is_duplicate_of(self, other: 'EventModel', fuzzy: bool = True) -> bool:
        """Check if this event is a duplicate of another."""
        # Exact match on ID
        if self.event_id == other.event_id:
            return True
            
        if not fuzzy:
            return False
            
        # Fuzzy matching
        # Same date and very similar name
        if self.date.date() == other.date.date():
            name_similarity = self._string_similarity(self.name.lower(), other.name.lower())
            if name_similarity > 0.8:
                return True
                
        return False
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        # Simple character-based similarity
        longer = str1 if len(str1) > len(str2) else str2
        shorter = str2 if longer == str1 else str1
        
        if not longer:
            return 1.0
            
        matches = sum(1 for i, char in enumerate(shorter) if i < len(longer) and char == longer[i])
        return matches / len(longer)


class EventCollection:
    """Collection of events with utility methods."""
    
    def __init__(self, events: Optional[List[EventModel]] = None):
        self.events: List[EventModel] = events or []
        self._id_index: Dict[str, EventModel] = {}
        self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild the ID index."""
        self._id_index = {event.event_id: event for event in self.events}
    
    def add(self, event: EventModel, check_duplicates: bool = True) -> bool:
        """Add an event to the collection."""
        if check_duplicates and self.has_duplicate(event):
            logger.debug(f"Skipping duplicate event: {event.name}")
            return False
            
        self.events.append(event)
        self._id_index[event.event_id] = event
        return True
    
    def add_many(self, events: List[EventModel], check_duplicates: bool = True) -> int:
        """Add multiple events, returning count of added events."""
        added = 0
        for event in events:
            if self.add(event, check_duplicates):
                added += 1
        return added
    
    def has_duplicate(self, event: EventModel, fuzzy: bool = True) -> bool:
        """Check if collection contains a duplicate of the event."""
        # Quick check by ID
        if event.event_id in self._id_index:
            return True
            
        if fuzzy:
            # Check for fuzzy duplicates
            for existing in self.events:
                if event.is_duplicate_of(existing, fuzzy=True):
                    return True
                    
        return False
    
    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        """Get event by ID."""
        return self._id_index.get(event_id)
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[EventModel]:
        """Get events within a date range."""
        return [
            event for event in self.events
            if start_date <= event.date <= end_date
        ]
    
    def get_by_source(self, source: str) -> List[EventModel]:
        """Get events from a specific source."""
        return [event for event in self.events if event.source == source]
    
    def get_upcoming(self, from_date: Optional[datetime] = None) -> List[EventModel]:
        """Get upcoming events from a given date (default: now)."""
        from_date = from_date or datetime.now()
        return [event for event in self.events if event.date >= from_date]
    
    def sort_by_date(self, reverse: bool = False):
        """Sort events by date."""
        self.events.sort(key=lambda e: e.date, reverse=reverse)
    
    def remove_duplicates(self) -> int:
        """Remove duplicate events, returning count removed."""
        seen_ids: Set[str] = set()
        unique_events = []
        removed = 0
        
        for event in self.events:
            if event.event_id not in seen_ids:
                # Check for fuzzy duplicates among unique events
                is_duplicate = False
                for unique_event in unique_events:
                    if event.is_duplicate_of(unique_event, fuzzy=True):
                        is_duplicate = True
                        removed += 1
                        break
                        
                if not is_duplicate:
                    seen_ids.add(event.event_id)
                    unique_events.append(event)
            else:
                removed += 1
                
        self.events = unique_events
        self._rebuild_index()
        return removed
    
    def to_list(self) -> List[Dict]:
        """Convert collection to list of dictionaries."""
        return [event.to_dict() for event in self.events]
    
    def __len__(self) -> int:
        return len(self.events)
    
    def __iter__(self):
        return iter(self.events)
    
    def __getitem__(self, index: int) -> EventModel:
        return self.events[index]