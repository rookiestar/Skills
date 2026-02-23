#!/usr/bin/env python3
"""
Backward compatibility shim for state_manager.py

The actual module has been moved to core/state_manager.py
This file provides backward compatibility for existing imports.
"""

from .core.state_manager import StateManager, get_default_state_dir

__all__ = ['StateManager', 'get_default_state_dir']
