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


def send_digest(send_email=False):
    """Send email digest to photographer."""
    from email_service.sender import EmailSender
    
    logger.info("Starting digest process")
    
    # Default to test mode unless --send flag is used
    test_mode = not send_email
    
    # Load latest events
    storage_manager = StorageManager()
    try:
        events = storage_manager.load_latest(format="json")
        logger.info(f"Loaded {len(events)} events")
    except Exception as e:
        logger.error(f"Failed to load events: {e}")
        print("Error: No events found. Please run 'scrape' first.")
        return
    
    try:
        sender = EmailSender()
        
        if test_mode:
            print("Running in test mode - email will be generated but not sent")
            
        success = sender.send_digest(events, test_mode=test_mode)
        
        if success:
            if test_mode:
                print("\n✓ Test digest generated successfully!")
                print("Check the data/digests directory for preview files.")
                print("\nTo actually send the email, run:")
                print("  python main.py send-digest --send")
            else:
                print("\n✓ Digest sent successfully!")
        else:
            if not test_mode:
                print("\n✗ Failed to send digest. Check logs for details.")
                
    except Exception as e:
        logger.error(f"Error in send_digest: {e}")
        print(f"\nError: {e}")
        print("\nMake sure you have configured email settings.")
        print("Run: python setup_gmail.py")


def check_replies():
    """Check for and parse photographer replies."""
    from email_service.sender import EmailMonitor
    from email_service.reply_parser import ReplyProcessor
    
    logger.info("Checking for email replies")
    
    try:
        monitor = EmailMonitor()
        processor = ReplyProcessor()
        
        # Check replies from last 48 hours by default
        hours_back = 48
        replies = monitor.check_replies(hours_back=hours_back)
        
        print(f"\nChecking emails from the last {hours_back} hours...")
        
        if not replies:
            print("No new replies found.")
            return
            
        print(f"\nFound {len(replies)} replies:")
        
        total_selections = 0
        
        for i, reply in enumerate(replies, 1):
            print(f"\n{i}. From: {reply['from']}")
            print(f"   Subject: {reply['subject']}")
            print(f"   Date: {reply['date']}")
            
            # Process the reply to extract event selections
            selected_events = processor.process_reply(reply)
            
            if selected_events:
                print(f"   ✓ Found {len(selected_events)} event selections:")
                for event in selected_events:
                    print(f"     - {event.name} ({event.date.strftime('%b %d')})")
                total_selections += len(selected_events)
            else:
                print("   ✗ No event selections found in this reply")
        
        if total_selections > 0:
            print(f"\n✓ Total events selected: {total_selections}")
            print("\nRun 'send-outreach' to send emails to the selected event organizers.")
        else:
            print("\nNo event selections were found in the replies.")
        
    except Exception as e:
        logger.error(f"Error checking replies: {e}")
        print(f"\nError: {e}")
        print("\nMake sure you have configured email settings.")
        print("Run: python setup_gmail.py")


def send_outreach(test_mode=False):
    """Send outreach emails to selected event organizers."""
    from email_service.outreach import OutreachSender, load_selected_events
    
    logger.info("Starting outreach process")
    
    # Load selected events
    selected_events = load_selected_events()
    
    if not selected_events:
        print("No selected events found.")
        print("Please run 'check-replies' first to process photographer selections.")
        return
        
    print(f"\nFound {len(selected_events)} selected events")
    
    if test_mode:
        print("\nRunning in test mode - emails will be generated but not sent")
        
    try:
        sender = OutreachSender()
        results = sender.send_outreach_for_events(selected_events, test_mode=test_mode)
        
        sent = results['sent']
        failed = results['failed']
        
        print(f"\n✓ Outreach complete!")
        print(f"  - Sent: {len(sent)} emails")
        print(f"  - Failed: {len(failed)} emails")
        
        if test_mode:
            print("\nTo actually send the emails, run:")
            print("  python main.py send-outreach --send")
        
        if failed:
            print("\nFailed events (no contact info):")
            for event_id in failed[:5]:
                print(f"  - {event_id}")
            if len(failed) > 5:
                print(f"  ... and {len(failed) - 5} more")
                
    except Exception as e:
        logger.error(f"Error sending outreach: {e}")
        print(f"\nError: {e}")


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
    
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send emails (for send-digest and send-outreach commands)"
    )
    
    args = parser.parse_args()
    
    commands = {
        "scrape": scrape,
        "send-digest": lambda: send_digest(send_email=args.send),
        "check-replies": check_replies,
        "send-outreach": lambda: send_outreach(test_mode=not args.send),
        "run-all": run_all
    }
    
    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()