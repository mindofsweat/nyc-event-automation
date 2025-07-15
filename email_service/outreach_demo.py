#!/usr/bin/env python3
"""
Demo script to show outreach email generation with sample data.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from email_service.outreach import OutreachGenerator, OutreachSender
from data_store.models import EventModel
from datetime import datetime
from pathlib import Path
import json


def create_demo_event():
    """Create a demo event with contact information."""
    return EventModel(
        name="Hudson Yards Summer Concerts: Paul Russell",
        date=datetime(2025, 7, 16, 18, 0),
        location="Hudson Yards, NYC",
        source_url="https://www.hudsonyardsnewyork.com/events",
        contact_email="events@hudsonyardsnewyork.com",  # Demo email
        description="Join us for an amazing summer concert featuring Paul Russell at Hudson Yards.",
        source="demo"
    )


def demo_outreach():
    """Demonstrate outreach email generation."""
    print("Outreach Email Demo")
    print("=" * 50)
    
    # Create demo event
    event = create_demo_event()
    print(f"\nDemo Event: {event.name}")
    print(f"Date: {event.date.strftime('%B %d, %Y')}")
    print(f"Location: {event.location}")
    print(f"Contact: {event.contact_email}")
    
    # Generate outreach email
    generator = OutreachGenerator()
    email_data = generator.generate_outreach_email(
        event,
        organizer_name="Hudson Yards Events Team"
    )
    
    if email_data:
        print(f"\nGenerated Email:")
        print("-" * 50)
        print(f"To: {email_data['to']}")
        print(f"Subject: {email_data['subject']}")
        print("\nText Body Preview:")
        print(email_data['text_body'][:500] + "...")
        
        # Save demo files
        demo_dir = Path("data/demo_outreach")
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        # Save HTML version
        html_file = demo_dir / "demo_outreach.html"
        with open(html_file, 'w') as f:
            f.write(email_data['html_body'])
        print(f"\nHTML version saved to: {html_file}")
        
        # Save text version
        text_file = demo_dir / "demo_outreach.txt"
        with open(text_file, 'w') as f:
            f.write(email_data['text_body'])
        print(f"Text version saved to: {text_file}")
        
    else:
        print("\nFailed to generate email")


if __name__ == "__main__":
    demo_outreach()