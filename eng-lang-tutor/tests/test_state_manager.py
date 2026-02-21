"""
Unit tests for state_manager.py
"""

import pytest
import json
import tempfile
import os
from datetime import date, timedelta
from pathlib import Path

from state_manager import StateManager


class TestStateManager:
    """Tests for StateManager class."""

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates required directories."""
        sm = StateManager(data_dir=str(tmp_path))

        assert sm.data_dir.exists()
        assert sm.logs_dir.exists()
        assert sm.daily_dir.exists()

    def test_load_state_default(self, tmp_path):
        """Test loading state when file doesn't exist returns defaults."""
        sm = StateManager(data_dir=str(tmp_path))
        state = sm.load_state()

        assert state["version"] == 2
        assert state["initialized"] == False
        assert state["user"]["xp"] == 0
        assert state["user"]["level"] == 1
        assert state["preferences"]["cefr_level"] == "B1"
        assert "completion_status" in state
        assert "schedule" in state

    def test_save_and_load_state(self, tmp_path, sample_state):
        """Test saving and loading state."""
        sm = StateManager(data_dir=str(tmp_path))

        # Modify and save
        sample_state["user"]["xp"] = 100
        sample_state["user"]["level"] = 3
        sm.save_state(sample_state)

        # Load and verify
        loaded = sm.load_state()
        assert loaded["user"]["xp"] == 100
        assert loaded["user"]["level"] == 3

    def test_save_state_atomic_write(self, tmp_path, sample_state):
        """Test that save uses atomic write (temp file then rename)."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_state(sample_state)

        # Temp file should not exist after save
        temp_file = sm.state_file.with_suffix('.tmp')
        assert not temp_file.exists()

        # State file should exist
        assert sm.state_file.exists()

    def test_append_event(self, tmp_path):
        """Test appending events to log file."""
        sm = StateManager(data_dir=str(tmp_path))

        sm.append_event("test_event", {"key": "value"})
        sm.append_event("another_event", {"data": 123})

        # Check log file exists and contains events
        today = date.today()
        log_file = sm.logs_dir / f"events_{today.strftime('%Y-%m')}.jsonl"
        assert log_file.exists()

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        event1 = json.loads(lines[0])
        assert event1["type"] == "test_event"
        assert event1["data"]["key"] == "value"

    def test_get_today_dir(self, tmp_path):
        """Test getting today's directory."""
        sm = StateManager(data_dir=str(tmp_path))
        today_dir = sm.get_today_dir()

        assert today_dir.exists()
        assert today_dir.name == date.today().strftime('%Y-%m-%d')

    def test_get_daily_dir(self, tmp_path):
        """Test getting directory for specific date."""
        sm = StateManager(data_dir=str(tmp_path))
        target = date(2026, 2, 20)
        daily_dir = sm.get_daily_dir(target)

        assert daily_dir.name == "2026-02-20"

    def test_save_and_load_daily_content(self, tmp_path, sample_keypoint):
        """Test saving and loading daily content."""
        sm = StateManager(data_dir=str(tmp_path))
        target_date = date(2026, 2, 20)

        # Save
        saved_path = sm.save_daily_content("keypoint", sample_keypoint, target_date)
        assert saved_path.exists()

        # Load
        loaded = sm.load_daily_content("keypoint", target_date)
        assert loaded["topic_fingerprint"] == "workplace_touch_base"
        assert loaded["category"] == "oral"

    def test_load_daily_content_not_found(self, tmp_path):
        """Test loading non-existent daily content returns None."""
        sm = StateManager(data_dir=str(tmp_path))
        result = sm.load_daily_content("nonexistent", date(2020, 1, 1))
        assert result is None

    def test_get_recent_daily_content(self, tmp_path, sample_keypoint):
        """Test getting recent daily content for deduplication."""
        sm = StateManager(data_dir=str(tmp_path))

        # Create content for past 3 days
        for i in range(3):
            target = date.today() - timedelta(days=i)
            kp = sample_keypoint.copy()
            kp["topic_fingerprint"] = f"topic_{i}"
            sm.save_daily_content("keypoint", kp, target)

        # Get recent content
        recent = sm.get_recent_daily_content(days=3)
        assert len(recent) == 3

    def test_get_recent_topics(self, tmp_path, sample_keypoint):
        """Test getting recent topic fingerprints."""
        sm = StateManager(data_dir=str(tmp_path))

        for i in range(3):
            target = date.today() - timedelta(days=i)
            kp = sample_keypoint.copy()
            kp["topic_fingerprint"] = f"topic_{i}"
            sm.save_daily_content("keypoint", kp, target)

        topics = sm.get_recent_topics(days=3)
        assert "topic_0" in topics
        assert "topic_1" in topics
        assert "topic_2" in topics

    def test_add_to_error_notebook(self, tmp_path, sample_state):
        """Test adding errors to notebook."""
        sm = StateManager(data_dir=str(tmp_path))

        error = {
            "question": "What does 'touch base' mean?",
            "user_answer": "A",
            "correct_answer": "B",
            "explanation": "Touch base means quick check-in"
        }

        updated = sm.add_to_error_notebook(sample_state, error)

        assert len(updated["error_notebook"]) == 1
        assert updated["error_notebook"][0]["question"] == "What does 'touch base' mean?"
        assert updated["error_notebook"][0]["reviewed"] == False
        assert "date" in updated["error_notebook"][0]

    def test_clear_reviewed_errors(self, tmp_path, sample_state):
        """Test clearing reviewed errors."""
        sm = StateManager(data_dir=str(tmp_path))

        # Add reviewed and unreviewed errors
        sample_state["error_notebook"] = [
            {"question": "Q1", "reviewed": True},
            {"question": "Q2", "reviewed": False},
            {"question": "Q3", "reviewed": True}
        ]

        updated = sm.clear_reviewed_errors(sample_state)

        assert len(updated["error_notebook"]) == 1
        assert updated["error_notebook"][0]["question"] == "Q2"

    def test_backup_state(self, tmp_path, sample_state):
        """Test creating backup."""
        sm = StateManager(data_dir=str(tmp_path))
        sm.save_state(sample_state)

        backup_path = sm.backup_state(backup_dir=str(tmp_path / "backups"))
        assert backup_path.exists()
        assert "state_backup_" in backup_path.name

    def test_restore_from_backup(self, tmp_path, sample_state):
        """Test restoring from backup."""
        sm = StateManager(data_dir=str(tmp_path))

        # Save original state
        sample_state["user"]["xp"] = 100
        sm.save_state(sample_state)

        # Create backup
        backup_path = sm.backup_state(backup_dir=str(tmp_path / "backups"))

        # Modify state
        sample_state["user"]["xp"] = 200
        sm.save_state(sample_state)

        # Restore from backup
        success = sm.restore_from_backup(backup_path)
        assert success

        loaded = sm.load_state()
        assert loaded["user"]["xp"] == 100

    def test_merge_with_defaults(self, tmp_path):
        """Test merging partial state with defaults."""
        sm = StateManager(data_dir=str(tmp_path))

        # Create partial state (missing some fields)
        partial_state = {
            "user": {"xp": 50},
            "progress": {"total_quizzes": 5}
        }

        sm.save_state(partial_state)
        loaded = sm.load_state()

        # Should have defaults merged in
        assert loaded["user"]["xp"] == 50
        assert loaded["user"]["level"] == 1  # default
        assert loaded["preferences"]["cefr_level"] == "B1"  # default
        assert loaded["progress"]["total_quizzes"] == 5


