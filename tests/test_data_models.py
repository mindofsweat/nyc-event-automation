"""
Unit tests for data models and storage.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import csv

from data_store.models import EventModel, EventCollection
from data_store.storage import JSONStorage, CSVStorage, StorageManager


class TestEventModel:
    """Test cases for EventModel."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = EventModel(
            name="Test Event",
            date=datetime(2025, 7, 20, 18, 0),
            location="NYC",
            source_url="https://example.com/event"
        )
        
        assert event.name == "Test Event"
        assert event.date.year == 2025
        assert event.location == "NYC"
        assert event.event_id is not None
    
    def test_event_id_generation(self):
        """Test unique ID generation."""
        event1 = EventModel(
            name="Same Event",
            date=datetime(2025, 7, 20),
            location="Same Location",
            source_url="https://example1.com"
        )
        
        event2 = EventModel(
            name="Same Event",
            date=datetime(2025, 7, 20),
            location="Same Location",
            source_url="https://example2.com"
        )
        
        # Same name, date, location = same ID
        assert event1.event_id == event2.event_id
        
        # Different details = different ID
        event3 = EventModel(
            name="Different Event",
            date=datetime(2025, 7, 20),
            location="Same Location",
            source_url="https://example3.com"
        )
        
        assert event3.event_id != event1.event_id
    
    def test_text_cleaning(self):
        """Test text field cleaning."""
        event = EventModel(
            name="  Test Event  \n\n",
            date=datetime.now(),
            location="  NYC  ",
            source_url="https://example.com",
            description="  Multiple   spaces  "
        )
        
        assert event.name == "Test Event"
        assert event.location == "NYC"
        assert event.description == "Multiple spaces"
    
    def test_email_extraction(self):
        """Test extracting email from description."""
        event = EventModel(
            name="Test Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com",
            description="Contact us at info@example.com for details"
        )
        
        assert event.contact_email == "info@example.com"
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        event = EventModel(
            name="Test Event",
            date=datetime(2025, 7, 20, 18, 0),
            location="NYC",
            source_url="https://example.com"
        )
        
        data = event.to_dict()
        
        assert data['name'] == "Test Event"
        assert data['date'] == "2025-07-20T18:00:00"
        assert data['location'] == "NYC"
        assert 'event_id' in data
    
    def test_is_duplicate(self):
        """Test duplicate detection."""
        event1 = EventModel(
            name="Test Event",
            date=datetime(2025, 7, 20),
            location="NYC",
            source_url="https://example.com"
        )
        
        event2 = EventModel(
            name="Test Event",
            date=datetime(2025, 7, 20),
            location="NYC",
            source_url="https://different.com"
        )
        
        assert event1.is_duplicate(event2)
        
        # Different name = not duplicate
        event3 = EventModel(
            name="Different Event",
            date=datetime(2025, 7, 20),
            location="NYC",
            source_url="https://example.com"
        )
        
        assert not event1.is_duplicate(event3)


