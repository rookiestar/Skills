#!/usr/bin/env python3
"""
共享音频工具函数

提供音频处理相关的通用功能，避免代码重复。
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def get_ffmpeg_path() -> str:
    """
    获取 FFmpeg 可执行文件路径

    Returns:
        FFmpeg 路径

    Raises:
        RuntimeError: 如果未找到 FFmpeg
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg not found. Install it with: brew install ffmpeg (macOS) "
            "or apt-get install ffmpeg (Ubuntu)"
        )
    return ffmpeg_path


def get_audio_duration(audio_path: Path, ffmpeg_path: Optional[str] = None) -> float:
    """
    获取音频文件时长

    Args:
        audio_path: 音频文件路径
        ffmpeg_path: FFmpeg 可执行文件路径（可选，默认自动检测）

    Returns:
        时长（秒），如果无法解析则返回 0.0
    """
    if ffmpeg_path is None:
        ffmpeg_path = get_ffmpeg_path()

    cmd = [
        ffmpeg_path,
        "-i", str(audio_path),
        "-hide_banner",
        "-f", "null",
        "-"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        # ffmpeg 超时，返回 0.0
        return 0.0
    except Exception:
        return 0.0

    # 从 stderr 中解析时长，格式: "  Duration: 00:00:03.45, ..."
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return 0.0
