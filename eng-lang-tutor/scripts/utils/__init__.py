#!/usr/bin/env python3
"""Utilities: helper functions and deduplication."""

from .helpers import safe_divide, deep_merge, clamp
from .dedup import DeduplicationManager

__all__ = [
    'safe_divide',
    'deep_merge',
    'clamp',
    'DeduplicationManager',
]