class TestCompletionTracking:
    """Tests for quiz completion tracking."""

    def test_can_take_quiz_initial(self, tmp_path, sample_state):
        """Test that quiz can be taken initially."""
        sm = StateManager(data_dir=str(tmp_path))

        assert sm.can_take_quiz(sample_state) is True

    def test_can_take_quiz_after_completion(self, tmp_path, sample_state):
        """Test that quiz cannot be taken after completion today."""
        sm = StateManager(data_dir=str(tmp_path))

        # Mark quiz as completed today
        sample_state = sm.mark_quiz_completed(sample_state)

        assert sm.can_take_quiz(sample_state) is False

    def test_mark_quiz_completed_sets_date(self, tmp_path, sample_state):
        """Test that marking quiz completed sets the date."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.mark_quiz_completed(sample_state)

        today = date.today().isoformat()
        assert updated["completion_status"]["quiz_completed_date"] == today

    def test_record_keypoint_view(self, tmp_path, sample_state):
        """Test recording keypoint views."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.record_keypoint_view(sample_state, date.today())

        assert len(updated["completion_status"]["keypoint_view_history"]) == 1
        entry = updated["completion_status"]["keypoint_view_history"][0]
        assert entry["date"] == date.today().isoformat()

    def test_has_viewed_keypoint(self, tmp_path, sample_state):
        """Test checking if keypoint was viewed."""
        sm = StateManager(data_dir=str(tmp_path))

        # Initially not viewed
        assert sm.has_viewed_keypoint(sample_state, date.today()) is False

        # After recording
        sample_state = sm.record_keypoint_view(sample_state, date.today())
        assert sm.has_viewed_keypoint(sample_state, date.today()) is True


