#!/usr/bin/env python3
"""
飞书语音消息发送模块

将 TTS 生成的音频转换为飞书语音格式并发送。

使用示例：
    from scripts.feishu_voice import FeishuVoiceSender

    sender = FeishuVoiceSender(app_id="xxx", app_secret="xxx")

    # 发送单条语音
    await sender.send_voice(
        receive_id="ou_xxx",
        text="Hello, nice to meet you!"
    )

    # 发送知识点音频
    await sender.send_keypoint_voices(
        receive_id="ou_xxx",
        keypoint=keypoint,
        audio_info=audio_info
    )
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .converter import AudioConverter, ConversionResult


@dataclass
class VoiceSendResult:
    """语音发送结果"""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None


class FeishuVoiceSender:
    """
    飞书语音消息发送器

    工作流程：
    1. TTS 生成 MP3 音频
    2. 转换为 Opus 格式（飞书推荐）
    3. 上传到飞书素材库
    4. 发送语音消息
    """

    FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        tenant_key: Optional[str] = None,
        audio_dir: Optional[Path] = None
    ):
        """
        初始化飞书语音发送器

        Args:
            app_id: 飞书应用 ID（可从环境变量 FEISHU_APP_ID 读取）
            app_secret: 飞书应用密钥（可从环境变量 FEISHU_APP_SECRET 读取）
            tenant_key: 租户密钥（自建应用无需）
            audio_dir: 音频缓存目录
        """
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self.tenant_key = tenant_key

        if not self.app_id or not self.app_secret:
            raise ValueError(
                "Missing Feishu credentials. Set FEISHU_APP_ID and FEISHU_APP_SECRET "
                "environment variables or pass them to constructor."
            )

        self.audio_dir = audio_dir or Path(
            os.getenv("OPENCLAW_STATE_DIR", "~/.openclaw/state/eng-lang-tutor")
        ).expanduser() / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self.converter = AudioConverter()
        self._access_token: Optional[str] = None
        self._token_expires: float = 0

    async def _get_access_token(self) -> str:
        """获取飞书访问令牌"""
        import time

        # 检查缓存
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        url = f"{self.FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                result = await resp.json()

                if result.get("code") != 0:
                    raise RuntimeError(f"Failed to get access token: {result}")

                self._access_token = result["tenant_access_token"]
                self._token_expires = time.time() + result.get("expire", 7200) - 300

                return self._access_token

    async def _upload_file(self, file_path: Path, file_type: str = "opus") -> str:
        """
        上传文件到飞书素材库

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            file_key
        """
        token = await self._get_access_token()

        url = f"{self.FEISHU_API_BASE}/im/v1/files"
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("file_type", file_type)
                form.add_field("file_name", file_path.name)
                form.add_field("file", f, filename=file_path.name)

                async with session.post(url, headers=headers, data=form) as resp:
                    result = await resp.json()

                    if result.get("code") != 0:
                        raise RuntimeError(f"Failed to upload file: {result}")

                    return result["data"]["file_key"]

    async def _send_file_message(
        self,
        receive_id: str,
        file_key: str,
        receive_id_type: str = "open_id"
    ) -> str:
        """
        发送文件消息

        Args:
            receive_id: 接收者 ID
            file_key: 文件 key
            receive_id_type: 接收者 ID 类型

        Returns:
            message_id
        """
        token = await self._get_access_token()

        url = f"{self.FEISHU_API_BASE}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        params = {
            "receive_id_type": receive_id_type
        }
        data = {
            "receive_id": receive_id,
            "msg_type": "file",
            "content": f'{{"file_key": "{file_key}"}}'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, params=params, json=data) as resp:
                result = await resp.json()

                if result.get("code") != 0:
                    raise RuntimeError(f"Failed to send message: {result}")

                return result["data"]["message_id"]

    async def send_voice(
        self,
        receive_id: str,
        audio_path: Path,
        receive_id_type: str = "open_id",
        auto_convert: bool = True,
        delete_after_send: bool = False
    ) -> VoiceSendResult:
        """
        发送语音消息

        Args:
            receive_id: 接收者 ID（open_id / user_id / union_id）
            audio_path: 音频文件路径（MP3 或 Opus）
            receive_id_type: 接收者 ID 类型
            auto_convert: 是否自动转换为 Opus 格式
            delete_after_send: 发送后是否删除临时文件

        Returns:
            VoiceSendResult
        """
        audio_path = Path(audio_path)
        temp_file = None

        try:
            # 如果是 MP3，转换为 Opus
            if auto_convert and audio_path.suffix.lower() == ".mp3":
                opus_path = audio_path.with_suffix(".opus")
                result = self.converter.convert_to_voice(
                    input_path=audio_path,
                    output_path=opus_path,
                    format="opus",
                    sample_rate=16000
                )
                if not result.success:
                    return VoiceSendResult(
                        success=False,
                        error_message=f"Audio conversion failed: {result.error_message}"
                    )
                audio_path = opus_path
                temp_file = opus_path if delete_after_send else None

            # 上传文件
            file_key = await self._upload_file(audio_path)

            # 发送消息
            message_id = await self._send_file_message(
                receive_id=receive_id,
                file_key=file_key,
                receive_id_type=receive_id_type
            )

            return VoiceSendResult(
                success=True,
                message_id=message_id
            )

        except Exception as e:
            return VoiceSendResult(
                success=False,
                error_message=str(e)
            )
        finally:
            # 清理临时文件
            if temp_file and temp_file.exists():
                temp_file.unlink()

    async def send_voice_from_text(
        self,
        receive_id: str,
        text: str,
        voice: str = "catherine",
        speed: float = 0.9,
        receive_id_type: str = "open_id"
    ) -> VoiceSendResult:
        """
        从文本直接生成并发送语音

        Args:
            receive_id: 接收者 ID
            text: 要转换的文本
            voice: 音色
            speed: 语速
            receive_id_type: 接收者 ID 类型

        Returns:
            VoiceSendResult
        """
        from .tts import TTSManager

        try:
            # 生成 TTS 音频
            manager = TTSManager.from_env()
            output_path = self.audio_dir / f"temp_{hash(text)}.mp3"

            result = manager.synthesize(
                text=text,
                output_path=output_path,
                voice=voice,
                speed=speed
            )

            if not result.success:
                return VoiceSendResult(
                    success=False,
                    error_message=f"TTS failed: {result.error_message}"
                )

            # 发送语音
            return await self.send_voice(
                receive_id=receive_id,
                audio_path=output_path,
                receive_id_type=receive_id_type,
                auto_convert=True,
                delete_after_send=True
            )

        except Exception as e:
            return VoiceSendResult(
                success=False,
                error_message=str(e)
            )

    async def send_keypoint_voices(
        self,
        receive_id: str,
        keypoint: Dict[str, Any],
        audio_info: Dict[str, Any],
        receive_id_type: str = "open_id",
        include_dialogue: bool = True,
        include_expressions: bool = True
    ) -> List[VoiceSendResult]:
        """
        发送知识点的所有语音

        Args:
            receive_id: 接收者 ID
            keypoint: 知识点数据
            audio_info: TTS 生成的音频信息
            receive_id_type: 接收者 ID 类型
            include_dialogue: 是否发送对话音频
            include_expressions: 是否发送表达音频

        Returns:
            发送结果列表
        """
        results = []
        date_str = audio_info.get("generated_at", "")[:10]  # YYYY-MM-DD

        # 发送对话音频
        if include_dialogue:
            for item in audio_info.get("dialogue", []):
                if "error" in item:
                    results.append(VoiceSendResult(
                        success=False,
                        error_message=f"Dialogue generation failed: {item['error']}"
                    ))
                    continue

                audio_url = item.get("audio_url", "")
                if not audio_url:
                    continue

                # 解析路径：audio/YYYY-MM-DD/filename.opus
                parts = audio_url.split("/")
                audio_path = self.audio_dir / parts[1] / parts[2]

                if not audio_path.exists():
                    # 尝试 MP3 扩展名
                    audio_path = audio_path.with_suffix(".mp3")

                if audio_path.exists():
                    speaker = item.get("speaker", "")
                    text = item.get("text", "")

                    result = await self.send_voice(
                        receive_id=receive_id,
                        audio_path=audio_path,
                        receive_id_type=receive_id_type,
                        auto_convert=True
                    )
                    results.append(result)

        # 发送表达音频
        if include_expressions:
            for item in audio_info.get("expressions", []):
                if "error" in item:
                    results.append(VoiceSendResult(
                        success=False,
                        error_message=f"Expression generation failed: {item['error']}"
                    ))
                    continue

                audio_url = item.get("audio_url", "")
                if not audio_url:
                    continue

                parts = audio_url.split("/")
                audio_path = self.audio_dir / parts[1] / parts[2]

                if not audio_path.exists():
                    audio_path = audio_path.with_suffix(".mp3")

                if audio_path.exists():
                    result = await self.send_voice(
                        receive_id=receive_id,
                        audio_path=audio_path,
                        receive_id_type=receive_id_type,
                        auto_convert=True
                    )
                    results.append(result)

        return results
