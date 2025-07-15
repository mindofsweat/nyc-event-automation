#!/usr/bin/env python3
"""
Test the reply parser with example inputs.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from email_service.reply_parser import ReplyParser


def test_parser():
    """Test the reply parser with various input formats."""
    parser = ReplyParser()
    
    test_replies = [
        {
            'name': 'Comma separated',
            'body': '1, 3, 5'
        },
        {
            'name': 'With text',
            'body': 'Hi! I would like to pursue events 2, 4, and 7. Thanks!'
        },
        {
            'name': 'List format',
            'body': '''
            Here are my selections:
            1
            3
            6
            
            Looking forward to these!
            '''
        },
        {
            'name': 'Mixed format',
            'body': 'I\'m interested in #1, event 4, and the 6th one'
        },
        {
            'name': 'With quotes',
            'body': '''
            2, 5
            
            > On Monday, you wrote:
            > Here are the latest events...
            > 1. Photography Workshop
            '''
        },
        {
            'name': 'No selections',
            'body': 'Thanks for the email, but I\'m not available this week.'
        }
    ]
    
    print("Reply Parser Test")
    print("=" * 50)
    
    for test in test_replies:
        print(f"\nTest: {test['name']}")
        print(f"Reply body: {test['body'].strip()}")
        
        selections = parser.parse_reply(test['body'])
        
        if selections:
            print(f"✓ Found selections: {selections}")
        else:
            print("✗ No selections found")
        
        print("-" * 30)


if __name__ == "__main__":
    test_parser()