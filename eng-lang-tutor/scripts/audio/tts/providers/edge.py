#!/usr/bin/env python3
"""
Edge-TTS Provider 实现

Microsoft Edge TTS 服务：
- 完全免费，无需 API 密钥
- 高质量 24kHz 神经语音
- 支持多种美式英语发音人
- 国内网络可能需要代理
"""

import asyncio
import edge_tts
from pathlib import Path
from typing import Optional, ClassVar, Dict

from ..base import TTSProvider, TTSConfig, TTSResult


class EdgeTTSProvider(TTSProvider):
    """
    Microsoft Edge TTS Provider

    支持的美式英语发音人：
    - en-US-JennyNeural: 女声，友好亲切（推荐）
    - en-US-AriaNeural: 女声，自信清晰
    - en-US-EricNeural: 男声，专业理性（推荐）
    - en-US-GuyNeural: 男声，热情活力
    - en-US-AnaNeural: 女声，可爱随和
    - en-US-ChristopherNeural: 男声，权威可靠

    无需认证信息，直接使用。
    """

    PROVIDER_NAME: ClassVar[str] = "edge-tts"
    DEFAULT_FEMALE_VOICE: ClassVar[str] = "en-US-JennyNeural"  # 友好亲切
    DEFAULT_MALE_VOICE: ClassVar[str] = "en-US-EricNeural"     # 专业理性
    # 角色音色映射：旁白-女声，对话A-男声，对话B-女声
    DEFAULT_NARRATOR_VOICE: ClassVar[str] = "en-US-JennyNeural"    # 旁白 - 女声
    DEFAULT_DIALOGUE_A_VOICE: ClassVar[str] = "en-US-EricNeural"   # 对话 A - 男声
    DEFAULT_DIALOGUE_B_VOICE: ClassVar[str] = "en-US-JennyNeural"  # 对话 B - 女声

    SUPPORTED_VOICES: ClassVar[Dict[str, str]] = {
        "en-US-JennyNeural": "美式英语女声，友好亲切（推荐）",
        "en-US-AriaNeural": "美式英语女声，自信清晰",
        "en-US-EricNeural": "美式英语男声，专业理性（推荐）",
        "en-US-GuyNeural": "美式英语男声，热情活力",
        "en-US-AnaNeural": "美式英语女声，可爱随和",
        "en-US-ChristopherNeural": "美式英语男声，权威可靠",
        "en-US-MichelleNeural": "美式英语女声，友好舒适",
        "en-US-RogerNeural": "美式英语男声，生动活泼",
        "en-US-AndrewNeural": "美式英语男声，友好积极",
        "en-US-BrianNeural": "美式英语男声，友好积极",
        "en-US-EmmaNeural": "美式英语女声，友好积极",
        "en-US-AvaNeural": "美式英语女声，友好积极",
    }

    def _validate_credentials(self) -> None:
        """
        验证认证信息

        Edge-TTS 不需要认证信息，直接通过。
        """
        # Edge-TTS 不需要任何认证信息
        pass

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
            output_path: 输出文件路径（.mp3）
            voice: 语音 ID（可选，默认使用女声）
            speed: 语速（可选，0.5-2.0，1.0 = 正常）

        Returns:
            TTSResult: 合成结果
        """
        voice = voice or self.get_voice("female")
        speed_val = speed or self.config.speed

        # 将 speed (0.5-2.0) 转换为 edge-tts 的 rate 格式
        # speed=1.0 -> rate="+0%"
        # speed=0.7 -> rate="-30%" (更慢，适合学习)
        # speed=1.5 -> rate="+50%" (更快)
        rate_percent = int((speed_val - 1.0) * 100)
        rate = f"{rate_percent:+d}%"

        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _synthesize_async():
            """异步合成语音"""
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(str(output_path))

        try:
            # 在同步上下文中运行异步代码
            asyncio.run(_synthesize_async())
            return TTSResult(success=True, audio_path=output_path)

        except Exception as e:
            return TTSResult(success=False, error_message=str(e))
