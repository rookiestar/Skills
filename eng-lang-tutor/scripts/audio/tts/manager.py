#!/usr/bin/env python3
"""
TTS 管理器 - 通用入口，支持多 Provider

提供统一的 TTS 接口，支持切换不同的 TTS 服务提供商。

使用示例：
    # 方式 1：从环境变量读取配置（默认使用 Edge-TTS）
    manager = TTSManager.from_env()

    # 方式 2：使用 Edge-TTS（默认，免费无需认证）
    manager = TTSManager(provider="edge-tts")

    # 方式 3：使用讯飞（需要认证）
    manager = TTSManager(
        provider="xunfei",
        appid="xxx",
        api_key="xxx",
        api_secret="xxx"
    )

    # 合成单条语音
    result = manager.synthesize("Hello", Path("output.mp3"))

    # 为知识点生成所有音频
    audio_info = manager.generate_keypoint_audio(keypoint)
"""

from pathlib import Path
from typing import Dict, Any, Optional, Type, ClassVar
from datetime import date, datetime
import os
import sys

# 添加 scripts 目录到路径以导入 state_manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .base import TTSProvider, TTSConfig, TTSResult
from .providers.xunfei import XunFeiProvider
from .providers.edge import EdgeTTSProvider

try:
    from ...core.state_manager import get_default_state_dir
except ImportError:
    from scripts.core.state_manager import get_default_state_dir


# Provider 注册表
PROVIDERS: Dict[str, Type[TTSProvider]] = {
    "edge-tts": EdgeTTSProvider,  # 默认推荐
    "xunfei": XunFeiProvider,     # 备选方案
}


