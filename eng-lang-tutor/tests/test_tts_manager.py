#!/usr/bin/env python3
"""
TTS 模块单元测试

测试内容：
- TTSConfig 数据类
- TTSResult 数据类
- TTSManager 初始化和配置
- generate_keypoint_audio 方法的逻辑（不实际调用 API）
"""

import pytest
from pathlib import Path
from datetime import date
import tempfile
import os

from scripts.audio.tts.base import TTSConfig, TTSResult
from scripts.audio.tts.manager import TTSManager, PROVIDERS


class TestTTSConfig:
    """测试 TTSConfig 数据类"""

    def test_default_config(self):
        """测试默认配置"""
        config = TTSConfig()
        assert config.female_voice == ""
        assert config.male_voice == ""
        assert config.speed == 0.9
        assert config.output_format == "mp3"

    def test_custom_config(self):
        """测试自定义配置"""
        config = TTSConfig(
            female_voice="catherine",
            male_voice="henry",
            speed=0.8,
            output_format="wav"
        )
        assert config.female_voice == "catherine"
        assert config.male_voice == "henry"
        assert config.speed == 0.8
        assert config.output_format == "wav"


class TestTTSResult:
    """测试 TTSResult 数据类"""

    def test_success_result(self):
        """测试成功结果"""
        result = TTSResult(
            success=True,
            audio_path=Path("/tmp/test.mp3"),
            duration_seconds=5.0
        )
        assert result.success is True
        assert result.audio_path == Path("/tmp/test.mp3")
        assert result.error_message is None
        assert result.duration_seconds == 5.0

    def test_failure_result(self):
        """测试失败结果"""
        result = TTSResult(
            success=False,
            error_message="Connection failed"
        )
        assert result.success is False
        assert result.audio_path is None
        assert result.error_message == "Connection failed"


class TestTTSManager:
    """测试 TTSManager 类"""

    def test_list_supported_providers(self):
        """测试列出支持的 Providers"""
        providers = TTSManager.list_supported_providers()
        assert "xunfei" in providers
        assert isinstance(providers, list)

    def test_init_with_invalid_provider(self):
        """测试使用无效的 Provider 初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Unknown provider"):
                TTSManager(provider="invalid_provider", data_dir=tmpdir)

    def test_init_xunfei_missing_credentials(self):
        """测试讯飞 Provider 缺少认证信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 清除可能存在的环境变量
            env_backup = {}
            for key in ["XUNFEI_APPID", "XUNFEI_API_KEY", "XUNFEI_API_SECRET"]:
                env_backup[key] = os.environ.pop(key, None)

            try:
                with pytest.raises(ValueError, match="Missing required credential"):
                    TTSManager(provider="xunfei", data_dir=tmpdir)
            finally:
                # 恢复环境变量
                for key, value in env_backup.items():
                    if value is not None:
                        os.environ[key] = value

    def test_init_xunfei_with_credentials(self):
        """测试讯飞 Provider 使用认证信息初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TTSManager(
                provider="xunfei",
                data_dir=tmpdir,
                appid="test_appid",
                api_key="test_api_key",
                api_secret="test_api_secret"
            )
            assert manager.provider_name == "xunfei"
            assert manager.audio_dir == Path(tmpdir) / "audio"
            assert manager.audio_dir.exists()

    def test_init_from_env(self):
        """测试从环境变量初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 设置环境变量
            os.environ["TTS_PROVIDER"] = "xunfei"
            os.environ["XUNFEI_APPID"] = "env_appid"
            os.environ["XUNFEI_API_KEY"] = "env_api_key"
            os.environ["XUNFEI_API_SECRET"] = "env_api_secret"

            try:
                manager = TTSManager.from_env(data_dir=tmpdir)
                assert manager.provider_name == "xunfei"
            finally:
                # 清理环境变量
                for key in ["TTS_PROVIDER", "XUNFEI_APPID", "XUNFEI_API_KEY", "XUNFEI_API_SECRET"]:
                    os.environ.pop(key, None)

    def test_list_voices(self):
        """测试列出支持的语音"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TTSManager(
                provider="xunfei",
                data_dir=tmpdir,
                appid="test_appid",
                api_key="test_api_key",
                api_secret="test_api_secret"
            )
            voices = manager.list_voices()
            assert "catherine" in voices
            assert "henry" in voices
            assert isinstance(voices, dict)


class TestGenerateKeypointAudio:
    """测试 generate_keypoint_audio 方法的逻辑"""

    @pytest.fixture
    def sample_keypoint(self):
        """示例知识点数据"""
        return {
            "date": "2026-02-21",
            "expressions": [
                {"phrase": "touch base", "usage_note": "Brief check-in"},
                {"phrase": "circle back", "usage_note": "Return to later"}
            ],
            "examples": [
                {
                    "situation": "Office check-in",
                    "dialogue": [
                        "A: Hey, just wanted to touch base about the project.",
                        "B: Sure! I'll have an update by EOD."
                    ]
                }
            ]
        }

    def test_generate_keypoint_audio_structure(self, sample_keypoint):
        """测试生成的音频信息结构（不实际调用 API）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TTSManager(
                provider="xunfei",
                data_dir=tmpdir,
                appid="test_appid",
                api_key="test_api_key",
                api_secret="test_api_secret"
            )

            # 注意：这个测试不会实际生成音频，因为需要真实的 API 调用
            # 这里只测试方法的结构和返回格式
            target_date = date(2026, 2, 21)
            audio_info = manager.generate_keypoint_audio(sample_keypoint, target_date)

            # 验证返回结构
            assert "dialogue" in audio_info
            assert "expressions" in audio_info
            assert "generated_at" in audio_info
            assert "provider" in audio_info
            assert audio_info["provider"] == "xunfei"

            # 验证对话音频信息（应该包含错误，因为没有实际 API）
            assert len(audio_info["dialogue"]) == 2  # 2 条对话

            # 验证表达音频信息
            assert len(audio_info["expressions"]) == 2  # 2 个表达

    def test_generate_keypoint_audio_creates_directory(self, sample_keypoint):
        """测试生成音频时创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TTSManager(
                provider="xunfei",
                data_dir=tmpdir,
                appid="test_appid",
                api_key="test_api_key",
                api_secret="test_api_secret"
            )

            target_date = date(2026, 2, 21)
            manager.generate_keypoint_audio(sample_keypoint, target_date)

            # 验证日期目录已创建
            expected_dir = Path(tmpdir) / "audio" / "2026-02-21"
            assert expected_dir.exists()


class TestGetVoice:
    """测试 get_voice 方法"""

    def test_get_female_voice(self):
        """测试获取女声"""
        from scripts.tts.providers.xunfei import XunFeiProvider

        provider = XunFeiProvider(
            appid="test",
            api_key="test",
            api_secret="test"
        )
        assert provider.get_voice("female") == "catherine"

    def test_get_male_voice(self):
        """测试获取男声"""
        from scripts.tts.providers.xunfei import XunFeiProvider

        provider = XunFeiProvider(
            appid="test",
            api_key="test",
            api_secret="test"
        )
        assert provider.get_voice("male") == "henry"

    def test_get_voice_with_custom_config(self):
        """测试使用自定义配置获取语音"""
        from scripts.tts.providers.xunfei import XunFeiProvider

        config = TTSConfig(female_voice="mary", male_voice="john")
        provider = XunFeiProvider(
            config=config,
            appid="test",
            api_key="test",
            api_secret="test"
        )
        assert provider.get_voice("female") == "mary"
        assert provider.get_voice("male") == "john"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
