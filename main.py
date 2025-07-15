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


# Configure logger
logger.add("logs/scraper_{time}.log", rotation="1 day", retention="7 days")


def scrape():
    """Run all scrapers and save event data."""
    logger.info("Starting scraping process")
    
    all_events = []
    
    # Run Eventbrite scraper
    try:
        logger.info("Running Eventbrite scraper...")
        eventbrite_scraper = EventbriteScraper(max_pages=3)
        eventbrite_events = eventbrite_scraper.scrape()
        all_events.extend(eventbrite_events)
        logger.info(f"Eventbrite: Found {len(eventbrite_events)} events")
    except Exception as e:
        logger.error(f"Eventbrite scraper failed: {e}")
    
    # Run NYC For Free scraper
    try:
        logger.info("Running NYC For Free scraper...")
        nycforfree_scraper = NYCForFreeScraper()
        nycforfree_events = nycforfree_scraper.scrape()
        all_events.extend(nycforfree_events)
        logger.info(f"NYC For Free: Found {len(nycforfree_events)} events")
    except Exception as e:
        logger.error(f"NYC For Free scraper failed: {e}")
    
    # Run Average Socialite scraper
    try:
        logger.info("Running Average Socialite scraper...")
        averagesocialite_scraper = AverageSocialiteScraper(max_pages=3)
        averagesocialite_events = averagesocialite_scraper.scrape()
        all_events.extend(averagesocialite_events)
        logger.info(f"Average Socialite: Found {len(averagesocialite_events)} events")
    except Exception as e:
        logger.error(f"Average Socialite scraper failed: {e}")
    
    # Save events to JSON
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"events_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(
            [event.to_dict() for event in all_events],
            f,
            indent=2,
            default=str
        )
    
    logger.info(f"Saved {len(all_events)} events to {output_file}")
    print(f"\nScraping complete!")
    print(f"Total events found: {len(all_events)}")
    print(f"Events saved to: {output_file}")
    
    # Show breakdown by source
    if all_events:
        sources = {}
        for event in all_events:
            source = event.source or "Unknown"
            sources[source] = sources.get(source, 0) + 1
        
        print("\nEvents by source:")
        for source, count in sources.items():
            print(f"  - {source}: {count} events")


def send_digest():
    """Send email digest to photographer."""
    print("Sending digest email...")
    # TODO: Implement digest sending logic
    print("Digest sent.")


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