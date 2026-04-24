#!/usr/bin/env python3
"""
Audio utilities 单元测试

测试内容：
- get_ffmpeg_path() 函数
- get_audio_duration() 函数
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import tempfile


class TestGetFfmpegPath:
    """测试 get_ffmpeg_path 函数"""

    def test_returns_path_when_ffmpeg_exists(self):
        """测试 ffmpeg 存在时返回路径"""
        from scripts.audio.utils import get_ffmpeg_path

        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/local/bin/ffmpeg'
            result = get_ffmpeg_path()
            assert result == '/usr/local/bin/ffmpeg'

    def test_raises_error_when_ffmpeg_not_found(self):
        """测试 ffmpeg 不存在时抛出错误"""
        from scripts.audio.utils import get_ffmpeg_path

        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                get_ffmpeg_path()


class TestGetAudioDuration:
    """测试 get_audio_duration 函数"""

    def test_parses_duration_correctly(self):
        """测试正确解析音频时长"""
        from scripts.audio.utils import get_audio_duration

        mock_result = MagicMock()
        mock_result.stderr = "  Duration: 00:01:23.45, bitrate: 128 kbps"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            with patch('shutil.which') as mock_which:
                mock_which.return_value = '/usr/bin/ffmpeg'

                result = get_audio_duration(
                    Path("/tmp/test.mp3"),
                    ffmpeg_path='/usr/bin/ffmpeg'
                )

                # 1分23.45秒 = 60 + 23.45 = 83.45秒
                assert result == 83.45

    def test_parses_hours_correctly(self):
        """测试正确解析小时"""
        from scripts.audio.utils import get_audio_duration

        mock_result = MagicMock()
        mock_result.stderr = "  Duration: 01:30:00.00, bitrate: 128 kbps"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            with patch('shutil.which') as mock_which:
                mock_which.return_value = '/usr/bin/ffmpeg'

                result = get_audio_duration(
                    Path("/tmp/test.mp3"),
                    ffmpeg_path='/usr/bin/ffmpeg'
                )

                # 1小时30分 = 3600 + 1800 = 5400秒
                assert result == 5400.0

    def test_returns_zero_on_parse_failure(self):
        """测试解析失败时返回 0.0"""
        from scripts.audio.utils import get_audio_duration

        mock_result = MagicMock()
        mock_result.stderr = "No duration info"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            with patch('shutil.which') as mock_which:
                mock_which.return_value = '/usr/bin/ffmpeg'

                result = get_audio_duration(
                    Path("/tmp/test.mp3"),
                    ffmpeg_path='/usr/bin/ffmpeg'
                )

                assert result == 0.0

    def test_auto_detects_ffmpeg_path(self):
        """测试自动检测 ffmpeg 路径"""
        from scripts.audio.utils import get_audio_duration

        mock_result = MagicMock()
        mock_result.stderr = "  Duration: 00:00:05.00"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            with patch('shutil.which') as mock_which:
                mock_which.return_value = '/usr/bin/ffmpeg'

                result = get_audio_duration(Path("/tmp/test.mp3"))

                # 应该自动调用 get_ffmpeg_path
                assert result == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
