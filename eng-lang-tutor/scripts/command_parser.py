#!/usr/bin/env python3
"""
Backward compatibility shim for command_parser.py

The actual module has been moved to cli/command_parser.py
This file provides backward compatibility for existing imports.
"""

from .cli.command_parser import CommandParser

__all__ = ['CommandParser']
