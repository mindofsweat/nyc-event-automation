"""
Tests for Eventbrite scraper.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup

from scrapers.eventbrite import EventbriteScraper
from scrapers.base import Event


class TestEventbriteScraper:
    """Test cases for Eventbrite scraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create an EventbriteScraper instance."""
        return EventbriteScraper(max_pages=1)
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML response from Eventbrite."""
        return """
        <div class="discover-search-desktop-card">
            <a class="listing-card-title-link" href="/e/sample-event-12345">
                NYC Food Festival
            </a>
            <time>Saturday, July 20, 2024</time>
            <div class="listing-card-venue">Brooklyn Bridge Park, NY</div>
        </div>
        """
    
    def test_parse_event_card(self, scraper, sample_html):
        """Test parsing a single event card."""
        soup = BeautifulSoup(sample_html, 'lxml')
        card = soup.find('div', class_='discover-search-desktop-card')
        
        event = scraper._parse_event_card(card)
        
        assert event is not None
        assert event.name == "NYC Food Festival"
        assert event.location == "Brooklyn Bridge Park, NY"
        assert event.source == "Eventbrite"
        assert "sample-event-12345" in event.source_url
        
    def test_parse_date(self, scraper):
        """Test date parsing."""
        test_cases = [
            ("Saturday, July 20, 2024", datetime(2024, 7, 20)),
            ("Jul 20, 2024", datetime(2024, 7, 20)),
            ("Tomorrow at 7:00 PM", None),  # Fuzzy dates might not parse consistently
        ]
        
        for date_text, expected in test_cases:
            result = scraper._parse_date(date_text)
            if expected:
                assert result.date() == expected.date()
    
    @patch.object(EventbriteScraper, 'get_soup')
    def test_scrape_category(self, mock_get_soup, scraper):
        """Test scraping a category."""
        # Mock the response
        mock_soup = BeautifulSoup("""
        <html>
            <div class="discover-search-desktop-card">
                <a class="listing-card-title-link" href="/e/event-1">Event 1</a>
                <time>July 20, 2024</time>
                <div class="listing-card-venue">Venue 1</div>
            </div>
            <div class="discover-search-desktop-card">
                <a class="listing-card-title-link" href="/e/event-2">Event 2</a>
                <time>July 21, 2024</time>
                <div class="listing-card-venue">Venue 2</div>
            </div>
        </html>
        """, 'lxml')
        
        mock_get_soup.return_value = mock_soup
        
        events = scraper._scrape_category("music")
        
        assert len(events) == 2
        assert events[0].name == "Event 1"
        assert events[1].name == "Event 2"
        
    def test_event_to_dict(self):
        """Test Event.to_dict method."""
        event = Event(
            name="Test Event",
            date=datetime(2024, 7, 20, 19, 0),
            location="NYC",
            source_url="https://example.com",
            source="Eventbrite"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['name'] == "Test Event"
        assert event_dict['location'] == "NYC"
        assert event_dict['source'] == "Eventbrite"
        assert 'scraped_at' in event_dict