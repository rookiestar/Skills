#!/usr/bin/env python3
"""
Backward compatibility shim for dedup.py

The actual module has been moved to utils/dedup.py
This file provides backward compatibility for existing imports.
"""

from .utils.dedup import DeduplicationManager

__all__ = ['DeduplicationManager']
