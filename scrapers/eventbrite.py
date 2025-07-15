"""
Eventbrite NYC events scraper.
"""

from datetime import datetime
from typing import List, Optional
import re
from urllib.parse import urljoin, quote
from loguru import logger
from dateutil import parser as date_parser

from .base import BaseScraper, Event


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite NYC events."""
    
    BASE_URL = "https://www.eventbrite.com"
    SEARCH_URL = "https://www.eventbrite.com/d/ny--new-york/events/"
    
    def __init__(self, user_agent: Optional[str] = None, max_pages: int = 5):
        super().__init__(user_agent)
        self.max_pages = max_pages
        
    def scrape(self) -> List[Event]:
        """Scrape events from Eventbrite NYC."""
        logger.info("Starting Eventbrite NYC scraper")
        events = []
        
        # Categories to search
        categories = [
            "music",
            "food-and-drink", 
            "arts",
            "business",
            "community",
            "film-and-media",
            "fashion",
            "health",
            "hobbies",
            "holiday",
            "science-and-tech",
            "sports-and-fitness"
        ]
        
        for category in categories:
            logger.info(f"Scraping category: {category}")
            try:
                category_events = self._scrape_category(category)
                events.extend(category_events)
                logger.info(f"Found {len(category_events)} events in {category}")
            except Exception as e:
                logger.error(f"Error scraping category {category}: {e}")
                
        logger.info(f"Eventbrite scraper completed. Total events found: {len(events)}")
        return events
    
    def _scrape_category(self, category: str) -> List[Event]:
        """Scrape events from a specific category."""
        events = []
        url = f"{self.SEARCH_URL}--{category}/"
        
        for page in range(1, self.max_pages + 1):
            try:
                page_url = f"{url}?page={page}" if page > 1 else url
                logger.debug(f"Scraping page {page}: {page_url}")
                
                soup = self.get_soup(page_url)
                event_cards = soup.find_all('div', class_='discover-search-desktop-card')
                
                if not event_cards:
                    # Try alternative selector
                    event_cards = soup.find_all('article', class_='listing-card')
                
                if not event_cards:
                    logger.warning(f"No events found on page {page}")
                    break
                    
                for card in event_cards:
                    try:
                        event = self._parse_event_card(card)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.error(f"Error parsing event card: {e}")
                        
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
                
        return events
    
    def _parse_event_card(self, card) -> Optional[Event]:
        """Parse an event from a card element."""
        try:
            # Find event link and title
            link_elem = card.find('a', class_='listing-card-title-link') or \
                       card.find('a', href=re.compile(r'/e/'))
            
            if not link_elem:
                return None
                
            event_url = link_elem.get('href', '')
            if not event_url.startswith('http'):
                event_url = urljoin(self.BASE_URL, event_url)
                
            # Extract event name
            name = link_elem.get_text(strip=True) or \
                   card.find('h3', class_='listing-card-title').get_text(strip=True)
            
            # Extract date
            date_elem = card.find('time') or \
                       card.find('div', class_='listing-card-date')
            
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                event_date = self._parse_date(date_text)
            else:
                event_date = None
                
            # Extract location
            location_elem = card.find('div', class_='listing-card-venue') or \
                           card.find('div', class_='card-text--truncated__two')
            
            location = location_elem.get_text(strip=True) if location_elem else "New York, NY"
            
            # Get more details from event page if needed
            if event_url and name and event_date:
                # For efficiency, we'll skip detailed page scraping in bulk operations
                # but you can enable it for more complete data
                # details = self._get_event_details(event_url)
                
                return Event(
                    name=name,
                    date=event_date,
                    location=location,
                    source_url=event_url,
                    source="Eventbrite"
                )
                
        except Exception as e:
            logger.error(f"Error parsing event card: {e}")
            
        return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from various Eventbrite date formats."""
        try:
            # Remove extra whitespace and newlines
            date_text = ' '.join(date_text.split())
            
            # Try to parse directly
            return date_parser.parse(date_text, fuzzy=True)
            
        except Exception as e:
            logger.warning(f"Could not parse date: {date_text} - {e}")
            return None
    
    def _get_event_details(self, event_url: str) -> dict:
        """Get additional event details from the event page."""
        details = {}
        
        try:
            soup = self.get_soup(event_url)
            
            # Try to find organizer contact
            organizer_elem = soup.find('a', href=re.compile(r'/o/'))
            if organizer_elem:
                details['organizer_url'] = urljoin(self.BASE_URL, organizer_elem['href'])
                
            # Get description
            desc_elem = soup.find('div', class_='structured-content-rich-text')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)[:500]
                
        except Exception as e:
            logger.error(f"Error getting event details: {e}")
            
        return details