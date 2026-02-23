#!/usr/bin/env python3
"""
Backward compatibility shim for scorer.py

The actual module has been moved to core/scorer.py
This file provides backward compatibility for existing imports.
"""

from .core.scorer import Scorer

__all__ = ['Scorer']