class TestInitialization:
    """Tests for initialization and preference management."""

    def test_update_onboarding_step(self, tmp_path, sample_state):
        """Test updating onboarding step."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.update_onboarding_step(sample_state, 2)
        assert updated["onboarding_step"] == 2
        assert updated["initialized"] == False

        # Step 6 completes initialization
        updated = sm.update_onboarding_step(sample_state, 6)
        assert updated["onboarding_step"] == 6
        assert updated["initialized"] == True

    def test_update_preferences_cefr(self, tmp_path, sample_state):
        """Test updating CEFR level preference."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.update_preferences(sample_state, cefr_level="C1")
        assert updated["preferences"]["cefr_level"] == "C1"

    def test_update_preferences_style(self, tmp_path, sample_state):
        """Test updating tutor style preference."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.update_preferences(sample_state, tutor_style="professional")
        assert updated["preferences"]["tutor_style"] == "professional"

    def test_update_schedule(self, tmp_path, sample_state):
        """Test updating schedule preferences."""
        sm = StateManager(data_dir=str(tmp_path))

        updated = sm.update_schedule(
            sample_state,
            keypoint_time="07:00",
            quiz_time="21:30"
        )
        assert updated["schedule"]["keypoint_time"] == "07:00"
        assert updated["schedule"]["quiz_time"] == "21:30"


class TestCLICommands:
    """Tests for CLI commands."""

    def test_cli_save_daily_keypoint(self, tmp_path):
        """Test CLI save_daily command for keypoint."""
        import subprocess
        import json

        content = json.dumps({
            "date": "2026-02-22",
            "topic_fingerprint": "test_cli_keypoint",
            "generated": True,
            "display": {"title": "Test CLI Keypoint"}
        })

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "save_daily",
             "--content-type", "keypoint",
             "--content", content,
             "--date", "2026-02-22"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Saved to:" in result.stdout

        # Verify file was created
        keypoint_file = tmp_path / "daily" / "2026-02-22" / "keypoint.json"
        assert keypoint_file.exists()

        with open(keypoint_file) as f:
            loaded = json.load(f)
        assert loaded["topic_fingerprint"] == "test_cli_keypoint"
        assert loaded["generated"] == True

    def test_cli_save_daily_quiz(self, tmp_path):
        """Test CLI save_daily command for quiz."""
        import subprocess
        import json

        content = json.dumps({
            "quiz_date": "2026-02-22",
            "questions": [],
            "generated": True
        })

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "save_daily",
             "--content-type", "quiz",
             "--content", content,
             "--date", "2026-02-22"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Saved to:" in result.stdout

        # Verify file was created
        quiz_file = tmp_path / "daily" / "2026-02-22" / "quiz.json"
        assert quiz_file.exists()

    def test_cli_record_view(self, tmp_path):
        """Test CLI record_view command."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "record_view",
             "--date", "2026-02-22"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "View recorded successfully" in result.stdout

        # Verify view was recorded in state
        state_file = tmp_path / "state.json"
        with open(state_file) as f:
            state = json.load(f)

        history = state["completion_status"]["keypoint_view_history"]
        assert len(history) == 1
        assert history[0]["date"] == "2026-02-22"

    def test_cli_save_daily_missing_args(self, tmp_path):
        """Test CLI save_daily with missing arguments."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "save_daily"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "Error:" in result.stdout

    def test_cli_save_daily_invalid_json(self, tmp_path):
        """Test CLI save_daily with invalid JSON."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "save_daily",
             "--content-type", "keypoint",
             "--content", "not valid json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "Error: Invalid JSON content" in result.stdout

    def test_cli_show_command(self, tmp_path):
        """Test CLI show command."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "show"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        # Output should be valid JSON
        state = json.loads(result.stdout)
        assert "version" in state
        assert "user" in state

    def test_cli_backup_command(self, tmp_path):
        """Test CLI backup command."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "backup"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Backup created:" in result.stdout

    def test_cli_stats_command(self, tmp_path):
        """Test CLI stats command."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "stats"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        stats = json.loads(result.stdout)
        assert "xp" in stats
        assert "level" in stats
        assert "streak" in stats

    def test_cli_config_show(self, tmp_path):
        """Test CLI config command (display)."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "config"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        config = json.loads(result.stdout)
        assert "cefr_level" in config
        assert "tutor_style" in config

    def test_cli_config_update(self, tmp_path):
        """Test CLI config command (update)."""
        import subprocess
        import json

        # Update CEFR level
        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "config",
             "--cefr", "C1"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Updated CEFR level" in result.stdout

        # Verify update
        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "config"],
            capture_output=True,
            text=True
        )
        config = json.loads(result.stdout)
        assert config["cefr_level"] == "C1"

    def test_cli_config_invalid_cefr(self, tmp_path):
        """Test CLI config with invalid CEFR level."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "config",
             "--cefr", "X9"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "Invalid CEFR level" in result.stdout

    def test_cli_errors_stats(self, tmp_path):
        """Test CLI errors stats command."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "errors",
             "--stats"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        stats = json.loads(result.stdout)
        assert "total" in stats
        assert "unreviewed" in stats

    def test_cli_errors_list(self, tmp_path, sample_state):
        """Test CLI errors list command."""
        import subprocess
        import json

        # First add some errors
        sm = StateManager(str(tmp_path))
        sm.add_to_error_notebook(sample_state, {"question": "Q1", "user_answer": "A", "correct_answer": "B"})
        sm.save_state(sample_state)

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "errors"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "errors" in data
        assert "total" in data

    def test_cli_schedule_show(self, tmp_path):
        """Test CLI schedule command (display)."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "schedule"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        schedule = json.loads(result.stdout)
        assert "keypoint_time" in schedule
        assert "quiz_time" in schedule

    def test_cli_schedule_update(self, tmp_path):
        """Test CLI schedule command (update)."""
        import subprocess
        import json

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "schedule",
             "--keypoint-time", "07:00",
             "--quiz-time", "21:00"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Schedule updated" in result.stdout

    def test_cli_schedule_invalid_order(self, tmp_path):
        """Test CLI schedule with quiz time before keypoint time."""
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/state_manager.py",
             "--data-dir", str(tmp_path),
             "schedule",
             "--keypoint-time", "22:00",
             "--quiz-time", "08:00"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "must be later than" in result.stdout
