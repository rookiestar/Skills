#!/usr/bin/env python3
"""
TTS Provider 抽象基类 - 所有 TTS 服务必须实现此接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, ClassVar
from pathlib import Path


# 支持的语速选项
SPEED_OPTIONS = {
    0.5: "非常慢 (Very Slow) - 初学者跟读",
    0.7: "慢速 (Slow) - 学习发音",
    0.9: "正常 (Normal) - 日常学习（推荐）",
    1.3: "快速 (Fast) - 听力挑战",
    1.7: "非常快 (Very Fast) - 进阶训练",
}


@dataclass
class TTSConfig:
    """通用 TTS 配置"""
    # 语速（0.5, 0.7, 0.9, 1.3, 1.7）
    speed: float = 0.9
    # 输出格式
    output_format: str = "mp3"
    # 角色音色映射（可选，为空则使用 provider 默认值）
    # 旁白 - 女声
    narrator_voice: str = ""
    # 对话 A - 男声
    dialogue_a_voice: str = ""
    # 对话 B - 女声
    dialogue_b_voice: str = ""
    # 兼容旧配置
    female_voice: str = ""
    male_voice: str = ""


@dataclass
class TTSResult:
    """TTS 合成结果"""
    success: bool
    audio_path: Optional[Path] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class TTSProvider(ABC):
    """
    TTS 服务提供者抽象基类

    所有 TTS 服务（讯飞、Edge-TTS 等）必须继承此类并实现抽象方法。
    """

    # 类属性：各 provider 的默认配置
    PROVIDER_NAME: ClassVar[str] = "base"
    DEFAULT_FEMALE_VOICE: ClassVar[str] = ""
    DEFAULT_MALE_VOICE: ClassVar[str] = ""
    # 默认角色音色映射
    DEFAULT_NARRATOR_VOICE: ClassVar[str] = ""    # 旁白 - 女声
    DEFAULT_DIALOGUE_A_VOICE: ClassVar[str] = ""  # 对话 A - 男声
    DEFAULT_DIALOGUE_B_VOICE: ClassVar[str] = ""  # 对话 B - 女声
    SUPPORTED_VOICES: ClassVar[Dict[str, str]] = {}  # voice_id -> description

    def __init__(self, config: Optional[TTSConfig] = None, **credentials):
        """
        初始化 TTS Provider

        Args:
            config: TTS 配置
            **credentials: Provider 特定的认证信息（api_key, appid 等）
        """
        self.config = config or TTSConfig()
        self.credentials = credentials
        self._validate_credentials()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """
        验证认证信息是否完整

        Raises:
            ValueError: 认证信息缺失或无效
        """
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> TTSResult:
        """
        合成语音

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            voice: 语音 ID（可选，使用配置中的默认值）
            speed: 语速（可选，使用配置中的默认值）

        Returns:
            TTSResult: 合成结果
        """
        pass

    def get_voice(self, gender: str = "female") -> str:
        """
        获取指定性别的语音 ID（兼容旧接口）

        Args:
            gender: 性别 ("female" 或 "male")

        Returns:
            语音 ID
        """
        if gender == "female":
            return self.config.female_voice or self.DEFAULT_FEMALE_VOICE
        return self.config.male_voice or self.DEFAULT_MALE_VOICE

    def get_voice_by_role(self, role: str) -> str:
        """
        获取指定角色的语音 ID

        Args:
            role: 角色 ("narrator", "dialogue_a", "dialogue_b")

        Returns:
            语音 ID
        """
        if role == "narrator":
            return self.config.narrator_voice or self.DEFAULT_NARRATOR_VOICE or self.DEFAULT_FEMALE_VOICE
        elif role == "dialogue_a":
            return self.config.dialogue_a_voice or self.DEFAULT_DIALOGUE_A_VOICE or self.DEFAULT_MALE_VOICE
        elif role == "dialogue_b":
            return self.config.dialogue_b_voice or self.DEFAULT_DIALOGUE_B_VOICE or self.DEFAULT_FEMALE_VOICE
        else:
            return self.get_voice("female")

    @classmethod
    def list_voices(cls) -> Dict[str, str]:
        """
        列出所有支持的语音

        Returns:
            语音 ID -> 描述 的字典
        """
        return cls.SUPPORTED_VOICES.copy()

    @classmethod
    def get_default_voices(cls) -> Dict[str, str]:
        """
        获取默认的角色音色映射

        Returns:
            角色 -> 默认语音 ID 的字典
        """
        return {
            "narrator": cls.DEFAULT_NARRATOR_VOICE or cls.DEFAULT_FEMALE_VOICE,
            "dialogue_a": cls.DEFAULT_DIALOGUE_A_VOICE or cls.DEFAULT_MALE_VOICE,
            "dialogue_b": cls.DEFAULT_DIALOGUE_B_VOICE or cls.DEFAULT_FEMALE_VOICE,
        }
