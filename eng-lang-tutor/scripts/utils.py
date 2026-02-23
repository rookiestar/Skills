#!/usr/bin/env python3
"""
Backward compatibility shim for utils.py

The actual module has been moved to utils/helpers.py
This file provides backward compatibility for existing imports.
"""

from .utils.helpers import safe_divide, deep_merge, clamp

__all__ = ['safe_divide', 'deep_merge', 'clamp']
