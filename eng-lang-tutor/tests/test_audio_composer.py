#!/usr/bin/env python3
"""
AudioComposer 模块单元测试和集成测试

测试内容：
- 音色选择逻辑（自动适配不同 TTS provider）
- 音频合成流程（mock TTS）
- 错误处理
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

from scripts.audio.composer import AudioComposer, CompositionResult
from scripts.audio.tts.base import TTSConfig, TTSResult


class MockTTSProvider:
    """Mock TTS Provider 用于测试"""

    PROVIDER_NAME = "mock"
    DEFAULT_FEMALE_VOICE = "mock_female"
    DEFAULT_MALE_VOICE = "mock_male"
    DEFAULT_NARRATOR_VOICE = "mock_narrator"
    DEFAULT_DIALOGUE_A_VOICE = "mock_dialogue_a"
    DEFAULT_DIALOGUE_B_VOICE = "mock_dialogue_b"

    def __init__(self, config=None):
        self.config = config or TTSConfig()

    def get_voice_by_role(self, role: str) -> str:
        """模拟 get_voice_by_role 方法"""
        role_map = {
            "narrator": self.DEFAULT_NARRATOR_VOICE,
            "dialogue_a": self.DEFAULT_DIALOGUE_A_VOICE,
            "dialogue_b": self.DEFAULT_DIALOGUE_B_VOICE,
        }
        return role_map.get(role, self.DEFAULT_FEMALE_VOICE)

    def synthesize(self, text, output_path, voice=None, speed=None):
        """模拟 synthesize 方法 - 创建空文件"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock audio data")
        return TTSResult(success=True, audio_path=output_path)


class MockEdgeTTSProvider:
    """Mock Edge-TTS Provider"""

    PROVIDER_NAME = "edge-tts"
    DEFAULT_NARRATOR_VOICE = "en-US-JennyNeural"
    DEFAULT_DIALOGUE_A_VOICE = "en-US-EricNeural"
    DEFAULT_DIALOGUE_B_VOICE = "en-US-JennyNeural"

    def __init__(self, config=None):
        self.config = config or TTSConfig()

    def get_voice_by_role(self, role: str) -> str:
        role_map = {
            "narrator": self.DEFAULT_NARRATOR_VOICE,
            "dialogue_a": self.DEFAULT_DIALOGUE_A_VOICE,
            "dialogue_b": self.DEFAULT_DIALOGUE_B_VOICE,
        }
        return role_map.get(role, "en-US-JennyNeural")

    def synthesize(self, text, output_path, voice=None, speed=None):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"edge-tts audio data")
        return TTSResult(success=True, audio_path=output_path)


class MockXunFeiProvider:
    """Mock XunFei Provider"""

    PROVIDER_NAME = "xunfei"
    DEFAULT_NARRATOR_VOICE = "catherine"
    DEFAULT_DIALOGUE_A_VOICE = "henry"
    DEFAULT_DIALOGUE_B_VOICE = "catherine"

    def __init__(self, config=None):
        self.config = config or TTSConfig()

    def get_voice_by_role(self, role: str) -> str:
        role_map = {
            "narrator": self.DEFAULT_NARRATOR_VOICE,
            "dialogue_a": self.DEFAULT_DIALOGUE_A_VOICE,
            "dialogue_b": self.DEFAULT_DIALOGUE_B_VOICE,
        }
        return role_map.get(role, "catherine")

    def synthesize(self, text, output_path, voice=None, speed=None):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"xunfei audio data")
        return TTSResult(success=True, audio_path=output_path)


class TestVoiceSelection:
    """测试音色选择逻辑"""

    def test_uses_tts_provider_default_voices_when_none_provided(self):
        """测试未指定音色时使用 TTS provider 的默认值"""
        mock_tts = MockTTSProvider()
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        # 模拟 compose_keypoint_audio 中的音色选择逻辑
        narrator_voice = None
        voice_a = None
        voice_b = None

        # 这是 composer.py 中的逻辑
        actual_narrator = narrator_voice or mock_tts.get_voice_by_role("narrator")
        actual_voice_a = voice_a or mock_tts.get_voice_by_role("dialogue_a")
        actual_voice_b = voice_b or mock_tts.get_voice_by_role("dialogue_b")

        assert actual_narrator == "mock_narrator"
        assert actual_voice_a == "mock_dialogue_a"
        assert actual_voice_b == "mock_dialogue_b"

    def test_uses_custom_voices_when_provided(self):
        """测试指定音色时使用自定义值"""
        mock_tts = MockTTSProvider()
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        narrator_voice = "custom_narrator"
        voice_a = "custom_voice_a"
        voice_b = "custom_voice_b"

        actual_narrator = narrator_voice or mock_tts.get_voice_by_role("narrator")
        actual_voice_a = voice_a or mock_tts.get_voice_by_role("dialogue_a")
        actual_voice_b = voice_b or mock_tts.get_voice_by_role("dialogue_b")

        assert actual_narrator == "custom_narrator"
        assert actual_voice_a == "custom_voice_a"
        assert actual_voice_b == "custom_voice_b"

    def test_edge_tts_provider_voices(self):
        """测试 Edge-TTS provider 的默认音色"""
        mock_tts = MockEdgeTTSProvider()

        narrator = mock_tts.get_voice_by_role("narrator")
        voice_a = mock_tts.get_voice_by_role("dialogue_a")
        voice_b = mock_tts.get_voice_by_role("dialogue_b")

        assert narrator == "en-US-JennyNeural"
        assert voice_a == "en-US-EricNeural"
        assert voice_b == "en-US-JennyNeural"

    def test_xunfei_provider_voices(self):
        """测试讯飞 provider 的默认音色"""
        mock_tts = MockXunFeiProvider()

        narrator = mock_tts.get_voice_by_role("narrator")
        voice_a = mock_tts.get_voice_by_role("dialogue_a")
        voice_b = mock_tts.get_voice_by_role("dialogue_b")

        assert narrator == "catherine"
        assert voice_a == "henry"
        assert voice_b == "catherine"


