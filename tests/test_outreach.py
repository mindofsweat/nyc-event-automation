"""
Unit tests for outreach email generation and sending.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import json

from email_service.outreach import OutreachGenerator, OutreachSender, load_selected_events
from data_store.models import EventModel


class TestOutreachGenerator:
    """Test cases for outreach email generation."""
    
    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator with test templates."""
        # Create test templates
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        html_template = template_dir / "outreach_template.html"
        html_template.write_text("""
        <html>
        <body>
            <p>Hi {{organizer_name}},</p>
            <p>Event: {{event_name}}</p>
            <p>Date: {{event_date}}</p>
            <p>Location: {{event_location}}</p>
        </body>
        </html>
        """)
        
        text_template = template_dir / "outreach_template.txt"
        text_template.write_text("""
Hi {{organizer_name}},
Event: {{event_name}}
Date: {{event_date}}
Location: {{event_location}}
        """)
        
        return OutreachGenerator(template_dir=str(template_dir))
    
    @pytest.fixture
    def sample_event(self):
        """Create sample event."""
        return EventModel(
            name="Summer Concert Series",
            date=datetime(2025, 7, 20, 18, 0),
            location="Central Park, NYC",
            source_url="https://example.com/event",
            contact_email="organizer@example.com",
            description="Join us for live music in the park"
        )
    
    def test_generate_outreach_email(self, generator, sample_event):
        """Test generating outreach email."""
        result = generator.generate_outreach_email(
            sample_event,
            organizer_name="Event Team"
        )
        
        assert result is not None
        assert result['to'] == "organizer@example.com"
        assert "Summer Concert Series" in result['subject']
        assert "Hi Event Team" in result['html_body']
        assert "July 20, 2025" in result['text_body']
        assert "Central Park, NYC" in result['html_body']
    
    def test_generate_without_organizer_name(self, generator, sample_event):
        """Test generating email without organizer name."""
        result = generator.generate_outreach_email(sample_event)
        
        assert "Hi there" in result['text_body']
    
    def test_extract_email_from_description(self, generator):
        """Test extracting email from event description."""
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com",
            description="Contact us at info@testevent.com for details"
        )
        
        email = generator._extract_email_from_event(event)
        assert email == "info@testevent.com"
    
    def test_extract_email_from_url(self, generator):
        """Test extracting email from URL domain."""
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://www.eventsite.com/contact",
            description="No email here"
        )
        
        email = generator._extract_email_from_event(event)
        assert email == "info@eventsite.com"
    
    def test_no_email_found(self, generator):
        """Test when no email can be found."""
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com/event123",
            description="No contact information"
        )
        
        result = generator.generate_outreach_email(event)
        assert result is None
    
    def test_extract_organizer_name(self, generator):
        """Test extracting organizer name from event."""
        event = EventModel(
            name="Concert presented by Live Nation",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com"
        )
        
        name = generator._extract_organizer_name(event)
        assert name == "Live Nation"


