"""
Google Sheets storage handler for event data.
"""

import os
from typing import List, Dict, Optional, Union
from datetime import datetime
from pathlib import Path
import json

import gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from loguru import logger

from .models import EventModel, EventCollection


class GoogleSheetsStorage:
    """Store and retrieve events from Google Sheets."""
    
    # Google Sheets API scope
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Column headers for the sheet
    HEADERS = [
        'Event ID',
        'Name',
        'Date',
        'Location',
        'Source',
        'Source URL',
        'Contact Email',
        'Description',
        'Scraped At',
        'Status',
        'Selected',
        'Outreach Sent'
    ]
    
    def __init__(self, spreadsheet_id: Optional[str] = None, 
                 credentials_file: Optional[str] = None,
                 use_oauth: bool = False):
        """
        Initialize Google Sheets storage.
        
        Args:
            spreadsheet_id: ID of the Google Sheet to use
            credentials_file: Path to service account credentials JSON
            use_oauth: Use OAuth2 credentials instead of service account
        """
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')
        self.credentials_file = credentials_file or os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'sheets_credentials.json')
        self.use_oauth = use_oauth
        
        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID must be provided or set in GOOGLE_SHEETS_ID environment variable")
        
        self.client = self._authenticate()
        self.spreadsheet = None
        self.worksheet = None
        self._initialize_sheet()
    
    def _authenticate(self) -> gspread.Client:
        """Authenticate with Google Sheets API."""
        try:
            if self.use_oauth:
                # Use OAuth2 credentials (same as Gmail)
                return self._authenticate_oauth()
            else:
                # Use service account credentials
                return self._authenticate_service_account()
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    def _authenticate_service_account(self) -> gspread.Client:
        """Authenticate using service account credentials."""
        if not Path(self.credentials_file).exists():
            raise FileNotFoundError(
                f"Service account credentials not found: {self.credentials_file}\n"
                "Please download service account credentials from Google Cloud Console."
            )
        
        creds = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=self.SCOPES
        )
        
        return gspread.authorize(creds)
    
    def _authenticate_oauth(self) -> gspread.Client:
        """Authenticate using OAuth2 credentials."""
        # Try to use existing Gmail credentials
        token_file = "token.json"
        
        if not Path(token_file).exists():
            raise FileNotFoundError(
                "OAuth token not found. Please run setup_gmail.py first."
            )
        
        import pickle
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
        
        # Add spreadsheets scope if not present
        if self.SCOPES[0] not in creds._scopes:
            logger.warning("Spreadsheet scope not in credentials. May need re-authentication.")
        
        return gspread.authorize(creds)
    
    def _initialize_sheet(self):
        """Initialize the spreadsheet and worksheet."""
        try:
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Try to get existing worksheet or create new one
            try:
                self.worksheet = self.spreadsheet.worksheet("Events")
            except gspread.WorksheetNotFound:
                self.worksheet = self.spreadsheet.add_worksheet(
                    title="Events",
                    rows=1000,
                    cols=len(self.HEADERS)
                )
                # Add headers
                self.worksheet.update('A1:L1', [self.HEADERS])
                self.worksheet.format('A1:L1', {'textFormat': {'bold': True}})
                
            logger.info(f"Connected to Google Sheet: {self.spreadsheet.title}")
            
        except Exception as e:
            logger.error(f"Failed to initialize sheet: {e}")
            raise
    
    def save(self, events: EventCollection) -> str:
        """
        Save events to Google Sheets.
        
        Args:
            events: Collection of events to save
            
        Returns:
            URL of the Google Sheet
        """
        try:
            # Get existing event IDs to avoid duplicates
            existing_ids = self._get_existing_event_ids()
            
            # Prepare rows for new events
            new_rows = []
            for event in events:
                if event.event_id not in existing_ids:
                    row = self._event_to_row(event)
                    new_rows.append(row)
            
            if new_rows:
                # Find the next empty row
                next_row = len(self.worksheet.get_all_values()) + 1
                
                # Batch update for efficiency
                cell_range = f'A{next_row}:L{next_row + len(new_rows) - 1}'
                self.worksheet.update(cell_range, new_rows)
                
                logger.info(f"Added {len(new_rows)} new events to Google Sheet")
            else:
                logger.info("No new events to add to Google Sheet")
            
            return self.spreadsheet.url
            
        except Exception as e:
            logger.error(f"Failed to save to Google Sheets: {e}")
            raise
    
    def load(self) -> EventCollection:
        """
        Load all events from Google Sheets.
        
        Returns:
            Collection of events
        """
        try:
            # Get all records
            records = self.worksheet.get_all_records()
            
            collection = EventCollection()
            for record in records:
                try:
                    event = self._row_to_event(record)
                    if event:
                        collection.add(event)
                except Exception as e:
                    logger.warning(f"Failed to parse row: {record}. Error: {e}")
            
            logger.info(f"Loaded {len(collection)} events from Google Sheet")
            return collection
            
        except Exception as e:
            logger.error(f"Failed to load from Google Sheets: {e}")
            return EventCollection()
    
    def update_event_status(self, event_id: str, status: str):
        """Update the status of a specific event."""
        try:
            # Find the row with this event ID
            event_ids = self.worksheet.col_values(1)  # Event ID is column 1
            
            try:
                row_index = event_ids.index(event_id) + 1  # 1-based index
                self.worksheet.update_cell(row_index, 10, status)  # Status is column 10
                logger.info(f"Updated status for event {event_id} to {status}")
            except ValueError:
                logger.warning(f"Event {event_id} not found in sheet")
                
        except Exception as e:
            logger.error(f"Failed to update event status: {e}")
    
    def mark_events_selected(self, event_ids: List[str]):
        """Mark events as selected by photographer."""
        try:
            # Get all event IDs
            all_event_ids = self.worksheet.col_values(1)
            
            # Batch update for efficiency
            updates = []
            for event_id in event_ids:
                try:
                    row_index = all_event_ids.index(event_id) + 1
                    updates.append({
                        'range': f'K{row_index}',  # Selected is column 11
                        'values': [['Yes']]
                    })
                except ValueError:
                    logger.warning(f"Event {event_id} not found in sheet")
            
            if updates:
                self.worksheet.batch_update(updates)
                logger.info(f"Marked {len(updates)} events as selected")
                
        except Exception as e:
            logger.error(f"Failed to mark events as selected: {e}")
    
    def mark_outreach_sent(self, event_ids: List[str]):
        """Mark events as having outreach sent."""
        try:
            # Get all event IDs
            all_event_ids = self.worksheet.col_values(1)
            
            # Batch update
            updates = []
            for event_id in event_ids:
                try:
                    row_index = all_event_ids.index(event_id) + 1
                    updates.append({
                        'range': f'L{row_index}',  # Outreach Sent is column 12
                        'values': [[datetime.now().isoformat()]]
                    })
                except ValueError:
                    logger.warning(f"Event {event_id} not found in sheet")
            
            if updates:
                self.worksheet.batch_update(updates)
                logger.info(f"Marked {len(updates)} events as outreach sent")
                
        except Exception as e:
            logger.error(f"Failed to mark outreach sent: {e}")
    
    def get_selected_events(self) -> EventCollection:
        """Get events marked as selected."""
        try:
            records = self.worksheet.get_all_records()
            
            collection = EventCollection()
            for record in records:
                if record.get('Selected') == 'Yes' and not record.get('Outreach Sent'):
                    event = self._row_to_event(record)
                    if event:
                        collection.add(event)
            
            return collection
            
        except Exception as e:
            logger.error(f"Failed to get selected events: {e}")
            return EventCollection()
    
    def _event_to_row(self, event: EventModel) -> List[Union[str, None]]:
        """Convert event to spreadsheet row."""
        return [
            event.event_id,
            event.name,
            event.date.isoformat() if event.date else '',
            event.location or '',
            event.source or '',
            event.source_url or '',
            event.contact_email or '',
            event.description or '',
            event.scraped_at.isoformat() if event.scraped_at else '',
            'New',  # Status
            '',     # Selected
            ''      # Outreach Sent
        ]
    
    def _row_to_event(self, record: Dict) -> Optional[EventModel]:
        """Convert spreadsheet row to event."""
        try:
            # Parse date
            date_str = record.get('Date', '')
            if date_str:
                date = datetime.fromisoformat(date_str)
            else:
                date = datetime.now()
            
            event = EventModel(
                name=record.get('Name', ''),
                date=date,
                location=record.get('Location', ''),
                source_url=record.get('Source URL', ''),
                contact_email=record.get('Contact Email') or None,
                description=record.get('Description') or None,
                source=record.get('Source') or None
            )
            
            # Preserve original event ID
            event.event_id = record.get('Event ID', event.event_id)
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to parse event record: {e}")
            return None
    
    def _get_existing_event_ids(self) -> set:
        """Get set of existing event IDs in the sheet."""
        try:
            event_ids = self.worksheet.col_values(1)[1:]  # Skip header
            return set(event_ids)
        except Exception:
            return set()
    
    def create_summary_sheet(self):
        """Create a summary sheet with statistics."""
        try:
            # Try to get existing summary sheet or create new one
            try:
                summary = self.spreadsheet.worksheet("Summary")
            except gspread.WorksheetNotFound:
                summary = self.spreadsheet.add_worksheet(
                    title="Summary",
                    rows=20,
                    cols=5
                )
            
            # Calculate statistics
            all_records = self.worksheet.get_all_records()
            
            total_events = len(all_records)
            selected_events = sum(1 for r in all_records if r.get('Selected') == 'Yes')
            outreach_sent = sum(1 for r in all_records if r.get('Outreach Sent'))
            
            # Count by source
            sources = {}
            for record in all_records:
                source = record.get('Source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            
            # Update summary
            summary_data = [
                ['NYC Event Automation Summary', ''],
                ['Last Updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['', ''],
                ['Total Events', total_events],
                ['Selected Events', selected_events],
                ['Outreach Sent', outreach_sent],
                ['', ''],
                ['Events by Source', '']
            ]
            
            for source, count in sources.items():
                summary_data.append([source, count])
            
            summary.clear()
            summary.update('A1:B' + str(len(summary_data)), summary_data)
            summary.format('A1:B1', {'textFormat': {'bold': True, 'fontSize': 14}})
            summary.format('A8:A8', {'textFormat': {'bold': True}})
            
            logger.info("Updated summary sheet")
            
        except Exception as e:
            logger.error(f"Failed to create summary sheet: {e}")


class GoogleSheetsManager:
    """Manager for Google Sheets operations."""
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        """Initialize the manager."""
        self.storage = GoogleSheetsStorage(spreadsheet_id=spreadsheet_id)
    
    def sync_events(self, local_events: EventCollection) -> Dict[str, int]:
        """
        Sync local events with Google Sheets.
        
        Args:
            local_events: Local event collection
            
        Returns:
            Dictionary with sync statistics
        """
        # Save new events to sheet
        self.storage.save(local_events)
        
        # Get current sheet data
        sheet_events = self.storage.load()
        
        stats = {
            'local_events': len(local_events),
            'sheet_events': len(sheet_events),
            'new_events': 0
        }
        
        # Count new events
        sheet_ids = {e.event_id for e in sheet_events}
        for event in local_events:
            if event.event_id not in sheet_ids:
                stats['new_events'] += 1
        
        # Update summary
        self.storage.create_summary_sheet()
        
        return stats
    
    def export_to_sheets(self, events: EventCollection) -> str:
        """Export events to Google Sheets and return the URL."""
        return self.storage.save(events)