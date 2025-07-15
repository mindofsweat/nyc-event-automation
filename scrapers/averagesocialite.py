"""
Average Socialite NYC events scraper.
"""

from datetime import datetime
from typing import List, Optional
import re
from urllib.parse import urljoin, urlparse
from loguru import logger
from dateutil import parser as date_parser

from .base import BaseScraper, Event


class AverageSocialiteScraper(BaseScraper):
    """Scraper for Average Socialite NYC events."""
    
    BASE_URL = "https://www.averagesocialite.com"
    EVENTS_URL = "https://www.averagesocialite.com/nyc-events?tag=NYC"
    
    def __init__(self, user_agent: Optional[str] = None, max_pages: int = 3):
        super().__init__(user_agent)
        self.max_pages = max_pages
        
    def scrape(self) -> List[Event]:
        """Scrape events from Average Socialite."""
        logger.info("Starting Average Socialite scraper")
        events = []
        
        # Average Socialite uses pagination
        for page in range(1, self.max_pages + 1):
            try:
                page_url = self.EVENTS_URL if page == 1 else f"{self.EVENTS_URL}&page={page}"
                logger.info(f"Scraping page {page}: {page_url}")
                
                soup = self.get_soup(page_url)
                
                # Find event containers - they typically use article or div with specific classes
                event_containers = soup.find_all('article', class_='blog-item') or \
                                 soup.find_all('div', class_='blog-item') or \
                                 soup.find_all('div', class_='event-item')
                
                # Alternative: look for summary blocks
                if not event_containers:
                    event_containers = soup.find_all('div', class_='summary-item')
                
                if not event_containers:
                    logger.warning(f"No events found on page {page}")
                    break
                
                logger.info(f"Found {len(event_containers)} event containers on page {page}")
                
                for container in event_containers:
                    try:
                        event = self._parse_event_container(container)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.error(f"Error parsing event container: {e}")
                        
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
                
        logger.info(f"Average Socialite scraper completed. Total events found: {len(events)}")
        return events
    
    def _parse_event_container(self, container) -> Optional[Event]:
        """Parse an event from a container element."""
        try:
            # Find event title and link
            title_elem = container.find('h1', class_='blog-title') or \
                        container.find('h2', class_='blog-title') or \
                        container.find('h3', class_='summary-title') or \
                        container.find('a', class_='summary-title-link')
            
            if not title_elem:
                # Try to find any heading with a link
                for heading in container.find_all(['h1', 'h2', 'h3']):
                    if heading.find('a'):
                        title_elem = heading
                        break
            
            if not title_elem:
                return None
            
            # Get event name
            name = title_elem.get_text(strip=True)
            
            # Get event URL
            link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
            if link_elem and link_elem.get('href'):
                event_url = urljoin(self.BASE_URL, link_elem['href'])
            else:
                # Try to find any link in the container
                any_link = container.find('a', href=True)
                event_url = urljoin(self.BASE_URL, any_link['href']) if any_link else self.EVENTS_URL
            
            # Extract date - Average Socialite often includes dates in the title or description
            event_date = self._extract_date_from_container(container)
            
            # Extract location
            location = self._extract_location_from_container(container)
            
            # Extract description
            desc_elem = container.find('div', class_='summary-excerpt') or \
                       container.find('div', class_='blog-excerpt') or \
                       container.find('p')
            
            description = None
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:500]
            
            # Get more details from the event page if we have basic info
            if name and event_url:
                # For efficiency, we'll only fetch details if we don't have a date
                if not event_date:
                    details = self._get_event_details(event_url)
                    if details.get('date'):
                        event_date = details['date']
                    if details.get('location') and location == "New York, NY":
                        location = details['location']
                
                # Only create event if we have a date
                if event_date:
                    return Event(
                        name=name,
                        date=event_date,
                        location=location,
                        source_url=event_url,
                        description=description,
                        source="Average Socialite"
                    )
                    
        except Exception as e:
            logger.error(f"Error parsing event container: {e}")
            
        return None
    
    def _extract_date_from_container(self, container) -> Optional[datetime]:
        """Extract date from various parts of the container."""
        try:
            # Look for time elements
            time_elem = container.find('time')
            if time_elem:
                if time_elem.get('datetime'):
                    return date_parser.parse(time_elem['datetime'])
                else:
                    return self._parse_date(time_elem.get_text(strip=True))
            
            # Look for date in meta elements
            meta_date = container.find('span', class_='blog-meta-item--date') or \
                       container.find('span', class_='date')
            if meta_date:
                return self._parse_date(meta_date.get_text(strip=True))
            
            # Search in the full text
            full_text = container.get_text()
            return self._extract_date_from_text(full_text)
            
        except Exception as e:
            logger.debug(f"Could not extract date: {e}")
            return None
    
    def _extract_location_from_container(self, container) -> str:
        """Extract location from the container."""
        try:
            # Look for location elements
            location_elem = container.find('span', class_='location') or \
                           container.find('div', class_='event-location') or \
                           container.find('address')
            
            if location_elem:
                location = location_elem.get_text(strip=True)
                # Ensure it's in NYC
                if 'NY' in location or 'New York' in location or 'Manhattan' in location or 'Brooklyn' in location:
                    return location
            
            # Search in text for NYC locations
            full_text = container.get_text()
            location_patterns = [
                r'at\s+([^,]+(?:Manhattan|Brooklyn|Queens|Bronx|NYC)[^,]*)',
                r'@\s*([^,\n]+)',
                r'Location:\s*([^\n]+)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                    
        except Exception as e:
            logger.debug(f"Could not extract location: {e}")
            
        return "New York, NY"
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from various formats."""
        try:
            # Clean up the date text
            date_text = ' '.join(date_text.split())
            
            # Handle "Through" dates by taking the first date
            if 'through' in date_text.lower() or '-' in date_text:
                date_text = re.split(r'through|-', date_text, flags=re.IGNORECASE)[0].strip()
            
            return date_parser.parse(date_text, fuzzy=True)
            
        except Exception as e:
            logger.warning(f"Could not parse date: {date_text} - {e}")
            return None
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Try to extract date from free text."""
        try:
            # Common date patterns in Average Socialite
            patterns = [
                r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',  # January 15th, 2024
                r'(\d{1,2}/\d{1,2}/\d{2,4})',                   # 01/15/2024
                r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*-\s*\d{1,2})?)',  # January 15th or January 15-17
                r'(?:When|Date):\s*([^\n]+)',                   # When: January 15
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(1).strip()
                        # Handle date ranges by taking first date
                        if '-' in date_str:
                            date_str = date_str.split('-')[0].strip()
                        return date_parser.parse(date_str, fuzzy=True)
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Could not extract date from text: {e}")
            
        return None
    
    def _get_event_details(self, event_url: str) -> dict:
        """Get additional event details from the event page."""
        details = {}
        
        try:
            soup = self.get_soup(event_url)
            
            # Look for structured data
            content_area = soup.find('div', class_='blog-item-content') or \
                          soup.find('div', class_='content') or \
                          soup.find('article')
            
            if content_area:
                # Extract date from content
                date = self._extract_date_from_text(content_area.get_text())
                if date:
                    details['date'] = date
                
                # Extract location
                location = self._extract_location_from_container(content_area)
                if location != "New York, NY":
                    details['location'] = location
                    
        except Exception as e:
            logger.error(f"Error getting event details from {event_url}: {e}")
            
        return details