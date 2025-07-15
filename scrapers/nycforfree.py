"""
NYC For Free events scraper.
"""

from datetime import datetime
from typing import List, Optional
import re
from urllib.parse import urljoin
from loguru import logger
from dateutil import parser as date_parser

from .base import BaseScraper, Event


class NYCForFreeScraper(BaseScraper):
    """Scraper for NYC For Free events."""
    
    BASE_URL = "https://www.nycforfree.co"
    EVENTS_URL = "https://www.nycforfree.co/events"
    
    def __init__(self, user_agent: Optional[str] = None):
        super().__init__(user_agent)
        
    def scrape(self) -> List[Event]:
        """Scrape events from NYC For Free."""
        logger.info("Starting NYC For Free scraper")
        events = []
        
        try:
            soup = self.get_soup(self.EVENTS_URL)
            
            # Find all event items - they use article tags with specific classes
            event_items = soup.find_all('article', class_='eventlist-event')
            
            if not event_items:
                # Try alternative selectors
                event_items = soup.find_all('div', class_='eventlist-event') or \
                             soup.find_all('div', class_='event-item')
            
            logger.info(f"Found {len(event_items)} event items to parse")
            
            for item in event_items:
                try:
                    event = self._parse_event_item(item)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing event item: {e}")
                    
        except Exception as e:
            logger.error(f"Error scraping NYC For Free: {e}")
            
        logger.info(f"NYC For Free scraper completed. Total events found: {len(events)}")
        return events
    
    def _parse_event_item(self, item) -> Optional[Event]:
        """Parse an event from an item element."""
        try:
            # Find event title/link
            title_elem = item.find('h1', class_='eventlist-title') or \
                        item.find('h2', class_='eventlist-title') or \
                        item.find('a', class_='eventlist-title-link')
            
            if not title_elem:
                # Try to find any heading or link within the item
                title_elem = item.find(['h1', 'h2', 'h3']) or item.find('a')
            
            if not title_elem:
                return None
            
            # Get event name
            name = title_elem.get_text(strip=True)
            
            # Get event URL
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
            if link_elem and link_elem.get('href'):
                event_url = urljoin(self.BASE_URL, link_elem['href'])
            else:
                # Try to find any link in the item
                any_link = item.find('a', href=True)
                event_url = urljoin(self.BASE_URL, any_link['href']) if any_link else self.EVENTS_URL
            
            # Extract date
            date_elem = item.find('time', class_='event-date') or \
                       item.find('span', class_='event-date') or \
                       item.find('div', class_='eventlist-datetag')
            
            event_date = None
            if date_elem:
                # Try to get datetime attribute first
                if date_elem.get('datetime'):
                    event_date = date_parser.parse(date_elem['datetime'])
                else:
                    date_text = date_elem.get_text(strip=True)
                    event_date = self._parse_date(date_text)
            
            # If no date found in specific elements, search in text
            if not event_date:
                full_text = item.get_text()
                event_date = self._extract_date_from_text(full_text)
            
            # Extract location
            location_elem = item.find('span', class_='eventlist-address') or \
                           item.find('div', class_='event-location') or \
                           item.find('address')
            
            location = "New York, NY"  # Default
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            # Extract description if available
            desc_elem = item.find('div', class_='eventlist-description') or \
                       item.find('div', class_='event-description')
            
            description = None
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:500]
            
            # Only create event if we have minimum required fields
            if name and event_date:
                return Event(
                    name=name,
                    date=event_date,
                    location=location,
                    source_url=event_url,
                    description=description,
                    source="NYC For Free"
                )
                
        except Exception as e:
            logger.error(f"Error parsing event item: {e}")
            
        return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from various formats."""
        try:
            # Clean up the date text
            date_text = ' '.join(date_text.split())
            
            # NYC For Free often uses formats like "January 15, 2024"
            return date_parser.parse(date_text, fuzzy=True)
            
        except Exception as e:
            logger.warning(f"Could not parse date: {date_text} - {e}")
            return None
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Try to extract date from free text."""
        try:
            # Look for common date patterns
            patterns = [
                r'(\w+\s+\d{1,2},?\s+\d{4})',  # January 15, 2024
                r'(\d{1,2}/\d{1,2}/\d{2,4})',   # 01/15/2024
                r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?)',  # January 15th
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        return date_parser.parse(match.group(1), fuzzy=True)
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Could not extract date from text: {e}")
            
        return None