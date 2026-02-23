#!/usr/bin/env python3
"""
音频格式转换器 - 将 MP3 转换为飞书语音格式

飞书语音消息要求：
- 格式: Opus / Speex / AAC / AMR
- 采样率: 8000Hz / 16000Hz
- 声道: 单声道
"""

import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .utils import get_ffmpeg_path, get_audio_duration


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class AudioConverter:
    """音频格式转换器"""

    # 飞书支持的语音格式
    SUPPORTED_FORMATS = ["opus", "speex", "aac", "amr"]
    SUPPORTED_SAMPLE_RATES = [8000, 16000]

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        初始化转换器

        Args:
            ffmpeg_path: ffmpeg 可执行文件路径（默认自动检测）
        """
        self.ffmpeg_path = ffmpeg_path or get_ffmpeg_path()

    def convert_to_voice(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        format: str = "opus",
        sample_rate: int = 16000,
        bitrate: str = "24k"
    ) -> ConversionResult:
        """
        将音频文件转换为飞书语音格式

        Args:
            input_path: 输入文件路径（支持 MP3, WAV, M4A 等）
            output_path: 输出文件路径（可选，默认同目录更换扩展名）
            format: 输出格式（opus, speex, aac, amr）
            sample_rate: 采样率（8000 或 16000）
            bitrate: 比特率（默认 24k，适合语音）

        Returns:
            ConversionResult: 转换结果
        """
        # 参数验证
        if format not in self.SUPPORTED_FORMATS:
            return ConversionResult(
                success=False,
                error_message=f"Unsupported format: {format}. Supported: {self.SUPPORTED_FORMATS}"
            )

        if sample_rate not in self.SUPPORTED_SAMPLE_RATES:
            return ConversionResult(
                success=False,
                error_message=f"Unsupported sample rate: {sample_rate}. Supported: {self.SUPPORTED_SAMPLE_RATES}"
            )

        input_path = Path(input_path)
        if not input_path.exists():
            return ConversionResult(
                success=False,
                error_message=f"Input file not found: {input_path}"
            )

        # 确定输出路径
        if output_path is None:
            output_path = input_path.with_suffix(f".{format}")
        else:
            output_path = Path(output_path)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建 ffmpeg 命令
        codec_map = {
            "opus": "libopus",
            "speex": "libspeex",
            "aac": "aac",
            "amr": "libvo_amrwbenc"
        }

        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),      # 输入文件
            "-acodec", codec_map[format],  # 编码器
            "-ar", str(sample_rate),    # 采样率
            "-ac", "1",                 # 单声道
            "-ab", bitrate,             # 比特率
            "-y",                       # 覆盖输出文件
            str(output_path)
        ]

        # 特定格式优化
        if format == "opus":
            # Opus 针对语音优化
            cmd.extend(["-application", "audio"])
        elif format == "speex":
            # Speex 针对语音优化
            cmd.extend(["-compression_level", "10"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )

            if result.returncode != 0:
                return ConversionResult(
                    success=False,
                    error_message=f"ffmpeg error: {result.stderr}"
                )

            # 获取音频时长
            duration = get_audio_duration(output_path, self.ffmpeg_path)

            return ConversionResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration
            )

        except subprocess.TimeoutExpired:
            return ConversionResult(
                success=False,
                error_message="Conversion timeout (>60s)"
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                error_message=str(e)
            )

    def batch_convert(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        format: str = "opus",
        sample_rate: int = 16000
    ) -> dict:
        """
        批量转换目录中的音频文件

        Args:
            input_dir: 输入目录
            output_dir: 输出目录（可选，默认在输入目录下创建 voice/ 子目录）
            format: 输出格式
            sample_rate: 采样率

        Returns:
            转换结果字典 {原文件名: ConversionResult}
        """
        input_dir = Path(input_dir)
        if output_dir is None:
            output_dir = input_dir / "voice"
        else:
            output_dir = Path(output_dir)

        results = {}

        # 支持的输入格式
        input_extensions = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]

        for input_file in input_dir.glob("*"):
            if input_file.suffix.lower() not in input_extensions:
                continue

            output_file = output_dir / input_file.with_suffix(f".{format}").name
            results[input_file.name] = self.convert_to_voice(
                input_path=input_file,
                output_path=output_file,
                format=format,
                sample_rate=sample_rate
            )

        return results


# 便捷函数
def convert_mp3_to_opus(
    input_path: Path,
    output_path: Optional[Path] = None
) -> ConversionResult:
    """
    将 MP3 转换为 Opus 格式（飞书推荐）

    Args:
        input_path: MP3 文件路径
        output_path: 输出路径（可选）

    Returns:
        ConversionResult
    """
    converter = AudioConverter()
    return converter.convert_to_voice(
        input_path=input_path,
        output_path=output_path,
        format="opus",
        sample_rate=16000
    )
