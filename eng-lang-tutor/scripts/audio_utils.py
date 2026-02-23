#!/usr/bin/env python3
"""
Backward compatibility shim for audio_utils.py

The actual module has been moved to audio/utils.py
This file provides backward compatibility for existing imports.
"""

from .audio.utils import get_ffmpeg_path, get_audio_duration

__all__ = ['get_ffmpeg_path', 'get_audio_duration']
