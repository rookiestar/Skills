#!/usr/bin/env python3
"""
Backward compatibility shim for error_notebook.py

The actual module has been moved to core/error_notebook.py
This file provides backward compatibility for existing imports.
"""

from .core.error_notebook import ErrorNotebookManager

__all__ = ['ErrorNotebookManager']
