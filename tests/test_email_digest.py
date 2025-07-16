"""
Unit tests for email digest generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import json

from email_service.digest import DigestGenerator, DigestTracker
from data_store.models import EventModel, EventCollection


class TestDigestGenerator:
    """Test cases for digest email generation."""
    
    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator with test templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        html_template = template_dir / "digest_template.html"
        html_template.write_text("""
        <html>
        <body>
            <h1>{{event_count}} Events</h1>
            {% for event in events %}
            <div>{{event.display_number}}. {{event.name}}</div>
            {% endfor %}
        </body>
        </html>
        """)
        
        text_template = template_dir / "digest_template.txt"
        text_template.write_text("""
{{event_count}} Events
{% for event in events %}
{{event.display_number}}. {{event.name}}
{% endfor %}
        """)
        
        return DigestGenerator(template_dir=str(template_dir))
    
    @pytest.fixture
    def sample_events(self):
        """Create sample event collection."""
        collection = EventCollection()
        for i in range(1, 6):
            collection.add(EventModel(
                name=f"Event {i}",
                date=datetime.now() + timedelta(days=i),
                location=f"Location {i}",
                source_url=f"https://example.com/event{i}",
                description=f"Description for event {i}"
            ))
        return collection
    
    def test_generate_digest(self, generator, sample_events):
        """Test generating email digest."""
        digest = generator.generate_digest(sample_events)
        
        assert digest is not None
        assert digest['event_count'] == 5
        assert "5 Events" in digest['html_body']
        assert "5 Events" in digest['text_body']
        
        # Check events are numbered
        for i in range(1, 6):
            assert f"{i}. Event {i}" in digest['html_body']
            assert f"{i}. Event {i}" in digest['text_body']
    
    def test_generate_digest_with_limit(self, generator, sample_events):
        """Test generating digest with event limit."""
        digest = generator.generate_digest(sample_events, max_events=3)
        
        assert digest['event_count'] == 3
        assert "3 Events" in digest['html_body']
        
        # Only first 3 events should be included
        assert "1. Event 1" in digest['html_body']
        assert "3. Event 3" in digest['html_body']
        assert "4. Event 4" not in digest['html_body']
    
    def test_generate_subject_line(self, generator):
        """Test subject line generation."""
        # Test with multiple events
        subject1 = generator._generate_subject(5)
        assert "5 new events" in subject1
        assert datetime.now().strftime('%B') in subject1
        
        # Test with single event
        subject2 = generator._generate_subject(1)
        assert "1 new event" in subject2
    
    def test_prepare_events_for_template(self, generator, sample_events):
        """Test preparing events for template."""
        events_list = list(sample_events)
        prepared = generator._prepare_events_for_template(events_list[:3])
        
        assert len(prepared) == 3
        assert prepared[0]['display_number'] == 1
        assert prepared[0]['date_formatted'] is not None
        assert prepared[0]['name'] == "Event 1"
    
    def test_save_digest(self, generator, sample_events, tmp_path):
        """Test saving digest to files."""
        generator.output_dir = tmp_path / "digests"
        
        digest = generator.generate_digest(sample_events)
        saved_files = generator.save_digest(digest)
        
        assert 'html' in saved_files
        assert 'text' in saved_files
        
        # Check files exist
        assert Path(saved_files['html']).exists()
        assert Path(saved_files['text']).exists()
        
        # Check content
        with open(saved_files['html']) as f:
            html_content = f.read()
            assert "5 Events" in html_content
    
    def test_create_digest_mapping(self, generator, sample_events, tmp_path):
        """Test creating digest mapping file."""
        generator.output_dir = tmp_path / "data"
        
        events_list = list(sample_events)
        generator._create_digest_mapping(events_list, "digest_123")
        
        mapping_file = generator.output_dir / "digest_mapping.json"
        assert mapping_file.exists()
        
        with open(mapping_file) as f:
            mapping = json.load(f)
        
        assert mapping['digest_id'] == "digest_123"
        assert len(mapping['events']) == 5
        assert mapping['events'][0]['display_number'] == 1


class TestDigestTracker:
    """Test cases for digest tracking."""
    
    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with test file."""
        tracker = DigestTracker()
        tracker.tracking_file = tmp_path / "digest_tracking.json"
        return tracker
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events with IDs."""
        events = []
        for i in range(1, 4):
            event = EventModel(
                name=f"Event {i}",
                date=datetime.now(),
                location="NYC",
                source_url=f"https://example.com/{i}"
            )
            event.event_id = f"event_{i}"
            events.append(event)
        return events
    
    def test_filter_new_events(self, tracker, sample_events):
        """Test filtering out already sent events."""
        # Mark first event as sent
        tracker._save_tracking_data({
            'sent_events': {'event_1': '2025-07-15T10:00:00'}
        })
        
        collection = EventCollection()
        for event in sample_events:
            collection.add(event)
        
        new_events = tracker.filter_new_events(collection)
        
        assert len(new_events) == 2
        assert new_events[0].event_id == "event_2"
        assert new_events[1].event_id == "event_3"
    
    def test_mark_events_sent(self, tracker):
        """Test marking events as sent."""
        event_ids = ['event_1', 'event_2', 'event_3']
        sent_time = datetime.now()
        
        tracker.mark_events_sent(event_ids, sent_time)
        
        # Check tracking file
        data = tracker._load_tracking_data()
        assert len(data['sent_events']) == 3
        assert 'event_1' in data['sent_events']
        assert 'event_2' in data['sent_events']
        assert 'event_3' in data['sent_events']
    
    def test_get_last_digest_time(self, tracker):
        """Test getting last digest time."""
        # No digest sent yet
        assert tracker.get_last_digest_time() is None
        
        # Mark some events as sent
        tracker.mark_events_sent(['event_1'], datetime.now())
        
        last_time = tracker.get_last_digest_time()
        assert last_time is not None
        assert isinstance(last_time, datetime)
    
    def test_cleanup_old_events(self, tracker):
        """Test cleaning up old sent events."""
        # Add events with different ages
        now = datetime.now()
        old_time = now - timedelta(days=40)
        recent_time = now - timedelta(days=5)
        
        tracker._save_tracking_data({
            'sent_events': {
                'old_event': old_time.isoformat(),
                'recent_event': recent_time.isoformat()
            }
        })
        
        tracker._cleanup_old_events()
        
        data = tracker._load_tracking_data()
        assert 'old_event' not in data['sent_events']
        assert 'recent_event' in data['sent_events']


class TestDigestIntegration:
    """Integration tests for digest system."""
    
    def test_full_digest_flow(self, tmp_path):
        """Test complete digest generation flow."""
        # Setup
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create simple templates
        html_template = template_dir / "digest_template.html"
        html_template.write_text("""
        <html>
        <body>
            <h1>{{event_count}} NYC Events</h1>
            {% for event in events %}
            <div>{{event.display_number}}. {{event.name}} - {{event.date_formatted}}</div>
            {% endfor %}
        </body>
        </html>
        """)
        
        text_template = template_dir / "digest_template.txt"  
        text_template.write_text("""
{{event_count}} NYC Events
{% for event in events %}
{{event.display_number}}. {{event.name}} - {{event.date_formatted}}
{% endfor %}
        """)
        
        # Create events
        collection = EventCollection()
        for i in range(1, 4):
            event = EventModel(
                name=f"Event {i}",
                date=datetime.now() + timedelta(days=i),
                location="NYC",
                source_url=f"https://example.com/{i}"
            )
            collection.add(event)
        
        # Generate digest
        generator = DigestGenerator(template_dir=str(template_dir))
        generator.output_dir = tmp_path / "digests"
        
        digest = generator.generate_digest(collection)
        
        assert digest['event_count'] == 3
        assert "3 NYC Events" in digest['html_body']
        
        # Save digest
        saved_files = generator.save_digest(digest)
        assert Path(saved_files['html']).exists()
        
        # Test tracking
        tracker = DigestTracker()
        tracker.tracking_file = tmp_path / "tracking.json"
        
        # Filter new events (all should be new)
        new_events = tracker.filter_new_events(collection)
        assert len(new_events) == 3
        
        # Mark as sent
        event_ids = [e.event_id for e in new_events]
        tracker.mark_events_sent(event_ids, datetime.now())
        
        # Filter again (none should be new)
        new_events2 = tracker.filter_new_events(collection)
        assert len(new_events2) == 0
    
    def test_digest_with_no_events(self, tmp_path):
        """Test handling empty event collection."""
        generator = DigestGenerator()
        collection = EventCollection()
        
        # Should handle empty collection gracefully
        digest = generator.generate_digest(collection)
        
        assert digest['event_count'] == 0
        assert digest['events'] == []