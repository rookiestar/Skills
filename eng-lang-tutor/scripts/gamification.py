#!/usr/bin/env python3
"""
Backward compatibility shim for gamification.py

The actual module has been moved to core/gamification.py
This file provides backward compatibility for existing imports.
"""

from .core.gamification import GamificationManager

__all__ = ['GamificationManager']
