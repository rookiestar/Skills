#!/usr/bin/env python3
"""
讯飞 TTS Provider 实现

讯飞开放平台语音合成服务：
- 每日 500 分钟免费额度
- 国内网络稳定直连
- 支持美式英语发音人（catherine, henry）
- WebSocket 流式接口
"""

import websocket
import datetime
import hashlib
import base64
import hmac
import json
import os
import ssl
import certifi
from pathlib import Path
from typing import Optional, ClassVar, Dict
from urllib.parse import urlencode

from ..base import TTSProvider, TTSConfig, TTSResult


class XunFeiProvider(TTSProvider):
    """
    讯飞开放平台 TTS Provider

    支持的美式英语发音人：
    - catherine: 女声，自然流畅（推荐）
    - henry: 男声，沉稳专业
    - mary: 女声，新闻播报
    - john: 男声，活力阳光

    环境变量配置：
    - XUNFEI_APPID: 应用 ID
    - XUNFEI_API_KEY: API Key
    - XUNFEI_API_SECRET: API Secret
    """

    PROVIDER_NAME: ClassVar[str] = "xunfei"
    DEFAULT_FEMALE_VOICE: ClassVar[str] = "catherine"  # 美式英语女声
    DEFAULT_MALE_VOICE: ClassVar[str] = "henry"        # 美式英语男声
    # 角色音色映射：旁白-女声，对话A-男声，对话B-女声
    DEFAULT_NARRATOR_VOICE: ClassVar[str] = "catherine"  # 旁白 - 女声
    DEFAULT_DIALOGUE_A_VOICE: ClassVar[str] = "henry"    # 对话 A - 男声
    DEFAULT_DIALOGUE_B_VOICE: ClassVar[str] = "catherine"  # 对话 B - 女声

    SUPPORTED_VOICES: ClassVar[Dict[str, str]] = {
        "catherine": "美式英语女声，自然流畅（推荐）",
        "henry": "美式英语男声，沉稳专业",
        "mary": "美式英语女声，新闻播报",
        "john": "美式英语男声，活力阳光",
    }

    def _validate_credentials(self) -> None:
        """
        验证讯飞认证信息

        优先使用传入的 credentials，其次从环境变量读取。

        Raises:
            ValueError: 认证信息缺失
        """
        required = ["appid", "api_key", "api_secret"]
        for key in required:
            if key not in self.credentials:
                # 尝试从环境变量读取
                env_key = f"XUNFEI_{key.upper()}"
                if env_key in os.environ:
                    self.credentials[key] = os.environ[env_key]
                else:
                    raise ValueError(
                        f"Missing required credential: {key}. "
                        f"Set XUNFEI_{key.upper()} environment variable or pass it to constructor."
                    )

    def _create_auth_url(self) -> str:
        """
        生成 WebSocket 鉴权 URL

        Returns:
            带鉴权参数的 WebSocket URL
        """
        date = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        signature_origin = f"host: tts-api.xfyun.cn\ndate: {date}\nGET /v2/tts HTTP/1.1"
        signature_sha = hmac.new(
            self.credentials["api_secret"].encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode()
        authorization = base64.b64encode(
            f'api_key="{self.credentials["api_key"]}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'.encode()
        ).decode()

        params = urlencode({
            "authorization": authorization,
            "date": date,
            "host": "tts-api.xfyun.cn"
        })
        return f'wss://tts-api.xfyun.cn/v2/tts?{params}'

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
        # 讯飞语速范围 0-100，50 为正常
        speed_val = speed or self.config.speed
        speed_int = int(speed_val * 50)

        audio_data = bytearray()
        error_msg = None

        def on_message(ws, message):
            nonlocal error_msg
            try:
                data = json.loads(message)
                if data.get("code") == 0:
                    audio = data.get("data", {}).get("audio", "")
                    status = data.get("data", {}).get("status", 0)
                    if audio:
                        audio_data.extend(base64.b64decode(audio))
                    # status=2 表示合成完成，关闭连接
                    if status == 2:
                        ws.close()
                else:
                    error_msg = f"XunFei API error: code={data.get('code')}, message={data.get('message')}"
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {e}"

        def on_error(ws, error):
            nonlocal error_msg
            error_msg = str(error)

        def on_open(ws):
            request = {
                "common": {"app_id": self.credentials["appid"]},
                "business": {
                    "aue": "lame",      # MP3 格式
                    "sfl": 1,           # 开启流式返回
                    "auf": "audio/L16;rate=16000",
                    "vcn": voice,       # 发音人
                    "speed": speed_int, # 语速
                    "volume": 50,       # 音量
                    "pitch": 50,        # 音调
                },
                "data": {
                    "status": 2,  # 一次性传输
                    "text": str(base64.b64encode(text.encode('utf-8')), "UTF8")
                }
            }
            ws.send(json.dumps(request))

        try:
            ws_url = self._create_auth_url()
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
            )
            ws.on_open = on_open
            # 使用 certifi 提供的 SSL 证书
            ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": certifi.where()}
            )

            if error_msg:
                return TTSResult(success=False, error_message=error_msg)

            if not audio_data:
                return TTSResult(success=False, error_message="No audio data received")

            # 确保输出目录存在
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存音频文件
            with open(output_path, "wb") as f:
                f.write(audio_data)

            return TTSResult(success=True, audio_path=output_path)

        except Exception as e:
            return TTSResult(success=False, error_message=str(e))
