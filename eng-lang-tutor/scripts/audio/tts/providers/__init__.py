#!/usr/bin/env python3
"""
TTS Providers - TTS 服务提供者实现
"""

from .xunfei import XunFeiProvider
from .edge import EdgeTTSProvider

__all__ = [
    "XunFeiProvider",
    "EdgeTTSProvider",
]