class TTSManager:
    """
    TTS 管理器 - 统一入口

    提供统一的 TTS 接口，支持：
    - 多 Provider 切换
    - 环境变量配置
    - 知识点音频批量生成
    """

    # 支持的 Provider 列表
    SUPPORTED_PROVIDERS: ClassVar[list] = list(PROVIDERS.keys())

    def __init__(
        self,
        provider: str = "edge-tts",
        data_dir: str = None,
        config: Optional[TTSConfig] = None,
        **credentials
    ):
        """
        初始化 TTS 管理器

        Args:
            provider: Provider 名称（目前仅支持 "xunfei"）
            data_dir: 数据目录（默认使用 OPENCLAW_STATE_DIR 或 ~/.openclaw/state/eng-lang-tutor/）
            config: TTS 配置
            **credentials: Provider 认证信息

        示例:
            # 讯飞（使用默认数据目录）
            manager = TTSManager(provider="xunfei")

            # 讯飞（直接传入密钥）
            manager = TTSManager(
                provider="xunfei",
                appid="xxx",
                api_key="xxx",
                api_secret="xxx"
            )
        """
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(PROVIDERS.keys())}"
            )

        # 使用与 StateManager 相同的默认目录逻辑
        if data_dir is None:
            self.data_dir = get_default_state_dir()
        else:
            self.data_dir = Path(data_dir)

        self.audio_dir = self.data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self.provider_name = provider
        self.config = config or TTSConfig()

        # 初始化 Provider
        self.provider: TTSProvider = PROVIDERS[provider](
            config=self.config,
            **credentials
        )

    @classmethod
    def from_env(cls, provider: Optional[str] = None, **kwargs) -> "TTSManager":
        """
        从环境变量创建 TTS 管理器

        环境变量格式：
            TTS_PROVIDER=xunfei
            XUNFEI_APPID=xxx
            XUNFEI_API_KEY=xxx
            XUNFEI_API_SECRET=xxx

        Args:
            provider: Provider 名称（可选，默认从 TTS_PROVIDER 环境变量读取）
            **kwargs: 其他参数传递给构造函数

        Returns:
            TTSManager 实例
        """
        provider = provider or os.getenv("TTS_PROVIDER", "edge-tts")
        return cls(provider=provider, **kwargs)

    def switch_provider(self, provider: str, **credentials) -> None:
        """
        切换 Provider

        Args:
            provider: Provider 名称
            **credentials: 新 Provider 的认证信息
        """
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(PROVIDERS.keys())}"
            )

        self.provider_name = provider
        self.provider = PROVIDERS[provider](
            config=self.config,
            **credentials
        )

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> TTSResult:
        """
        合成单条语音

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            voice: 语音 ID（可选）
            speed: 语速（可选，0.5-2.0）

        Returns:
            TTSResult: 合成结果
        """
        return self.provider.synthesize(text, output_path, voice, speed)

    def generate_keypoint_audio(
        self,
        keypoint: Dict[str, Any],
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        为知识点生成所有音频

        生成内容：
        - 对话音频（按角色分文件，A=女声，B=男声）
        - 表达音频（语速更慢，适合学习）

        Args:
            keypoint: 知识点数据
            target_date: 目标日期（可选，默认今天）

        Returns:
            音频信息字典，包含 dialogue 和 expressions 列表
        """
        target_date = target_date or date.today()
        date_str = target_date.strftime('%Y-%m-%d')

        date_audio_dir = self.audio_dir / date_str
        date_audio_dir.mkdir(parents=True, exist_ok=True)

        audio_info = {
            "dialogue": [],
            "expressions": [],
            "generated_at": datetime.now().isoformat(),
            "provider": self.provider_name
        }

        # 1. 生成对话音频
        for i, example in enumerate(keypoint.get("examples", [])):
            for j, line in enumerate(example.get("dialogue", [])):
                if ":" in line:
                    speaker, text = line.split(":", 1)
                    speaker = speaker.strip()
                    text = text.strip()

                    if not text:
                        continue

                    # A = 男声，B = 女声
                    gender = "male" if speaker.upper() == "A" else "female"
                    voice = self.provider.get_voice(gender)
                    output_path = date_audio_dir / f"dialogue_{i}_{j}_{speaker}.mp3"

                    result = self.synthesize(
                        text=text,
                        output_path=output_path,
                        voice=voice
                    )

                    if result.success:
                        audio_info["dialogue"].append({
                            "speaker": speaker,
                            "text": text,
                            "audio_url": f"audio/{date_str}/{output_path.name}"
                        })
                    else:
                        # 记录错误但不中断
                        audio_info["dialogue"].append({
                            "speaker": speaker,
                            "text": text,
                            "error": result.error_message
                        })

        # 2. 生成表达音频（语速更慢）
        for i, expr in enumerate(keypoint.get("expressions", [])):
            phrase = expr.get("phrase", "")
            if not phrase:
                continue

            output_path = date_audio_dir / f"expression_{i+1}.mp3"
            result = self.synthesize(
                text=phrase,
                output_path=output_path,
                speed=0.7  # 更慢语速，适合学习
            )

            if result.success:
                audio_info["expressions"].append({
                    "text": phrase,
                    "audio_url": f"audio/{date_str}/{output_path.name}"
                })
            else:
                audio_info["expressions"].append({
                    "text": phrase,
                    "error": result.error_message
                })

        return audio_info

    @classmethod
    def list_supported_providers(cls) -> list:
        """
        列出所有支持的 Provider

        Returns:
            Provider 名称列表
        """
        return list(PROVIDERS.keys())

    def list_voices(self) -> Dict[str, str]:
        """
        列出当前 Provider 支持的语音

        Returns:
            语音 ID -> 描述 的字典
        """
        return self.provider.list_voices()

    def get_voice_by_role(self, role: str) -> str:
        """
        获取指定角色的语音 ID

        Args:
            role: 角色 ("narrator", "dialogue_a", "dialogue_b")

        Returns:
            语音 ID
        """
        return self.provider.get_voice_by_role(role)

    def get_audio_path(self, date_str: str, filename: str) -> Path:
        """
        获取音频文件的完整路径

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            filename: 文件名

        Returns:
            完整文件路径
        """
        return self.audio_dir / date_str / filename
