#!/usr/bin/env python3
"""
NYC Event Lead Scraper & Outreach Automator
Main entry point for the application.
"""

import argparse
import sys
import json
import os
from datetime import datetime
from pathlib import Path

from loguru import logger
from scrapers import (
    EventbriteScraper,
    NYCForFreeScraper,
    AverageSocialiteScraper
)
from data_store import EventModel, EventCollection, StorageManager


# Configure logger
logger.add("logs/scraper_{time}.log", rotation="1 day", retention="7 days")


def scrape():
    """Run all scrapers and save event data."""
    logger.info("Starting scraping process")
    
    # Create event collection
    collection = EventCollection()
    storage_manager = StorageManager()
    
    # Run Eventbrite scraper
    try:
        logger.info("Running Eventbrite scraper...")
        eventbrite_scraper = EventbriteScraper(max_pages=3)
        eventbrite_events = eventbrite_scraper.scrape()
        
        # Convert to EventModel objects
        for event in eventbrite_events:
            event_model = EventModel(
                name=event.name,
                date=event.date,
                location=event.location,
                source_url=event.source_url,
                contact_email=event.contact_email,
                description=event.description,
                source=event.source
            )
            collection.add(event_model)
            
        logger.info(f"Eventbrite: Found {len(eventbrite_events)} events")
    except Exception as e:
        logger.error(f"Eventbrite scraper failed: {e}")
    
    # Run NYC For Free scraper
    try:
        logger.info("Running NYC For Free scraper...")
        nycforfree_scraper = NYCForFreeScraper()
        nycforfree_events = nycforfree_scraper.scrape()
        
        for event in nycforfree_events:
            event_model = EventModel(
                name=event.name,
                date=event.date,
                location=event.location,
                source_url=event.source_url,
                contact_email=event.contact_email,
                description=event.description,
                source=event.source
            )
            collection.add(event_model)
            
        logger.info(f"NYC For Free: Found {len(nycforfree_events)} events")
    except Exception as e:
        logger.error(f"NYC For Free scraper failed: {e}")
    
    # Run Average Socialite scraper
    try:
        logger.info("Running Average Socialite scraper...")
        averagesocialite_scraper = AverageSocialiteScraper(max_pages=3)
        averagesocialite_events = averagesocialite_scraper.scrape()
        
        for event in averagesocialite_events:
            event_model = EventModel(
                name=event.name,
                date=event.date,
                location=event.location,
                source_url=event.source_url,
                contact_email=event.contact_email,
                description=event.description,
                source=event.source
            )
            collection.add(event_model)
            
        logger.info(f"Average Socialite: Found {len(averagesocialite_events)} events")
    except Exception as e:
        logger.error(f"Average Socialite scraper failed: {e}")
    
    # Remove duplicates
    duplicates_removed = collection.remove_duplicates()
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate events")
    
    # Sort by date
    collection.sort_by_date()
    
    # Save events in both formats
    saved_files = storage_manager.save_events(collection, format="both")
    
    # Print summary
    print(f"\nScraping complete!")
    print(f"Total unique events: {len(collection)}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"\nFiles saved:")
    for format_type, filepath in saved_files.items():
        print(f"  - {format_type.upper()}: {filepath}")
    
    # Show breakdown by source
    if collection:
        sources = {}
        for event in collection:
            source = event.source or "Unknown"
            sources[source] = sources.get(source, 0) + 1
        
        print("\nEvents by source:")
        for source, count in sources.items():
            print(f"  - {source}: {count} events")
            
    # Show some upcoming events
    upcoming = collection.get_upcoming()[:5]
    if upcoming:
        print("\nNext 5 upcoming events:")
        for i, event in enumerate(upcoming, 1):
            print(f"  {i}. {event.name} - {event.date.strftime('%b %d')} at {event.location}")


def send_digest():
    """Send email digest to photographer."""
    from email_service.digest import DigestGenerator, DigestTracker
    
    logger.info("Starting digest generation")
    
    # Load latest events
    storage_manager = StorageManager()
    try:
        events = storage_manager.load_latest(format="json")
        logger.info(f"Loaded {len(events)} events")
    except Exception as e:
        logger.error(f"Failed to load events: {e}")
        print("Error: No events found. Please run 'scrape' first.")
        return
    
    # Filter to only new events
    tracker = DigestTracker()
    new_events = tracker.filter_new_events(events)
    logger.info(f"Found {len(new_events)} new events to include in digest")
    
    if len(new_events) == 0:
        print("No new events to send in digest.")
        return
    
    # Generate digest
    generator = DigestGenerator()
    digest = generator.generate_digest(new_events, max_events=20)
    
    # Save digest for preview
    saved_files = generator.save_digest(digest)
    
    print(f"\nDigest generated successfully!")
    print(f"Subject: {digest['subject']}")
    print(f"Events included: {digest['event_count']}")
    print(f"\nPreview files saved:")
    print(f"  - HTML: {saved_files['html']}")
    print(f"  - Text: {saved_files['text']}")
    
    # Mark events as sent
    event_ids = [event.event_id for event in new_events]
    tracker.mark_events_sent(event_ids, datetime.now())
    
    print("\nTo actually send the email, configure SMTP settings and run 'send-digest --send'")
    print("For now, you can preview the digest in the saved files.")


def check_replies():
    """Check for and parse photographer replies."""
    print("Checking for replies...")
    # TODO: Implement reply checking logic
    print("Reply check complete.")


def send_outreach():
    """Send outreach emails to selected event organizers."""
    print("Sending outreach emails...")
    # TODO: Implement outreach logic
    print("Outreach complete.")


def run_all():
    """Run the complete workflow."""
    print(f"Starting full workflow at {datetime.now()}")
    scrape()
    send_digest()
    # Note: check_replies and send_outreach would typically run separately
    # after photographer has had time to respond
    print("Full workflow complete.")


def main():
    parser = argparse.ArgumentParser(
        description="NYC Event Lead Scraper & Outreach Automator"
    )
    
    parser.add_argument(
        "command",
        choices=["scrape", "send-digest", "check-replies", "send-outreach", "run-all"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    commands = {
        "scrape": scrape,
        "send-digest": send_digest,
        "check-replies": check_replies,
        "send-outreach": send_outreach,
        "run-all": run_all
    }
    
    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()