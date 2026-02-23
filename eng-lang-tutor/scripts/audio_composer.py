#!/usr/bin/env python3
"""
Backward compatibility shim for audio_composer.py

The actual module has been moved to audio/composer.py
This file provides backward compatibility for existing imports.
"""

from .audio.composer import AudioComposer, CompositionResult

__all__ = ['AudioComposer', 'CompositionResult']
