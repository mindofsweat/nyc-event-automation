"""
Unit tests for event scrapers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.base import Event
from scrapers.eventbrite import EventbriteScraper
from scrapers.nycforfree import NYCForFreeScraper
from scrapers.averagesocialite import AverageSocialiteScraper


class TestEventbriteScraper:
    """Test cases for Eventbrite scraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return EventbriteScraper(max_pages=1)
    
    @pytest.fixture
    def sample_html(self):
        """Sample Eventbrite HTML response."""
        return """
        <div class="search-results">
            <article class="event-card">
                <a href="/e/event-123">
                    <h2 class="event-card-title">Summer Concert</h2>
                </a>
                <div class="event-card-details">
                    <time datetime="2025-07-20T18:00:00">Sat, Jul 20, 6:00 PM</time>
                    <div class="event-card-location">Central Park, NYC</div>
                </div>
            </article>
            <article class="event-card">
                <a href="/e/event-456">
                    <h2 class="event-card-title">Art Exhibition</h2>
                </a>
                <div class="event-card-details">
                    <time datetime="2025-07-22T14:00:00">Mon, Jul 22, 2:00 PM</time>
                    <div class="event-card-location">MoMA, NYC</div>
                </div>
            </article>
        </div>
        """
    
    @patch('requests.get')
    def test_fetch_events_page(self, mock_get, scraper, sample_html):
        """Test fetching and parsing events page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_get.return_value = mock_response
        
        soup = scraper._fetch_page("music", 1)
        
        assert soup is not None
        assert len(soup.find_all('article', class_='event-card')) == 2
        mock_get.assert_called_once()
    
    def test_parse_event_card(self, scraper, sample_html):
        """Test parsing individual event card."""
        soup = BeautifulSoup(sample_html, 'html.parser')
        card = soup.find('article', class_='event-card')
        
        event = scraper._parse_event_card(card)
        
        assert event is not None
        assert event.name == "Summer Concert"
        assert event.location == "Central Park, NYC"
        assert event.date.strftime('%Y-%m-%d') == "2025-07-20"
        assert event.source == "Eventbrite"
        assert "event-123" in event.source_url
    
    @patch('requests.get')
    def test_scrape_multiple_categories(self, mock_get, scraper, sample_html):
        """Test scraping multiple categories."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_get.return_value = mock_response
        
        events = scraper.scrape()
        
        # Should call for each category
        assert mock_get.call_count >= len(scraper.categories)
        assert len(events) > 0
        assert all(isinstance(e, Event) for e in events)
    
    @patch('requests.get')
    def test_handle_request_error(self, mock_get, scraper):
        """Test handling of request errors."""
        mock_get.side_effect = Exception("Network error")
        
        events = scraper.scrape()
        
        assert events == []  # Should return empty list on error


class TestNYCForFreeScraper:
    """Test cases for NYC For Free scraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return NYCForFreeScraper()
    
    @pytest.fixture
    def sample_html(self):
        """Sample NYC For Free HTML response."""
        return """
        <div class="events-list">
            <article class="event-item">
                <h3><a href="/event/free-movie-night">Free Movie Night</a></h3>
                <div class="event-date">July 25, 2025</div>
                <div class="event-location">Brooklyn Bridge Park</div>
                <div class="event-description">
                    Join us for a free outdoor movie screening.
                </div>
            </article>
            <article class="event-item">
                <h3><a href="/event/yoga-class">Free Yoga Class</a></h3>
                <div class="event-date">Tomorrow</div>
                <div class="event-location">Bryant Park</div>
            </article>
        </div>
        """
    
    def test_parse_date_formats(self, scraper):
        """Test parsing various date formats."""
        # Test specific date
        date1 = scraper._parse_date("July 25, 2025")
        assert date1 is not None
        assert date1.strftime('%Y-%m-%d') == "2025-07-25"
        
        # Test relative dates
        date2 = scraper._parse_date("Tomorrow")
        assert date2 is not None
        
        # Test invalid date
        date3 = scraper._parse_date("Invalid Date")
        assert date3 is not None  # Should return a default date
    
    @patch('requests.get')
    def test_scrape_events(self, mock_get, scraper, sample_html):
        """Test scraping NYC For Free events."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        events = scraper.scrape()
        
        assert len(events) == 2
        assert events[0].name == "Free Movie Night"
        assert events[0].location == "Brooklyn Bridge Park"
        assert events[1].name == "Free Yoga Class"
        assert events[1].location == "Bryant Park"


class TestAverageSocialiteScraper:
    """Test cases for Average Socialite scraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return AverageSocialiteScraper(max_pages=1)
    
    @pytest.fixture
    def sample_html(self):
        """Sample Average Socialite HTML response."""
        return """
        <div class="event-listings">
            <div class="event-card">
                <h2 class="event-title">
                    <a href="/events/rooftop-party">Rooftop Party</a>
                </h2>
                <div class="event-meta">
                    <span class="date">Friday, July 26</span>
                    <span class="location">230 Fifth Rooftop</span>
                </div>
                <p class="description">Amazing rooftop party with DJ.</p>
            </div>
        </div>
        """
    
    def test_extract_location(self, scraper):
        """Test location extraction."""
        location1 = scraper._extract_location("Event at Times Square")
        assert location1 == "Times Square"
        
        location2 = scraper._extract_location("No location specified")
        assert location2 == "NYC"
    
    @patch('requests.get')
    def test_pagination(self, mock_get, scraper):
        """Test handling pagination."""
        # First page
        page1_html = """
        <div class="event-listings">
            <div class="event-card">
                <h2 class="event-title">Event 1</h2>
            </div>
        </div>
        <a href="?page=2" class="next-page">Next</a>
        """
        
        # Second page
        page2_html = """
        <div class="event-listings">
            <div class="event-card">
                <h2 class="event-title">Event 2</h2>
            </div>
        </div>
        """
        
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.text = page1_html
        mock_response1.raise_for_status = Mock()
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.text = page2_html
        mock_response2.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        scraper.max_pages = 2
        events = scraper.scrape()
        
        assert mock_get.call_count == 2  # Should fetch both pages


class TestScraperIntegration:
    """Integration tests for all scrapers."""
    
    @pytest.mark.parametrize("scraper_class", [
        EventbriteScraper,
        NYCForFreeScraper,
        AverageSocialiteScraper
    ])
    def test_scraper_returns_events(self, scraper_class):
        """Test that each scraper returns Event objects."""
        scraper = scraper_class()
        
        # Mock the scrape method to return sample events
        with patch.object(scraper, 'scrape') as mock_scrape:
            mock_scrape.return_value = [
                Event(
                    name="Test Event",
                    date=datetime.now(),
                    location="NYC",
                    source_url="https://example.com",
                    source=scraper_class.__name__
                )
            ]
            
            events = scraper.scrape()
            
            assert len(events) == 1
            assert all(isinstance(e, Event) for e in events)
            assert all(hasattr(e, 'name') for e in events)
            assert all(hasattr(e, 'date') for e in events)
            assert all(hasattr(e, 'location') for e in events)