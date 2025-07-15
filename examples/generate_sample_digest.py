#!/usr/bin/env python3
"""
Generate a sample email digest for testing/preview.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data_store import EventModel, EventCollection
from email_service.digest import DigestGenerator


def create_sample_events():
    """Create sample events for demonstration."""
    collection = EventCollection()
    
    # Create events for the next few days
    base_date = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
    
    sample_events = [
        EventModel(
            name="Brooklyn Food & Wine Festival",
            date=base_date + timedelta(days=2),
            location="Brooklyn Bridge Park, Brooklyn",
            source_url="https://eventbrite.com/brooklyn-food-wine",
            description="Annual celebration featuring local restaurants, wineries, and live music. Perfect for capturing culinary moments and crowd scenes.",
            source="Eventbrite"
        ),
        EventModel(
            name="SoHo Gallery Opening: Modern Photography",
            date=base_date + timedelta(days=3, hours=1),
            location="Gallery 23, SoHo, Manhattan",
            source_url="https://nycforfree.com/gallery-opening",
            description="Opening reception for new photography exhibition. Network with artists and art enthusiasts.",
            source="NYC For Free"
        ),
        EventModel(
            name="Central Park Concert Series",
            date=base_date + timedelta(days=5),
            location="Rumsey Playfield, Central Park",
            source_url="https://averagesocialite.com/central-park-concert",
            description="Free outdoor concert featuring local indie bands. Great opportunity for live music photography.",
            source="Average Socialite"
        ),
        EventModel(
            name="Rooftop Networking Event",
            date=base_date + timedelta(days=6, hours=2),
            location="230 Fifth Rooftop Bar, Manhattan",
            source_url="https://eventbrite.com/rooftop-networking",
            description="Professional networking event with stunning NYC skyline views.",
            source="Eventbrite"
        ),
        EventModel(
            name="Street Art Walking Tour",
            date=base_date + timedelta(days=8),
            location="Bushwick, Brooklyn",
            source_url="https://nycforfree.com/street-art-tour",
            description="Guided tour of Bushwick's vibrant street art scene. Document urban art and culture.",
            source="NYC For Free"
        ),
    ]
    
    for event in sample_events:
        collection.add(event)
    
    return collection


def main():
    """Generate and save sample digest."""
    print("Generating sample email digest...")
    
    # Create sample events
    events = create_sample_events()
    print(f"Created {len(events)} sample events")
    
    # Generate digest
    generator = DigestGenerator()
    digest = generator.generate_digest(events)
    
    # Save to examples directory
    output_dir = Path("examples/sample_digests")
    saved_files = generator.save_digest(digest, output_dir)
    
    print(f"\nDigest generated successfully!")
    print(f"Subject: {digest['subject']}")
    print(f"Events included: {digest['event_count']}")
    print(f"\nFiles saved:")
    print(f"  - HTML: {saved_files['html']}")
    print(f"  - Text: {saved_files['text']}")
    print(f"\nOpen the HTML file in a browser to preview the email format.")


if __name__ == "__main__":
    main()