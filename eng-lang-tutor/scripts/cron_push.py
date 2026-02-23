#!/usr/bin/env python3
"""
Backward compatibility shim for cron_push.py

The actual module has been moved to scheduling/cron_push.py
This file provides backward compatibility for existing imports.
"""

from .scheduling.cron_push import CronPusher

__all__ = ['CronPusher']
