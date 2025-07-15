"""
Base scraper class with common functionality for all event scrapers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger
import time


class Event:
    """Data model for an event."""
    
    def __init__(
        self,
        name: str,
        date: datetime,
        location: str,
        source_url: str,
        contact_email: Optional[str] = None,
        description: Optional[str] = None,
        source: Optional[str] = None
    ):
        self.name = name
        self.date = date
        self.location = location
        self.source_url = source_url
        self.contact_email = contact_email
        self.description = description
        self.source = source
        self.scraped_at = datetime.now()
        
    def to_dict(self) -> Dict:
        """Convert event to dictionary for storage."""
        return {
            "name": self.name,
            "date": self.date.isoformat(),
            "location": self.location,
            "source_url": self.source_url,
            "contact_email": self.contact_email,
            "description": self.description,
            "source": self.source,
            "scraped_at": self.scraped_at.isoformat()
        }
    
    def __repr__(self):
        return f"Event(name='{self.name}', date={self.date.strftime('%Y-%m-%d')}, location='{self.location}')"


class BaseScraper(ABC):
    """Abstract base class for event scrapers."""
    
    def __init__(self, user_agent: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    @abstractmethod
    def scrape(self) -> List[Event]:
        """Scrape events from the source. Must be implemented by subclasses."""
        pass
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """Get a page with retry logic."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
                    
    def get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        """Get BeautifulSoup object from URL."""
        response = self.get_page(url, **kwargs)
        return BeautifulSoup(response.content, 'lxml')