class TestOutreachSender:
    """Test cases for outreach email sending."""
    
    @pytest.fixture
    def sender(self):
        """Create sender with mocked email client."""
        mock_email_sender = Mock()
        return OutreachSender(email_sender=mock_email_sender)
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events with contact info."""
        return [
            EventModel(
                name=f"Event {i}",
                date=datetime(2025, 7, 20 + i),
                location="NYC",
                source_url=f"https://example{i}.com",
                contact_email=f"organizer{i}@example.com",
                event_id=f"event_{i}"
            )
            for i in range(1, 4)
        ]
    
    @patch('email_service.outreach.OutreachGenerator.generate_outreach_email')
    def test_send_outreach_for_events(self, mock_generate, sender, sample_events):
        """Test sending outreach for multiple events."""
        # Mock email generation
        def generate_email(event, **kwargs):
            return {
                'to': event.contact_email,
                'subject': f"Photography for {event.name}",
                'html_body': "<html>...</html>",
                'text_body': "...",
                'event_name': event.name
            }
        
        mock_generate.side_effect = generate_email
        sender.email_sender.send_outreach_email.return_value = True
        
        # Send outreach
        results = sender.send_outreach_for_events(sample_events)
        
        assert len(results['sent']) == 3
        assert len(results['failed']) == 0
        assert sender.email_sender.send_outreach_email.call_count == 3
    
    def test_send_outreach_test_mode(self, sender, sample_events):
        """Test outreach in test mode."""
        results = sender.send_outreach_for_events(sample_events, test_mode=True)
        
        # In test mode, emails are not actually sent
        sender.email_sender.send_outreach_email.assert_not_called()
    
    @patch('email_service.outreach.OutreachGenerator.generate_outreach_email')
    def test_skip_already_sent(self, mock_generate, sender, sample_events, tmp_path):
        """Test skipping already sent events."""
        # Create sent history
        sent_log = tmp_path / "outreach_sent.json"
        sent_log.write_text(json.dumps({
            'sent_events': ['event_1'],
            'details': []
        }))
        
        sender.sent_log_file = sent_log
        
        # Only event_1 should be skipped
        mock_generate.return_value = {
            'to': 'test@example.com',
            'subject': 'Test',
            'html_body': '<html></html>',
            'text_body': 'Test'
        }
        sender.email_sender.send_outreach_email.return_value = True
        
        results = sender.send_outreach_for_events(sample_events)
        
        # Should only send 2 emails (event_2 and event_3)
        assert len(results['sent']) == 2
        assert 'event_1' not in results['sent']
    
    def test_handle_send_failure(self, sender, sample_events):
        """Test handling email send failures."""
        sender.email_sender.send_outreach_email.return_value = False
        
        with patch('email_service.outreach.OutreachGenerator.generate_outreach_email') as mock_gen:
            mock_gen.return_value = {
                'to': 'test@example.com',
                'subject': 'Test',
                'html_body': '<html></html>',
                'text_body': 'Test'
            }
            
            results = sender.send_outreach_for_events(sample_events)
            
            assert len(results['sent']) == 0
            assert len(results['failed']) == 3
    
    def test_record_sent(self, sender, tmp_path):
        """Test recording sent emails."""
        sender.sent_log_file = tmp_path / "outreach_sent.json"
        
        sender._record_sent("event_123", "test@example.com")
        
        # Check file was created
        assert sender.sent_log_file.exists()
        
        # Check content
        with open(sender.sent_log_file) as f:
            data = json.load(f)
        
        assert 'event_123' in data['sent_events']
        assert len(data['details']) == 1
        assert data['details'][0]['event_id'] == 'event_123'
        assert data['details'][0]['recipient'] == 'test@example.com'


class TestLoadSelectedEvents:
    """Test cases for loading selected events."""
    
    @patch('email_service.outreach.Path')
    @patch('email_service.outreach.StorageManager')
    def test_load_selected_events(self, mock_storage, mock_path, tmp_path):
        """Test loading selected events from file."""
        # Mock selections file
        selections_data = [
            {
                'date': '2025-07-15T14:00:00',
                'from': 'photographer@example.com',
                'event_ids': ['event_1', 'event_2'],
                'status': 'pending_outreach'
            }
        ]
        
        selections_file = tmp_path / "selections.json"
        selections_file.write_text(json.dumps(selections_data))
        
        mock_path.return_value = selections_file
        
        # Mock events data
        events = [
            EventModel(
                name="Event 1",
                date=datetime.now(),
                location="NYC",
                source_url="https://example.com",
                event_id="event_1"
            ),
            EventModel(
                name="Event 2",
                date=datetime.now(),
                location="NYC",
                source_url="https://example.com",
                event_id="event_2"
            )
        ]
        
        mock_storage.return_value.load_latest.return_value = events
        
        # Load selected events
        result = load_selected_events()
        
        assert len(result) == 2
        assert result[0].event_id == "event_1"
        assert result[1].event_id == "event_2"
    
    @patch('email_service.outreach.Path')
    def test_load_selected_events_no_file(self, mock_path):
        """Test loading when no selections file exists."""
        mock_path.return_value.exists.return_value = False
        
        result = load_selected_events()
        
        assert result == []


class TestOutreachIntegration:
    """Integration tests for outreach system."""
    
    def test_full_outreach_flow(self, tmp_path):
        """Test complete outreach flow."""
        # Create templates
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        html_template = template_dir / "outreach_template.html"
        html_template.write_text("<html>Hi {{organizer_name}}</html>")
        
        text_template = template_dir / "outreach_template.txt"
        text_template.write_text("Hi {{organizer_name}}")
        
        # Create event
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com",
            contact_email="test@example.com"
        )
        
        # Generate email
        generator = OutreachGenerator(template_dir=str(template_dir))
        email_data = generator.generate_outreach_email(event)
        
        assert email_data is not None
        assert email_data['to'] == "test@example.com"
        assert "Hi there" in email_data['text_body']
        
        # Test sending (mocked)
        mock_email_sender = Mock()
        mock_email_sender.send_outreach_email.return_value = True
        
        sender = OutreachSender(email_sender=mock_email_sender)
        results = sender.send_outreach_for_events([event])
        
        assert len(results['sent']) == 1
        assert len(results['failed']) == 0