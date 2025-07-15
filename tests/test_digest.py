"""
Tests for email digest generator.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from email_service.digest import DigestGenerator, DigestTracker
from data_store import EventModel, EventCollection


class TestDigestGenerator:
    """Test cases for digest generator."""
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing."""
        collection = EventCollection()
        
        base_date = datetime.now() + timedelta(days=1)
        
        events = [
            EventModel(
                name="Photography Workshop",
                date=base_date,
                location="Manhattan, NYC",
                source_url="https://example.com/workshop",
                description="Learn advanced photography techniques",
                source="Eventbrite"
            ),
            EventModel(
                name="NYC Food & Wine Festival",
                date=base_date + timedelta(days=2),
                location="Brooklyn Bridge Park",
                source_url="https://example.com/food-festival",
                description="Annual food and wine celebration with live music",
                source="NYC For Free"
            ),
            EventModel(
                name="Art Gallery Opening",
                date=base_date + timedelta(days=3),
                location="Chelsea, NYC",
                source_url="https://example.com/art-opening",
                source="Average Socialite"
            ),
        ]
        
        for event in events:
            collection.add(event)
            
        return collection
    
    def test_generate_digest(self, sample_events):
        """Test basic digest generation."""
        generator = DigestGenerator()
        digest = generator.generate_digest(sample_events)
        
        assert 'subject' in digest
        assert 'html_body' in digest
        assert 'text_body' in digest
        assert digest['event_count'] == 3
        
        # Check subject format
        assert "NYC Event Leads" in digest['subject']
        assert "3 new events" in digest['subject']
        
        # Check HTML content
        assert "Photography Workshop" in digest['html_body']
        assert "NYC Food & Wine Festival" in digest['html_body']
        assert "Art Gallery Opening" in digest['html_body']
        assert "Keith" in digest['html_body']
        
        # Check text content
        assert "Photography Workshop" in digest['text_body']
        assert "#1" in digest['text_body']
        assert "#2" in digest['text_body']
        assert "#3" in digest['text_body']
    
    def test_event_formatting(self, sample_events):
        """Test individual event formatting."""
        generator = DigestGenerator()
        event = sample_events[0]
        
        # Test HTML formatting
        html = generator._format_event_html(event, 1)
        assert "#1" in html
        assert event.name in html
        assert event.location in html
        assert event.source_url in html
        
        # Test text formatting
        text = generator._format_event_text(event, 1)
        assert "#1 - Photography Workshop" in text
        assert "Manhattan, NYC" in text
    
    def test_max_events_limit(self, sample_events):
        """Test limiting number of events in digest."""
        generator = DigestGenerator()
        digest = generator.generate_digest(sample_events, max_events=2)
        
        assert digest['event_count'] == 2
        assert "#3" not in digest['text_body']
    
    def test_save_digest(self, sample_events):
        """Test saving digest to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            generator = DigestGenerator()
            digest = generator.generate_digest(sample_events)
            saved_files = generator.save_digest(digest, output_dir)
            
            assert saved_files['html'].exists()
            assert saved_files['text'].exists()
            
            # Verify content
            with open(saved_files['html'], 'r') as f:
                html_content = f.read()
                assert "NYC Event Opportunities" in html_content
                
            with open(saved_files['text'], 'r') as f:
                text_content = f.read()
                assert digest['subject'] in text_content


class TestDigestTracker:
    """Test cases for digest tracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create tracker with temporary file."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            tracker = DigestTracker(tracking_file=Path(f.name))
            yield tracker
            # Cleanup
            Path(f.name).unlink(missing_ok=True)
    
    def test_mark_events_sent(self, tracker):
        """Test marking events as sent."""
        event_ids = ['event1', 'event2', 'event3']
        digest_date = datetime.now()
        
        tracker.mark_events_sent(event_ids, digest_date)
        
        assert 'event1' in tracker.tracking_data['sent_events']
        assert len(tracker.tracking_data['digest_history']) == 1
        assert tracker.tracking_data['digest_history'][0]['event_count'] == 3
    
    def test_filter_new_events(self, tracker):
        """Test filtering out already sent events."""
        # Create events
        events = EventCollection()
        event1 = EventModel("Event 1", datetime.now(), "NYC", "url1")
        event2 = EventModel("Event 2", datetime.now(), "NYC", "url2")
        event3 = EventModel("Event 3", datetime.now(), "NYC", "url3")
        
        events.add(event1)
        events.add(event2)
        events.add(event3)
        
        # Mark event1 as sent
        tracker.mark_events_sent([event1.event_id], datetime.now())
        
        # Filter new events
        new_events = tracker.filter_new_events(events)
        
        assert len(new_events) == 2
        assert new_events.get_by_id(event1.event_id) is None
        assert new_events.get_by_id(event2.event_id) is not None
    
    def test_persistence(self, tracker):
        """Test that tracking data persists."""
        # Add some data
        tracker.mark_events_sent(['event1', 'event2'], datetime.now())
        tracking_file = tracker.tracking_file
        
        # Create new tracker with same file
        tracker2 = DigestTracker(tracking_file=tracking_file)
        
        assert 'event1' in tracker2.tracking_data['sent_events']
        assert len(tracker2.tracking_data['digest_history']) == 1