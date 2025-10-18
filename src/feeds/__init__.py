"""
Feeds Module
============
RSS/Atom feed generation for parliamentary data.

Exports:
    - FeedBuilder: Base feed builder class
    - FeedFormat: RSS/Atom format enum
    - GuidBuilder: GUID generation utility
    - BillsFeedBuilder: Bills feed builder
    - LatestBillsFeedBuilder: Latest bills feed
    - BillsByTagFeedBuilder: Tag-filtered bills feed
    - AllEntitiesFeedBuilder: Unified activity feed
    - feed_cache: Global feed cache instance
"""

from .feed_builder import (
    FeedBuilder,
    FeedFormat,
    GuidBuilder,
    FeedCache,
    feed_cache
)

from .bill_feeds import (
    BillsFeedBuilder,
    LatestBillsFeedBuilder,
    BillsByTagFeedBuilder,
    AllEntitiesFeedBuilder
)

__all__ = [
    # Base classes
    'FeedBuilder',
    'FeedFormat',
    'GuidBuilder',
    'FeedCache',
    'feed_cache',
    
    # Bill feeds
    'BillsFeedBuilder',
    'LatestBillsFeedBuilder',
    'BillsByTagFeedBuilder',
    'AllEntitiesFeedBuilder',
]
