"""
Event scrapers for NYC-based event websites.
"""

from .base import Event, BaseScraper
from .eventbrite import EventbriteScraper
from .nycforfree import NYCForFreeScraper
from .averagesocialite import AverageSocialiteScraper

__all__ = [
    'Event', 
    'BaseScraper', 
    'EventbriteScraper',
    'NYCForFreeScraper',
    'AverageSocialiteScraper'
]