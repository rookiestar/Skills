"""
Unit tests for cron_push.py
"""

import pytest
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cron_push import CronPusher
from state_manager import StateManager


class TestCronPusher:
    """Tests for CronPusher class."""

    def test_init(self, tmp_path):
        """Test initialization."""
        pusher = CronPusher(data_dir=str(tmp_path))
        assert pusher.state_manager is not None
        assert pusher.today == date.today()

    # === Keypoint Push Tests ===

    def test_push_keypoint_creates_new(self, tmp_path):
        """Test creating new keypoint."""
        pusher = CronPusher(data_dir=str(tmp_path))

        result = pusher.push_keypoint()

        assert result["status"] == "created"
        assert "keypoint" in result
        assert result["keypoint"]["date"] == date.today().isoformat()
        assert result["keypoint"]["needs_generation"] == True

    def test_push_keypoint_exists(self, tmp_path, sample_keypoint):
        """Test that existing keypoint is not overwritten."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_daily_content("keypoint", sample_keypoint, date.today())

        pusher = CronPusher(data_dir=str(tmp_path))
        result = pusher.push_keypoint()

        assert result["status"] == "exists"

    def test_push_keypoint_records_view(self, tmp_path):
        """Test that keypoint push records view in state."""
        pusher = CronPusher(data_dir=str(tmp_path))

        pusher.push_keypoint()

        state = pusher.state_manager.load_state()
        assert pusher.state_manager.has_viewed_keypoint(state, date.today())

    def test_push_keypoint_updates_recent_topics(self, tmp_path):
        """Test that keypoint push updates recent topics."""
        pusher = CronPusher(data_dir=str(tmp_path))

        pusher.push_keypoint()

        state = pusher.state_manager.load_state()
        assert len(state["recent_topics"]) == 1

    # === Quiz Push Tests ===

    def test_push_quiz_creates_new(self, tmp_path):
        """Test creating new quiz."""
        pusher = CronPusher(data_dir=str(tmp_path))

        result = pusher.push_quiz()

        assert result["status"] == "created"
        assert "quiz" in result
        assert result["quiz"]["quiz_date"] == date.today().isoformat()
        assert result["quiz"]["needs_generation"] == True

    def test_push_quiz_exists(self, tmp_path, sample_quiz):
        """Test that existing quiz is not overwritten."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_daily_content("quiz", sample_quiz, date.today())

        pusher = CronPusher(data_dir=str(tmp_path))
        result = pusher.push_quiz()

        assert result["status"] == "exists"

    def test_push_quiz_creates_keypoint_if_missing(self, tmp_path):
        """Test that quiz push creates keypoint if missing."""
        pusher = CronPusher(data_dir=str(tmp_path))

        result = pusher.push_quiz()

        # Should have created both quiz and keypoint
        assert result["status"] == "created"

        keypoint = pusher.state_manager.load_daily_content("keypoint", date.today())
        assert keypoint is not None

    # === Status Tests ===

    def test_get_status(self, tmp_path, sample_state):
        """Test getting status."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_state(sample_state)

        pusher = CronPusher(data_dir=str(tmp_path))
        status = pusher.get_status()

        assert status["date"] == date.today().isoformat()
        assert "initialized" in status
        assert "keypoint_exists" in status
        assert "quiz_exists" in status
        assert "can_take_quiz" in status

    def test_get_status_with_content(self, tmp_path, sample_state, sample_keypoint, sample_quiz):
        """Test getting status with existing content."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_state(sample_state)
        sm.save_daily_content("keypoint", sample_keypoint, date.today())
        sm.save_daily_content("quiz", sample_quiz, date.today())

        pusher = CronPusher(data_dir=str(tmp_path))
        status = pusher.get_status()

        assert status["keypoint_exists"] == True
        assert status["quiz_exists"] == True
