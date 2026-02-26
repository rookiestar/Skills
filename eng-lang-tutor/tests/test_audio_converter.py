#!/usr/bin/env python3
"""
AudioConverter 单元测试

测试内容：
- AudioConverter 初始化
- convert_to_voice() 参数验证
- convert_to_feishu_voice() 参数验证
- ConversionResult 数据类
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


class TestConversionResult:
    """测试 ConversionResult 数据类"""

    def test_success_result(self):
        """测试成功的转换结果"""
        from scripts.audio.converter import ConversionResult

        result = ConversionResult(
            success=True,
            output_path=Path("/tmp/output.opus"),
            duration_seconds=10.5
        )
        assert result.success is True
        assert result.output_path == Path("/tmp/output.opus")
        assert result.duration_seconds == 10.5
        assert result.error_message is None

    def test_failure_result(self):
        """测试失败的转换结果"""
        from scripts.audio.converter import ConversionResult

        result = ConversionResult(
            success=False,
            error_message="ffmpeg not found"
        )
        assert result.success is False
        assert result.output_path is None
        assert result.error_message == "ffmpeg not found"


class TestAudioConverterInit:
    """测试 AudioConverter 初始化"""

    def test_init_with_ffmpeg_path(self):
        """测试使用自定义 ffmpeg 路径初始化"""
        from scripts.audio.converter import AudioConverter

        converter = AudioConverter(ffmpeg_path="/custom/ffmpeg")
        assert converter.ffmpeg_path == "/custom/ffmpeg"

    def test_init_auto_detect_ffmpeg(self):
        """测试自动检测 ffmpeg 路径"""
        from scripts.audio.converter import AudioConverter

        with patch('scripts.audio.converter.get_ffmpeg_path') as mock_get:
            mock_get.return_value = '/usr/bin/ffmpeg'
            converter = AudioConverter()
            assert converter.ffmpeg_path == '/usr/bin/ffmpeg'

    def test_supported_formats(self):
        """测试支持的格式常量"""
        from scripts.audio.converter import AudioConverter

        assert "opus" in AudioConverter.SUPPORTED_FORMATS
        assert "speex" in AudioConverter.SUPPORTED_FORMATS
        assert "aac" in AudioConverter.SUPPORTED_FORMATS
        assert "amr" in AudioConverter.SUPPORTED_FORMATS

    def test_supported_sample_rates(self):
        """测试支持的采样率常量"""
        from scripts.audio.converter import AudioConverter

        assert 8000 in AudioConverter.SUPPORTED_SAMPLE_RATES
        assert 16000 in AudioConverter.SUPPORTED_SAMPLE_RATES


class TestConvertToVoice:
    """测试 convert_to_voice 方法"""

    @pytest.fixture
    def converter(self):
        """创建测试用的 converter"""
        from scripts.audio.converter import AudioConverter
        return AudioConverter(ffmpeg_path="/usr/bin/ffmpeg")

    def test_rejects_unsupported_format(self, converter):
        """测试拒绝不支持的格式"""
        result = converter.convert_to_voice(
            input_path=Path("/tmp/test.mp3"),
            format="invalid_format"
        )

        assert result.success is False
        assert "Unsupported format" in result.error_message

    def test_rejects_unsupported_sample_rate(self, converter):
        """测试拒绝不支持的采样率"""
        result = converter.convert_to_voice(
            input_path=Path("/tmp/test.mp3"),
            format="opus",
            sample_rate=44100  # 不支持的采样率
        )

        assert result.success is False
        assert "Unsupported sample rate" in result.error_message

    def test_rejects_nonexistent_file(self, converter):
        """测试拒绝不存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.mp3"

            result = converter.convert_to_voice(
                input_path=nonexistent,
                format="opus"
            )

            assert result.success is False
            assert "not found" in result.error_message

    def test_successful_conversion(self, converter):
        """测试成功转换"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个模拟的输入文件
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = "  Duration: 00:00:05.00"

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = converter.convert_to_voice(
                    input_path=input_file,
                    format="opus"
                )

                assert result.success is True
                assert result.output_path is not None

    def test_handles_ffmpeg_error(self, converter):
        """测试处理 ffmpeg 错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: Invalid codec"

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = converter.convert_to_voice(
                    input_path=input_file,
                    format="opus"
                )

                assert result.success is False
                assert "ffmpeg error" in result.error_message

    def test_handles_timeout(self, converter):
        """测试处理超时"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = TimeoutError()

                result = converter.convert_to_voice(
                    input_path=input_file,
                    format="opus"
                )

                assert result.success is False

    def test_generates_output_path_from_input(self, converter):
        """测试从输入文件生成输出路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = converter.convert_to_voice(
                    input_path=input_file,
                    format="opus"
                )

                # 输出路径应该是 test.opus
                assert result.output_path.suffix == ".opus"


class TestConvertToFeishuVoice:
    """测试 convert_to_feishu_voice 方法"""

    @pytest.fixture
    def converter(self):
        """创建测试用的 converter"""
        from scripts.audio.converter import AudioConverter
        return AudioConverter(ffmpeg_path="/usr/bin/ffmpeg")

    def test_rejects_nonexistent_file(self, converter):
        """测试拒绝不存在的文件"""
        result = converter.convert_to_feishu_voice(
            input_path=Path("/tmp/nonexistent.mp3")
        )

        assert result.success is False
        assert "not found" in result.error_message

    def test_successful_conversion(self, converter):
        """测试成功转换为飞书格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = "  Duration: 00:00:03.50"

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = converter.convert_to_feishu_voice(
                    input_path=input_file
                )

                assert result.success is True
                # 飞书格式输出 .m4a
                assert result.output_path.suffix == ".m4a"


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_convert_mp3_to_opus(self):
        """测试 convert_mp3_to_opus 便捷函数"""
        from scripts.audio.converter import convert_mp3_to_opus

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = convert_mp3_to_opus(input_file)

                assert result.success is True

    def test_convert_to_feishu_voice_func(self):
        """测试 convert_to_feishu_voice 便捷函数"""
        from scripts.audio.converter import convert_to_feishu_voice as convert_func

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.mp3"
            input_file.write_bytes(b"fake audio data")

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                result = convert_func(input_file)

                assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
