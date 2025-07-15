"""
Tests for data store models and storage handlers.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json
import csv

from data_store import EventModel, EventCollection, JSONStorage, CSVStorage, StorageManager


class TestEventModel:
    """Test cases for EventModel."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = EventModel(
            name="Test Event",
            date=datetime(2024, 7, 20, 19, 0),
            location="NYC",
            source_url="https://example.com"
        )
        
        assert event.name == "Test Event"
        assert event.location == "NYC"
        assert event.event_id is not None
        assert len(event.event_id) == 12
    
    def test_event_id_generation(self):
        """Test that similar events get different IDs."""
        event1 = EventModel(
            name="Test Event",
            date=datetime(2024, 7, 20),
            location="NYC",
            source_url="https://example1.com"
        )
        
        event2 = EventModel(
            name="Test Event",
            date=datetime(2024, 7, 21),  # Different date
            location="NYC",
            source_url="https://example2.com"
        )
        
        assert event1.event_id != event2.event_id
    
    def test_text_cleaning(self):
        """Test text cleaning functionality."""
        event = EventModel(
            name="  Test   Event  \n\n",
            date=datetime.now(),
            location="NYC\t\t",
            source_url="https://example.com",
            description="Multiple   spaces   here"
        )
        
        assert event.name == "Test Event"
        assert event.location == "NYC"
        assert event.description == "Multiple spaces here"
    
    def test_email_extraction(self):
        """Test email extraction from description."""
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com",
            description="Contact us at test@example.com for more info"
        )
        
        assert event.contact_email == "test@example.com"
    
    def test_duplicate_detection(self):
        """Test duplicate detection."""
        event1 = EventModel(
            name="NYC Food Festival",
            date=datetime(2024, 7, 20),
            location="Brooklyn",
            source_url="https://example1.com"
        )
        
        event2 = EventModel(
            name="NYC Food Fest",  # Similar name
            date=datetime(2024, 7, 20),  # Same date
            location="Brooklyn",
            source_url="https://example2.com"
        )
        
        assert event1.is_duplicate_of(event2, fuzzy=True)


class TestEventCollection:
    """Test cases for EventCollection."""
    
    def test_add_event(self):
        """Test adding events to collection."""
        collection = EventCollection()
        
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com"
        )
        
        assert collection.add(event) is True
        assert len(collection) == 1
        assert collection.get_by_id(event.event_id) == event
    
    def test_duplicate_prevention(self):
        """Test that duplicates are prevented."""
        collection = EventCollection()
        
        event1 = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com"
        )
        
        event2 = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com"
        )
        
        collection.add(event1)
        assert collection.add(event2) is False
        assert len(collection) == 1
    
    def test_get_by_date_range(self):
        """Test filtering by date range."""
        collection = EventCollection()
        
        today = datetime.now()
        
        events = [
            EventModel("Past Event", today - timedelta(days=1), "NYC", "url1"),
            EventModel("Today Event", today, "NYC", "url2"),
            EventModel("Future Event", today + timedelta(days=1), "NYC", "url3"),
        ]
        
        for event in events:
            collection.add(event)
        
        # Get events for today only
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today.replace(hour=23, minute=59, second=59)
        
        today_events = collection.get_by_date_range(start, end)
        assert len(today_events) == 1
        assert today_events[0].name == "Today Event"


class TestStorage:
    """Test cases for storage handlers."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_collection(self):
        """Create a sample event collection."""
        collection = EventCollection()
        
        events = [
            EventModel("Event 1", datetime(2024, 7, 20), "NYC", "url1", source="Test"),
            EventModel("Event 2", datetime(2024, 7, 21), "NYC", "url2", source="Test"),
            EventModel("Event 3", datetime(2024, 7, 22), "NYC", "url3", source="Test"),
        ]
        
        for event in events:
            collection.add(event)
            
        return collection
    
    def test_json_storage(self, temp_dir, sample_collection):
        """Test JSON storage save and load."""
        storage = JSONStorage()
        filepath = temp_dir / "test_events.json"
        
        # Save
        storage.save(sample_collection, filepath)
        assert filepath.exists()
        
        # Load
        loaded_collection = storage.load(filepath)
        assert len(loaded_collection) == len(sample_collection)
        
        # Verify data integrity
        for i, event in enumerate(loaded_collection):
            original = sample_collection[i]
            assert event.name == original.name
            assert event.date.date() == original.date.date()
            assert event.location == original.location
    
    def test_csv_storage(self, temp_dir, sample_collection):
        """Test CSV storage save and load."""
        storage = CSVStorage()
        filepath = temp_dir / "test_events.csv"
        
        # Save
        storage.save(sample_collection, filepath)
        assert filepath.exists()
        
        # Load
        loaded_collection = storage.load(filepath)
        assert len(loaded_collection) == len(sample_collection)
        
        # Verify CSV structure
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == EventModel.csv_headers()
    
    def test_storage_manager(self, temp_dir, sample_collection):
        """Test StorageManager functionality."""
        manager = StorageManager(data_dir=temp_dir)
        
        # Save in both formats
        saved_files = manager.save_events(sample_collection, format="both")
        
        assert "json" in saved_files
        assert "csv" in saved_files
        assert saved_files["json"].exists()
        assert saved_files["csv"].exists()
        
        # Load latest
        loaded = manager.load_latest(format="json")
        assert len(loaded) == len(sample_collection)