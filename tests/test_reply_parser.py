"""
Tests for email reply parser.
"""

import pytest
from datetime import datetime

from email_service.reply_parser import ReplyParser, ReplyProcessor
from data_store import EventModel, EventCollection


class TestReplyParser:
    """Test cases for reply parser."""
    
    @pytest.fixture
    def parser(self):
        """Create a ReplyParser instance."""
        return ReplyParser()
    
    def test_parse_comma_separated(self, parser):
        """Test parsing comma-separated numbers."""
        test_cases = [
            ("1, 3, 5", [1, 3, 5]),
            ("1,3,5", [1, 3, 5]),
            ("1, 3 and 5", [1, 3, 5]),
            ("I'm interested in events 1, 2, and 4", [1, 2, 4]),
            ("Please select 2,5,7 for me", [2, 5, 7]),
        ]
        
        for reply_body, expected in test_cases:
            result = parser.parse_reply(reply_body)
            assert result == expected, f"Failed for: {reply_body}"
    
    def test_parse_numbers_on_lines(self, parser):
        """Test parsing numbers on separate lines."""
        reply_body = """
        Here are my selections:
        1
        3
        5
        
        Thanks!
        """
        
        result = parser.parse_reply(reply_body)
        assert result == [1, 3, 5]
    
    def test_parse_numbered_list(self, parser):
        """Test parsing numbered list format."""
        reply_body = """
        My choices:
        1.
        3.
        7)
        """
        
        result = parser.parse_reply(reply_body)
        assert result == [1, 3, 7]
    
    def test_parse_with_context(self, parser):
        """Test parsing numbers with context words."""
        test_cases = [
            ("I want event 3", [3]),
            ("Interested in #5 and #8", [5, 8]),
            ("Please select number 2", [2]),
            ("The 3rd event looks good", [3]),
        ]
        
        for reply_body, expected in test_cases:
            result = parser.parse_reply(reply_body)
            assert result == expected, f"Failed for: {reply_body}"
    
    def test_parse_with_quotes(self, parser):
        """Test parsing replies with quoted text."""
        reply_body = """
        1, 4, 6
        
        > On July 15, 2024, you wrote:
        > Here are the events...
        > 1. Event One
        > 2. Event Two
        """
        
        result = parser.parse_reply(reply_body)
        assert result == [1, 4, 6]
    
    def test_parse_no_selections(self, parser):
        """Test parsing replies with no selections."""
        test_cases = [
            "Thanks for the email!",
            "I'll let you know later",
            "None of these work for me",
            "",
        ]
        
        for reply_body in test_cases:
            result = parser.parse_reply(reply_body)
            assert result == []
    
    def test_parse_out_of_range(self, parser):
        """Test filtering out unreasonable numbers."""
        reply_body = "I want events 2, 99, 150, and 5"
        
        result = parser.parse_reply(reply_body)
        assert result == [2, 5]  # 99 and 150 filtered out
    
    def test_parse_duplicates(self, parser):
        """Test handling duplicate selections."""
        reply_body = "1, 3, 1, 5, 3"
        
        result = parser.parse_reply(reply_body)
        assert result == [1, 3, 5]  # Duplicates removed and sorted


class TestReplyProcessor:
    """Test cases for reply processor."""
    
    @pytest.fixture
    def sample_reply(self):
        """Create a sample reply."""
        return {
            'from': 'photographer@example.com',
            'subject': 'Re: NYC Event Leads',
            'date': 'Mon, 15 Jul 2024 10:30:00 -0400',
            'body': 'Please select events 1, 3, and 5 for me. Thanks!'
        }
    
    def test_process_reply(self, sample_reply, tmp_path, monkeypatch):
        """Test processing a reply."""
        # Mock the data directory
        monkeypatch.setattr('email_service.reply_parser.Path', lambda x: tmp_path / x)
        
        processor = ReplyProcessor()
        
        # Create mock events
        events = EventCollection()
        for i in range(1, 6):
            events.add(EventModel(
                name=f"Event {i}",
                date=datetime.now(),
                location="NYC",
                source_url=f"http://example.com/{i}"
            ))
        
        # Mock getting selected events
        def mock_get_selected(nums, date=None):
            selected = EventCollection()
            for num in nums:
                if num <= len(events):
                    selected.add(events[num-1])
            return selected
            
        processor.parser.get_selected_events = mock_get_selected
        
        # Process the reply
        result = processor.process_reply(sample_reply)
        
        assert result is not None
        assert len(result) == 3
        assert result[0].name == "Event 1"
        assert result[1].name == "Event 3"
        assert result[2].name == "Event 5"