#!/usr/bin/env python3
"""
TTS Module - Text-to-Speech integration for eng-lang-tutor

Provides a unified interface for multiple TTS providers:
- XunFei (讯飞): Free tier with 500 min/day, stable in China
- Edge-TTS: Completely free, requires VPN in China

Usage:
    from scripts.tts import TTSManager

    # Using XunFei (from environment variables)
    manager = TTSManager.from_env()

    # Using Edge-TTS (no credentials needed)
    manager = TTSManager(provider="edge-tts")

    # Generate audio for keypoint
    audio_info = manager.generate_keypoint_audio(keypoint)
"""

from .manager import TTSManager
from .base import TTSProvider, TTSConfig, TTSResult

__all__ = [
    "TTSManager",
    "TTSProvider",
    "TTSConfig",
    "TTSResult",
]
