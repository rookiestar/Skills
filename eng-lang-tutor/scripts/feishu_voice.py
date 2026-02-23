#!/usr/bin/env python3
"""
Backward compatibility shim for feishu_voice.py

The actual module has been moved to audio/feishu_voice.py
This file provides backward compatibility for existing imports.
"""

from .audio.feishu_voice import FeishuVoiceSender, VoiceSendResult

__all__ = ['FeishuVoiceSender', 'VoiceSendResult']