class TestCompositionResult:
    """测试 CompositionResult 数据类"""

    def test_success_result(self):
        """测试成功的合成结果"""
        result = CompositionResult(
            success=True,
            audio_path=Path("/tmp/test.mp3"),
            duration_seconds=10.5
        )
        assert result.success is True
        assert result.audio_path == Path("/tmp/test.mp3")
        assert result.duration_seconds == 10.5
        assert result.error_message is None

    def test_failure_result(self):
        """测试失败的合成结果"""
        result = CompositionResult(
            success=False,
            error_message="TTS synthesis failed"
        )
        assert result.success is False
        assert result.audio_path is None
        assert result.error_message == "TTS synthesis failed"


class TestComposeKeypointAudio:
    """测试 compose_keypoint_audio 方法"""

    @pytest.fixture
    def sample_keypoint(self):
        """示例知识点数据"""
        return {
            "date": "2026-02-27",
            "expressions": [
                {"phrase": "touch base", "usage_note": "Brief check-in"},
                {"phrase": "circle back", "usage_note": "Return to later"}
            ],
            "alternatives": [
                "Let's catch up",
                "Let's sync up"
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

    @pytest.fixture
    def mock_tts(self):
        """Mock TTS provider"""
        return MockTTSProvider()

    def test_compose_with_empty_keypoint(self, mock_tts):
        """测试空知识点返回错误"""
        with patch.object(AudioComposer, '_generate_silence') as mock_silence:
            mock_silence.return_value = Path("/tmp/silence.mp3")

            composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")
            result = composer.compose_keypoint_audio(
                keypoint={},
                output_path=Path("/tmp/output.mp3")
            )

            assert result.success is False
            assert "No audio content" in result.error_message

    def test_compose_uses_provider_voices(self, mock_tts, sample_keypoint):
        """测试合成时使用 provider 的默认音色"""
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        # 使用 mock 替换实际的音频生成
        with patch.object(composer, '_synthesize_segment') as mock_synthesize, \
             patch.object(composer, '_generate_silence') as mock_silence, \
             patch.object(composer, '_concatenate_segments') as mock_concat:

            mock_synthesize.return_value = Path("/tmp/segment.mp3")
            mock_silence.return_value = Path("/tmp/silence.mp3")
            mock_concat.return_value = Path("/tmp/output.mp3")

            result = composer.compose_keypoint_audio(
                keypoint=sample_keypoint,
                output_path=Path("/tmp/output.mp3")
            )

            # 验证 _synthesize_segment 被调用时使用了正确的音色
            calls = mock_synthesize.call_args_list

            # 检查是否有使用 mock_narrator 的调用（旁白）
            narrator_calls = [c for c in calls if c.kwargs.get('voice') == 'mock_narrator']
            assert len(narrator_calls) > 0, "应该使用 mock_narrator 音色"

    def test_compose_with_custom_voices(self, mock_tts, sample_keypoint):
        """测试使用自定义音色合成"""
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        with patch.object(composer, '_synthesize_segment') as mock_synthesize, \
             patch.object(composer, '_generate_silence') as mock_silence, \
             patch.object(composer, '_concatenate_segments') as mock_concat:

            mock_synthesize.return_value = Path("/tmp/segment.mp3")
            mock_silence.return_value = Path("/tmp/silence.mp3")
            mock_concat.return_value = Path("/tmp/output.mp3")

            result = composer.compose_keypoint_audio(
                keypoint=sample_keypoint,
                output_path=Path("/tmp/output.mp3"),
                narrator_voice="custom_narrator",
                voice_a="custom_a",
                voice_b="custom_b"
            )

            # 验证使用了自定义音色
            calls = mock_synthesize.call_args_list
            narrator_calls = [c for c in calls if c.kwargs.get('voice') == 'custom_narrator']
            assert len(narrator_calls) > 0, "应该使用自定义的 custom_narrator 音色"


class TestEdgeTTSIntegration:
    """Edge-TTS 集成测试"""

    def test_edge_tts_voice_selection(self):
        """测试 Edge-TTS 的音色选择"""
        mock_tts = MockEdgeTTSProvider()
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        sample_keypoint = {
            "expressions": [{"phrase": "test"}],
            "examples": [{
                "dialogue": ["A: Hello", "B: Hi there"]
            }]
        }

        with patch.object(composer, '_synthesize_segment') as mock_synthesize, \
             patch.object(composer, '_generate_silence') as mock_silence, \
             patch.object(composer, '_concatenate_segments') as mock_concat:

            mock_synthesize.return_value = Path("/tmp/segment.mp3")
            mock_silence.return_value = Path("/tmp/silence.mp3")
            mock_concat.return_value = Path("/tmp/output.mp3")

            composer.compose_keypoint_audio(
                keypoint=sample_keypoint,
                output_path=Path("/tmp/output.mp3")
            )

            calls = mock_synthesize.call_args_list
            voices_used = [c.kwargs.get('voice') for c in calls]

            # 验证使用了 Edge-TTS 的音色
            assert "en-US-JennyNeural" in voices_used, "应该使用 Edge-TTS 的 JennyNeural"
            assert "en-US-EricNeural" in voices_used, "应该使用 Edge-TTS 的 EricNeural"


class TestXunFeiIntegration:
    """讯飞集成测试"""

    def test_xunfei_voice_selection(self):
        """测试讯飞的音色选择"""
        mock_tts = MockXunFeiProvider()
        composer = AudioComposer(tts_manager=mock_tts, ffmpeg_path="ffmpeg")

        sample_keypoint = {
            "expressions": [{"phrase": "test"}],
            "examples": [{
                "dialogue": ["A: Hello", "B: Hi there"]
            }]
        }

        with patch.object(composer, '_synthesize_segment') as mock_synthesize, \
             patch.object(composer, '_generate_silence') as mock_silence, \
             patch.object(composer, '_concatenate_segments') as mock_concat:

            mock_synthesize.return_value = Path("/tmp/segment.mp3")
            mock_silence.return_value = Path("/tmp/silence.mp3")
            mock_concat.return_value = Path("/tmp/output.mp3")

            composer.compose_keypoint_audio(
                keypoint=sample_keypoint,
                output_path=Path("/tmp/output.mp3")
            )

            calls = mock_synthesize.call_args_list
            voices_used = [c.kwargs.get('voice') for c in calls]

            # 验证使用了讯飞的音色
            assert "catherine" in voices_used, "应该使用讯飞的 catherine"
            assert "henry" in voices_used, "应该使用讯飞的 henry"


class TestRealProviders:
    """测试真实的 Provider 类（不调用 API）"""

    def test_edge_tts_provider_get_voice_by_role(self):
        """测试 EdgeTTSProvider 的 get_voice_by_role 方法"""
        from scripts.audio.tts.providers.edge import EdgeTTSProvider

        # EdgeTTSProvider 不需要认证
        provider = EdgeTTSProvider()

        assert provider.get_voice_by_role("narrator") == "en-US-JennyNeural"
        assert provider.get_voice_by_role("dialogue_a") == "en-US-EricNeural"
        assert provider.get_voice_by_role("dialogue_b") == "en-US-JennyNeural"

    def test_xunfei_provider_get_voice_by_role(self):
        """测试 XunFeiProvider 的 get_voice_by_role 方法"""
        from scripts.audio.tts.providers.xunfei import XunFeiProvider

        provider = XunFeiProvider(
            appid="test",
            api_key="test",
            api_secret="test"
        )

        assert provider.get_voice_by_role("narrator") == "catherine"
        assert provider.get_voice_by_role("dialogue_a") == "henry"
        assert provider.get_voice_by_role("dialogue_b") == "catherine"

    def test_edge_tts_provider_get_default_voices(self):
        """测试 EdgeTTSProvider 的 get_default_voices 类方法"""
        from scripts.audio.tts.providers.edge import EdgeTTSProvider

        defaults = EdgeTTSProvider.get_default_voices()

        assert defaults["narrator"] == "en-US-JennyNeural"
        assert defaults["dialogue_a"] == "en-US-EricNeural"
        assert defaults["dialogue_b"] == "en-US-JennyNeural"

    def test_xunfei_provider_get_default_voices(self):
        """测试 XunFeiProvider 的 get_default_voices 类方法"""
        from scripts.audio.tts.providers.xunfei import XunFeiProvider

        defaults = XunFeiProvider.get_default_voices()

        assert defaults["narrator"] == "catherine"
        assert defaults["dialogue_a"] == "henry"
        assert defaults["dialogue_b"] == "catherine"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
