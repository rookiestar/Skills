#!/usr/bin/env python3
"""
Backward compatibility shim for audio_converter.py

The actual module has been moved to audio/converter.py
This file provides backward compatibility for existing imports.
"""

from .audio.converter import AudioConverter, ConversionResult, convert_mp3_to_opus

__all__ = ['AudioConverter', 'ConversionResult', 'convert_mp3_to_opus']