class TestEventCollection:
    """Test cases for EventCollection."""
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events."""
        events = []
        for i in range(1, 6):
            event = EventModel(
                name=f"Event {i}",
                date=datetime.now() + timedelta(days=i),
                location=f"Location {i}",
                source_url=f"https://example.com/{i}"
            )
            events.append(event)
        return events
    
    def test_add_events(self, sample_events):
        """Test adding events to collection."""
        collection = EventCollection()
        
        for event in sample_events:
            collection.add(event)
        
        assert len(collection) == 5
        assert collection[0].name == "Event 1"
    
    def test_remove_duplicates(self):
        """Test removing duplicate events."""
        collection = EventCollection()
        
        # Add same event twice
        event = EventModel(
            name="Duplicate Event",
            date=datetime.now(),
            location="NYC",
            source_url="https://example.com"
        )
        
        collection.add(event)
        collection.add(event)
        
        assert len(collection) == 2
        
        removed = collection.remove_duplicates()
        
        assert removed == 1
        assert len(collection) == 1
    
    def test_get_by_source(self, sample_events):
        """Test filtering by source."""
        collection = EventCollection()
        
        for event in sample_events:
            event.source = "TestSource" if event.name in ["Event 1", "Event 3"] else "Other"
            collection.add(event)
        
        filtered = collection.get_by_source("TestSource")
        
        assert len(filtered) == 2
        assert all(e.source == "TestSource" for e in filtered)
    
    def test_get_upcoming(self):
        """Test getting upcoming events."""
        collection = EventCollection()
        
        # Add past and future events
        past_event = EventModel(
            name="Past Event",
            date=datetime.now() - timedelta(days=1),
            location="NYC",
            source_url="https://example.com"
        )
        
        future_event = EventModel(
            name="Future Event",
            date=datetime.now() + timedelta(days=1),
            location="NYC",
            source_url="https://example.com"
        )
        
        collection.add(past_event)
        collection.add(future_event)
        
        upcoming = collection.get_upcoming()
        
        assert len(upcoming) == 1
        assert upcoming[0].name == "Future Event"
    
    def test_get_date_range(self):
        """Test filtering by date range."""
        collection = EventCollection()
        
        base_date = datetime.now()
        
        for i in range(-2, 3):
            event = EventModel(
                name=f"Event {i}",
                date=base_date + timedelta(days=i),
                location="NYC",
                source_url=f"https://example.com/{i}"
            )
            collection.add(event)
        
        # Get events for tomorrow and day after
        start = base_date + timedelta(days=1)
        end = base_date + timedelta(days=2)
        
        filtered = collection.get_date_range(start, end)
        
        assert len(filtered) == 2
    
    def test_sort_by_date(self, sample_events):
        """Test sorting by date."""
        collection = EventCollection()
        
        # Add in reverse order
        for event in reversed(sample_events):
            collection.add(event)
        
        collection.sort_by_date()
        
        # Check events are in chronological order
        for i in range(len(collection) - 1):
            assert collection[i].date <= collection[i + 1].date


class TestStorageHandlers:
    """Test cases for storage handlers."""
    
    @pytest.fixture
    def sample_collection(self):
        """Create sample event collection."""
        collection = EventCollection()
        for i in range(1, 4):
            event = EventModel(
                name=f"Event {i}",
                date=datetime(2025, 7, 20 + i),
                location="NYC",
                source_url=f"https://example.com/{i}"
            )
            collection.add(event)
        return collection
    
    def test_json_storage(self, sample_collection, tmp_path):
        """Test JSON storage handler."""
        storage = JSONStorage()
        
        # Save
        filepath = storage.save(sample_collection, tmp_path)
        assert filepath.exists()
        assert filepath.suffix == '.json'
        
        # Load
        loaded = storage.load(filepath)
        assert len(loaded) == 3
        assert loaded[0].name == "Event 1"
        
        # Check JSON structure
        with open(filepath) as f:
            data = json.load(f)
        
        assert len(data) == 3
        assert data[0]['name'] == "Event 1"
    
    def test_csv_storage(self, sample_collection, tmp_path):
        """Test CSV storage handler."""
        storage = CSVStorage()
        
        # Save
        filepath = storage.save(sample_collection, tmp_path)
        assert filepath.exists()
        assert filepath.suffix == '.csv'
        
        # Load
        loaded = storage.load(filepath)
        assert len(loaded) == 3
        assert loaded[0].name == "Event 1"
        
        # Check CSV structure
        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]['name'] == "Event 1"
    
    def test_storage_manager(self, sample_collection, tmp_path):
        """Test storage manager."""
        manager = StorageManager(data_dir=tmp_path)
        
        # Save in both formats
        saved_files = manager.save_events(sample_collection, format="both")
        
        assert 'json' in saved_files
        assert 'csv' in saved_files
        assert Path(saved_files['json']).exists()
        assert Path(saved_files['csv']).exists()
        
        # Load latest
        loaded = manager.load_latest(format="json")
        assert len(loaded) == 3
        
        # Load specific file
        loaded2 = manager.load_events(Path(saved_files['csv']).name, format="csv")
        assert len(loaded2) == 3
    
    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent file."""
        storage = JSONStorage()
        
        result = storage.load(tmp_path / "nonexistent.json")
        assert isinstance(result, EventCollection)
        assert len(result) == 0
    
    def test_invalid_format(self, sample_collection, tmp_path):
        """Test handling invalid format."""
        manager = StorageManager(data_dir=tmp_path)
        
        with pytest.raises(ValueError):
            manager.save_events(sample_collection, format="invalid")


class TestDataIntegration:
    """Integration tests for data models and storage."""
    
    def test_full_data_flow(self, tmp_path):
        """Test complete data flow from creation to storage."""
        # Create events
        collection = EventCollection()
        
        event1 = EventModel(
            name="Concert in the Park",
            date=datetime(2025, 7, 25, 19, 0),
            location="Central Park",
            source_url="https://centralpark.com/concert",
            description="Free summer concert series. Contact: events@centralpark.com"
        )
        
        event2 = EventModel(
            name="Art Exhibition",
            date=datetime(2025, 7, 28, 14, 0),
            location="MoMA",
            source_url="https://moma.org/exhibition",
            source="MoMA"
        )
        
        collection.add(event1)
        collection.add(event2)
        
        # Test duplicate detection
        duplicate = EventModel(
            name="Concert in the Park",
            date=datetime(2025, 7, 25, 19, 0),
            location="Central Park",
            source_url="https://different-url.com"
        )
        
        collection.add(duplicate)
        removed = collection.remove_duplicates()
        assert removed == 1
        assert len(collection) == 2
        
        # Save to storage
        manager = StorageManager(data_dir=tmp_path)
        saved = manager.save_events(collection, format="both")
        
        # Load and verify
        loaded_json = manager.load_latest(format="json")
        loaded_csv = manager.load_latest(format="csv")
        
        assert len(loaded_json) == 2
        assert len(loaded_csv) == 2
        
        # Check data integrity
        assert loaded_json[0].name == "Concert in the Park"
        assert loaded_json[0].contact_email == "events@centralpark.com"
        assert loaded_csv[1].source == "MoMA"