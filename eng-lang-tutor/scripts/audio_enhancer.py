#!/usr/bin/env python3
"""
音频后处理优化器 - 使用 ffmpeg 直接处理

优化手段：
1. 音量归一化 - 统一音量水平
2. 动态压缩 - 让声音更饱满
3. 轻微混响 - 增加空间感
4. 高频增强 - 提升清晰度
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import subprocess
import shutil
import re


@dataclass
class EnhancementResult:
    """音频优化结果"""
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None


class AudioEnhancer:
    """
    音频后处理优化器

    使用 ffmpeg 对 TTS 生成的音频进行优化
    """

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        初始化音频优化器

        Args:
            ffmpeg_path: ffmpeg 可执行文件路径（默认自动检测）
        """
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        if not self.ffmpeg_path:
            raise RuntimeError(
                "ffmpeg not found. Install it with: brew install ffmpeg (macOS) "
                "or apt-get install ffmpeg (Ubuntu)"
            )

    def enhance(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        normalize_volume: bool = True,
        compression: float = 0.3,
        reverb_amount: float = 0.2,
        high_boost: float = 3.0
    ) -> EnhancementResult:
        """
        优化音频文件

        Args:
            input_path: 输入音频文件路径
            output_path: 输出文件路径（默认添加 .enhanced 后缀）
            normalize_volume: 是否归一化音量
            compression: 压缩强度（0-1）
            reverb_amount: 混响强度（0-1）
            high_boost: 高频增益（dB，0-6）

        Returns:
            EnhancementResult: 优化结果
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                return EnhancementResult(
                    success=False,
                    error_message=f"Input file not found: {input_path}"
                )

            output_path = Path(output_path) if output_path else input_path.with_stem(
                input_path.stem + "_enhanced"
            ).with_suffix(".mp3")

            # 构建 ffmpeg 滤镜链
            filters = []

            # 1. 归一化音量
            if normalize_volume:
                filters.append("loudnorm=I=-14:TP=-1.5:LRA=11")

            # 2. 动态压缩 - 让声音更饱满
            if compression > 0:
                # compand 压缩器: attacks:decays:points:soft-knee:gain:initial-volume:delay
                # 使用简单压缩
                filters.append(f"acompressor=threshold=-20dB:ratio=3:attack=5:release=50")

            # 3. 高频增强 - 提升清晰度
            if high_boost > 0:
                filters.append(f"equalizer=f=4000:t=h:w=2000:g={high_boost}")

            # 4. 轻微混响 - 增加空间感
            if reverb_amount > 0:
                # aecho 滤镜: in_gain:out_gain:delays:decays
                delay = 30  # 30ms 延迟
                decay = reverb_amount * 0.5  # 混响衰减
                filters.append(f"aecho=0.8:0.9:{delay}:{decay}")

            # 5. 最终音量调整
            filters.append("volume=1.2")

            # 组合滤镜
            filter_str = ",".join(filters)

            # 构建 ffmpeg 命令
            cmd = [
                self.ffmpeg_path,
                "-i", str(input_path),
                "-af", filter_str,
                "-c:a", "libmp3lame",
                "-q:a", "2",  # 高质量 MP3
                "-y",
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return EnhancementResult(
                    success=False,
                    error_message=f"ffmpeg error: {result.stderr}"
                )

            return EnhancementResult(
                success=True,
                output_path=output_path
            )

        except subprocess.TimeoutExpired:
            return EnhancementResult(
                success=False,
                error_message="ffmpeg timeout (>120s)"
            )
        except Exception as e:
            return EnhancementResult(
                success=False,
                error_message=str(e)
            )

    def enhance_simple(
        self,
        input_path: Path,
        output_path: Optional[Path] = None
    ) -> EnhancementResult:
        """
        简单优化（预设参数）

        适合快速处理，效果适中
        """
        return self.enhance(
            input_path=input_path,
            output_path=output_path,
            normalize_volume=True,
            compression=0.3,
            reverb_amount=0.15,
            high_boost=2.0
        )

    def enhance_natural(
        self,
        input_path: Path,
        output_path: Optional[Path] = None
    ) -> EnhancementResult:
        """
        自然风格优化

        更柔和的处理，适合对话场景
        """
        return self.enhance(
            input_path=input_path,
            output_path=output_path,
            normalize_volume=True,
            compression=0.2,
            reverb_amount=0.25,
            high_boost=1.5
        )

    def enhance_clear(
        self,
        input_path: Path,
        output_path: Optional[Path] = None
    ) -> EnhancementResult:
        """
        清晰风格优化

        更强的处理，适合学习场景
        """
        return self.enhance(
            input_path=input_path,
            output_path=output_path,
            normalize_volume=True,
            compression=0.4,
            reverb_amount=0.1,
            high_boost=4.0
        )

    def batch_enhance(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        pattern: str = "*.mp3",
        preset: str = "simple"
    ) -> dict:
        """
        批量优化目录中的音频文件

        Args:
            input_dir: 输入目录
            output_dir: 输出目录（默认在输入目录下创建 enhanced/ 子目录）
            pattern: 文件匹配模式
            preset: 预设 ("simple", "natural", "clear")

        Returns:
            结果字典 {文件名: EnhancementResult}
        """
        input_dir = Path(input_dir)
        if output_dir is None:
            output_dir = input_dir / "enhanced"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        enhance_func = {
            "simple": self.enhance_simple,
            "natural": self.enhance_natural,
            "clear": self.enhance_clear
        }.get(preset, self.enhance_simple)

        for audio_file in input_dir.glob(pattern):
            output_file = output_dir / audio_file.name
            results[audio_file.name] = enhance_func(audio_file, output_file)

        return results


def enhance_audio_file(
    input_path: Path,
    output_path: Optional[Path] = None
) -> EnhancementResult:
    """
    便捷函数：优化单个音频文件

    使用简单预设
    """
    enhancer = AudioEnhancer()
    return enhancer.enhance_simple(input_path, output_path)
