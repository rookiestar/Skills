#!/usr/bin/env python3
"""Audio functionality: TTS, composition, conversion, Feishu integration."""

from .composer import AudioComposer, CompositionResult
from .converter import AudioConverter, ConversionResult, convert_mp3_to_opus
from .utils import get_ffmpeg_path, get_audio_duration
from .feishu_voice import FeishuVoiceSender, VoiceSendResult
from .tts import TTSManager, TTSProvider, TTSResult

__all__ = [
    'AudioComposer',
    'CompositionResult',
    'AudioConverter',
    'ConversionResult',
    'convert_mp3_to_opus',
    'get_ffmpeg_path',
    'get_audio_duration',
    'FeishuVoiceSender',
    'VoiceSendResult',
    'TTSManager',
    'TTSProvider',
    'TTSResult',
]
