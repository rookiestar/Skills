#!/usr/bin/env python3
"""
知识点音频合成器 - 将多个音频片段合并为单个文件

音频结构：
- expressions: 引导语 [1s] 内容 [2s]
- alternatives: 引导语 [1s] 内容 [2s]
- dialogues: 引导语 [1s] 对话行1 [0.5s] 对话行2 ...

使用示例：
    from scripts.audio_composer import AudioComposer
    from scripts.tts import TTSManager

    tts = TTSManager.from_env()
    composer = AudioComposer(tts)

    result = composer.compose_keypoint_audio(keypoint, Path("output.mp3"))
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from .tts import TTSManager
from .utils import get_ffmpeg_path, get_audio_duration


@dataclass
class CompositionResult:
    """音频合成结果"""
    success: bool
    audio_path: Optional[Path] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


class AudioComposer:
    """
    知识点音频合成器

    将 expressions + alternatives + dialogues 合并为单个音频文件
    """

    def __init__(
        self,
        tts_manager: TTSManager,
        ffmpeg_path: Optional[str] = None
    ):
        """
        初始化音频合成器

        Args:
            tts_manager: TTS 管理器实例
            ffmpeg_path: ffmpeg 可执行文件路径（默认自动检测）
        """
        self.tts = tts_manager
        self.ffmpeg_path = ffmpeg_path or get_ffmpeg_path()

        # 创建临时目录用于存放中间文件
        self.temp_dir = Path(tempfile.mkdtemp(prefix="audio_composer_"))

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，确保清理临时目录"""
        self._cleanup()
        return False

    def _cleanup(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __del__(self):
        """析构函数（备用清理，不保证被调用）"""
        self._cleanup()

    def compose_keypoint_audio(
        self,
        keypoint: dict,
        output_path: Path,
        lead_in_silence: float = 1.0,   # 引导语后留白
        section_silence: float = 2.0,   # 内容后留白（段落间隔）
        dialogue_silence: float = 0.5,  # 对话行之间留白
        narrator_voice: str = None,     # 旁白音色（None 时使用 TTS provider 默认值）
        voice_a: str = None,            # 对话 A 音色（None 时使用 TTS provider 默认值）
        voice_b: str = None,            # 对话 B 音色（None 时使用 TTS provider 默认值）
        speed: float = 0.9              # 语速
    ) -> CompositionResult:
        """
        合成知识点音频

        Args:
            keypoint: 知识点数据
            output_path: 输出文件路径
            lead_in_silence: 引导语后留白时长（秒）
            section_silence: 内容后留白时长（秒）
            dialogue_silence: 对话行之间留白时长（秒）
            narrator_voice: 旁白音色
            voice_a: 对话 A 角色音色
            voice_b: 对话 B 角色音色
            speed: 语速

        Returns:
            CompositionResult: 合成结果
        """
        try:
            # 使用 TTS provider 的默认音色（自动适配 Edge-TTS 或讯飞）
            narrator_voice = narrator_voice or self.tts.get_voice_by_role("narrator")
            voice_a = voice_a or self.tts.get_voice_by_role("dialogue_a")
            voice_b = voice_b or self.tts.get_voice_by_role("dialogue_b")

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            segments: List[Path] = []
            segment_index = 0

            # 1. Expressions 部分
            expressions = keypoint.get("expressions", [])
            if expressions:
                # 引导语
                lead_in = self._synthesize_segment(
                    text="Key expressions",
                    voice=narrator_voice,
                    speed=speed,
                    index=segment_index
                )
                segments.append(lead_in)
                segment_index += 1

                # 引导语后留白
                silence_1s = self._generate_silence(lead_in_silence)
                segments.append(silence_1s)

                # 内容
                phrases = [expr.get("phrase", "") for expr in expressions]
                content_text = ". ".join(p for p in phrases if p)
                if content_text:
                    content = self._synthesize_segment(
                        text=content_text,
                        voice=narrator_voice,
                        speed=speed,
                        index=segment_index
                    )
                    segments.append(content)
                    segment_index += 1

                # 内容后留白
                silence_2s = self._generate_silence(section_silence)
                segments.append(silence_2s)

            # 2. Alternatives 部分
            alternatives = keypoint.get("alternatives", [])
            if alternatives:
                # 引导语
                lead_in = self._synthesize_segment(
                    text="You can also say",
                    voice=narrator_voice,
                    speed=speed,
                    index=segment_index
                )
                segments.append(lead_in)
                segment_index += 1

                # 引导语后留白
                silence_1s = self._generate_silence(lead_in_silence)
                segments.append(silence_1s)

                # 内容
                content_text = ". ".join(alt for alt in alternatives if alt)
                if content_text:
                    content = self._synthesize_segment(
                        text=content_text,
                        voice=narrator_voice,
                        speed=speed,
                        index=segment_index
                    )
                    segments.append(content)
                    segment_index += 1

                # 内容后留白
                silence_2s = self._generate_silence(section_silence)
                segments.append(silence_2s)

            # 3. Dialogues 部分
            examples = keypoint.get("examples", [])
            if examples:
                # 引导语
                lead_in = self._synthesize_segment(
                    text="Dialogue",
                    voice=narrator_voice,
                    speed=speed,
                    index=segment_index
                )
                segments.append(lead_in)
                segment_index += 1

                # 引导语后留白
                silence_1s = self._generate_silence(lead_in_silence)
                segments.append(silence_1s)

                # 对话内容
                silence_05s = self._generate_silence(dialogue_silence)
                for example in examples:
                    dialogue = example.get("dialogue", [])
                    for line in dialogue:
                        if ":" in line:
                            speaker, text = line.split(":", 1)
                            speaker = speaker.strip()
                            text = text.strip()

                            if not text:
                                continue

                            # A = EricNeural (男声), B = JennyNeural (女声)
                            voice = voice_a if speaker.upper() == "A" else voice_b

                            segment = self._synthesize_segment(
                                text=text,
                                voice=voice,
                                speed=speed,
                                index=segment_index
                            )
                            segments.append(segment)
                            segment_index += 1

                            # 对话行之间留白
                            segments.append(silence_05s)

            if not segments:
                return CompositionResult(
                    success=False,
                    error_message="No audio content to compose"
                )

            # 4. 拼接所有片段
            final_audio = self._concatenate_segments(segments, output_path)

            # 5. 获取时长
            duration = get_audio_duration(final_audio, self.ffmpeg_path)

            return CompositionResult(
                success=True,
                audio_path=final_audio,
                duration_seconds=duration
            )

        except Exception as e:
            return CompositionResult(
                success=False,
                error_message=str(e)
            )

    def _synthesize_segment(
        self,
        text: str,
        voice: str,
        speed: float,
        index: int
    ) -> Path:
        """
        合成单个音频片段

        Args:
            text: 文本
            voice: 音色
            speed: 语速
            index: 片段索引

        Returns:
            音频文件路径
        """
        output_path = self.temp_dir / f"segment_{index}.mp3"

        result = self.tts.synthesize(
            text=text,
            output_path=output_path,
            voice=voice,
            speed=speed
        )

        if not result.success:
            raise RuntimeError(f"TTS synthesis failed: {result.error_message}")

        return output_path

    def _generate_silence(self, duration: float) -> Path:
        """
        生成空白音频

        Args:
            duration: 时长（秒）

        Returns:
            空白音频文件路径
        """
        output_path = self.temp_dir / f"silence_{duration}.mp3"

        if output_path.exists():
            return output_path

        cmd = [
            self.ffmpeg_path,
            "-f", "lavfi",
            "-i", f"anullsrc=r=16000:cl=mono",
            "-t", str(duration),
            "-y",
            str(output_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to generate silence: {result.stderr}")

        return output_path

    def _concatenate_segments(
        self,
        segments: List[Path],
        output_path: Path
    ) -> Path:
        """
        拼接多个音频片段

        Args:
            segments: 音频片段路径列表
            output_path: 输出文件路径

        Returns:
            拼接后的音频文件路径
        """
        # 创建文件列表
        list_file = self.temp_dir / "concat_list.txt"
        with open(list_file, "w") as f:
            for seg in segments:
                # 需要转义路径中的特殊字符
                escaped_path = str(seg).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
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
            raise RuntimeError(f"Failed to concatenate audio: {result.stderr}")

        return output_path
