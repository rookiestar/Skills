#!/usr/bin/env python3
"""
TTS Provider 抽象基类 - 所有 TTS 服务必须实现此接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, ClassVar
from pathlib import Path


@dataclass
class TTSConfig:
    """通用 TTS 配置"""
    female_voice: str = ""  # 由各 provider 提供默认值
    male_voice: str = ""    # 由各 provider 提供默认值
    speed: float = 0.9      # 语速（0.5-2.0，1.0 = 正常）
    output_format: str = "mp3"


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
        获取指定性别的语音 ID

        Args:
            gender: 性别 ("female" 或 "male")

        Returns:
            语音 ID
        """
        if gender == "female":
            return self.config.female_voice or self.DEFAULT_FEMALE_VOICE
        return self.config.male_voice or self.DEFAULT_MALE_VOICE

    @classmethod
    def list_voices(cls) -> Dict[str, str]:
        """
        列出所有支持的语音

        Returns:
            语音 ID -> 描述 的字典
        """
        return cls.SUPPORTED_VOICES.copy()
