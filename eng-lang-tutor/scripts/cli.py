#!/usr/bin/env python3
"""
Backward compatibility shim for cli.py

The actual module has been moved to cli/cli.py
This file provides backward compatibility for existing imports.
"""

from .cli.cli import main

__all__ = ['main']
