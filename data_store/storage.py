"""
Storage handlers for event data in JSON and CSV formats.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Union
from abc import ABC, abstractmethod
from loguru import logger

from .models import EventModel, EventCollection


class EventStorage(ABC):
    """Abstract base class for event storage."""
    
    @abstractmethod
    def save(self, events: Union[EventCollection, List[EventModel]], filepath: Path) -> None:
        """Save events to storage."""
        pass
    
    @abstractmethod
    def load(self, filepath: Path) -> EventCollection:
        """Load events from storage."""
        pass
    
    def ensure_directory(self, filepath: Path) -> None:
        """Ensure the directory for the file exists."""
        filepath.parent.mkdir(parents=True, exist_ok=True)


class JSONStorage(EventStorage):
    """JSON storage handler for events."""
    
    def save(self, events: Union[EventCollection, List[EventModel]], filepath: Path) -> None:
        """Save events to JSON file."""
        self.ensure_directory(filepath)
        
        # Convert to EventCollection if needed
        if isinstance(events, list):
            collection = EventCollection(events)
        else:
            collection = events
            
        # Save to JSON
        data = {
            'metadata': {
                'total_events': len(collection),
                'export_date': datetime.now().isoformat(),
                'sources': list(set(event.source for event in collection if event.source))
            },
            'events': collection.to_list()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"Saved {len(collection)} events to {filepath}")
    
    def load(self, filepath: Path) -> EventCollection:
        """Load events from JSON file."""
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return EventCollection()
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Handle both old format (list) and new format (with metadata)
        if isinstance(data, list):
            events_data = data
        else:
            events_data = data.get('events', [])
            
        events = []
        for event_data in events_data:
            try:
                event = EventModel.from_dict(event_data)
                events.append(event)
            except Exception as e:
                logger.error(f"Error loading event: {e}")
                
        collection = EventCollection(events)
        logger.info(f"Loaded {len(collection)} events from {filepath}")
        return collection
    
    def load_multiple(self, directory: Path, pattern: str = "events_*.json") -> EventCollection:
        """Load and merge events from multiple JSON files."""
        collection = EventCollection()
        
        for filepath in directory.glob(pattern):
            try:
                file_collection = self.load(filepath)
                added = collection.add_many(file_collection.events, check_duplicates=True)
                logger.info(f"Added {added} unique events from {filepath}")
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
                
        return collection


class CSVStorage(EventStorage):
    """CSV storage handler for events."""
    
    def save(self, events: Union[EventCollection, List[EventModel]], filepath: Path) -> None:
        """Save events to CSV file."""
        self.ensure_directory(filepath)
        
        # Convert to EventCollection if needed
        if isinstance(events, list):
            collection = EventCollection(events)
        else:
            collection = events
            
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow(EventModel.csv_headers())
            
            # Write events
            for event in collection:
                writer.writerow(event.to_csv_row())
                
        logger.info(f"Saved {len(collection)} events to {filepath}")
    
    def load(self, filepath: Path) -> EventCollection:
        """Load events from CSV file."""
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return EventCollection()
            
        events = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Convert CSV row to event dict format
                    event_data = {
                        'event_id': row.get('event_id'),
                        'name': row['name'],
                        'date': row['date'],
                        'location': row['location'],
                        'source_url': row['source_url'],
                        'contact_email': row.get('contact_email') or None,
                        'description': row.get('description') or None,
                        'source': row.get('source') or None,
                        'scraped_at': row.get('scraped_at', datetime.now().isoformat())
                    }
                    
                    event = EventModel.from_dict(event_data)
                    events.append(event)
                except Exception as e:
                    logger.error(f"Error loading event from CSV: {e}")
                    
        collection = EventCollection(events)
        logger.info(f"Loaded {len(collection)} events from {filepath}")
        return collection


class StorageManager:
    """Manager for handling multiple storage formats."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.json_storage = JSONStorage()
        self.csv_storage = CSVStorage()
        
    def save_events(self, events: Union[EventCollection, List[EventModel]], 
                   format: str = "both", timestamp: bool = True) -> dict:
        """Save events in specified format(s)."""
        if timestamp:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"events_{timestamp_str}"
        else:
            base_name = "events"
            
        saved_files = {}
        
        if format in ["json", "both"]:
            json_path = self.data_dir / f"{base_name}.json"
            self.json_storage.save(events, json_path)
            saved_files["json"] = json_path
            
        if format in ["csv", "both"]:
            csv_path = self.data_dir / f"{base_name}.csv"
            self.csv_storage.save(events, csv_path)
            saved_files["csv"] = csv_path
            
        return saved_files
    
    def load_latest(self, format: str = "json") -> EventCollection:
        """Load the most recent events file."""
        pattern = f"events_*.{format}"
        files = list(self.data_dir.glob(pattern))
        
        if not files:
            logger.warning(f"No {format} files found in {self.data_dir}")
            return EventCollection()
            
        # Sort by modification time
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        if format == "json":
            return self.json_storage.load(latest_file)
        else:
            return self.csv_storage.load(latest_file)
    
    def merge_all_events(self) -> EventCollection:
        """Load and merge all events from all JSON files."""
        collection = self.json_storage.load_multiple(self.data_dir)
        removed = collection.remove_duplicates()
        logger.info(f"Merged events: {len(collection)} unique events ({removed} duplicates removed)")
        return collection