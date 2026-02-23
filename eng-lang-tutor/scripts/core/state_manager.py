#!/usr/bin/env python3
"""
State Manager - Handles state persistence and event logging for eng-lang-tutor.

Responsibilities:
- Load/save state.json
- Append events to monthly log files (events_YYYY-MM.jsonl)
- Provide atomic write operations for crash recovery
- Manage daily content directories
"""

import json
import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import shutil

from utils import deep_merge

try:
    from .error_notebook import ErrorNotebookManager
except ImportError:
    from error_notebook import ErrorNotebookManager


def get_default_state_dir() -> Path:
    """
    Get the default state directory path.

    Priority:
    1. OPENCLAW_STATE_DIR environment variable (if set)
    2. ~/.openclaw/state/eng-lang-tutor/ (default)

    Returns:
        Path to the state directory
    """
    env_dir = os.environ.get('OPENCLAW_STATE_DIR')
    if env_dir:
        return Path(env_dir)
    return Path.home() / '.openclaw' / 'state' / 'eng-lang-tutor'


class StateManager:
    """Manages state persistence and event logging."""

    def __init__(self, data_dir: str = None):
        """
        Initialize the state manager.

        Args:
            data_dir: Path to the data directory (relative or absolute).
                     If None, uses OPENCLAW_STATE_DIR env var or
                     ~/.openclaw/state/eng-lang-tutor/ as default.
        """
        if data_dir is None:
            self.data_dir = get_default_state_dir()
        else:
            self.data_dir = Path(data_dir)

        self.state_file = self.data_dir / "state.json"
        self.logs_dir = self.data_dir / "logs"
        self.daily_dir = self.data_dir / "daily"
        self.audio_dir = self.data_dir / "audio"

        # Migrate from old data/ directory if needed
        self._migrate_from_old_location()

        # Ensure directories exist
        self._ensure_directories()

        # Initialize sub-managers
        self.error_notebook = ErrorNotebookManager(self)

    def _migrate_from_old_location(self) -> None:
        """
        Migrate data from old data/ directory to new state directory.

        This is a one-time migration that runs if:
        1. The new state directory doesn't have state.json
        2. The old data/ directory exists with state.json
        """
        # Only migrate if using default state directory
        if self.data_dir != get_default_state_dir():
            return

        # Check if new location already has data
        if self.state_file.exists():
            return

        # Find old data directory (relative to this script's location)
        script_dir = Path(__file__).parent.parent
        old_data_dir = script_dir / "data"

        if not old_data_dir.exists():
            return

        old_state_file = old_data_dir / "state.json"
        if not old_state_file.exists():
            return

        # Perform migration
        print(f"Migrating data from {old_data_dir} to {self.data_dir}...")

        try:
            # Create new directory
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # Copy all contents
            for item in old_data_dir.iterdir():
                dest = self.data_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Rename old directory to backup
            backup_dir = script_dir / "data.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            old_data_dir.rename(backup_dir)

            print(f"Migration complete. Old data backed up to {backup_dir}")
        except Exception as e:
            print(f"Warning: Migration failed: {e}")
            print("Will use new empty state directory.")
            # Log migration failure to event log (after ensuring directories exist)
            try:
                self._ensure_directories()
                self.append_event('migration_failed', {
                    "error": str(e),
                    "source_dir": str(old_data_dir),
                    "target_dir": str(self.data_dir)
                })
            except Exception:
                pass  # Silently ignore logging failures during migration

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def _default_state(self) -> Dict[str, Any]:
        """Return the default state structure."""
        return {
            "version": 2,
            "initialized": False,
            "onboarding_step": 0,
            "completion_status": {
                "quiz_completed_date": None,
                "keypoint_view_history": []
            },
            "schedule": {
                "keypoint_time": "06:45",
                "quiz_time": "22:45",
                "timezone": "Asia/Shanghai"
            },
            "user": {
                "xp": 0,
                "level": 1,
                "streak": 0,
                "streak_freeze": 0,
                "gems": 0,
                "badges": []
            },
            "preferences": {
                "cefr_level": "B1",
                "oral_written_ratio": 0.7,
                "topics": {
                    "movies": 0.2,
                    "news": 0.15,
                    "gaming": 0.15,
                    "sports": 0.1,
                    "workplace": 0.2,
                    "social": 0.1,
                    "daily_life": 0.1
                },
                "tutor_style": "humorous",
                "dedup_days": 14
            },
            "progress": {
                "total_quizzes": 0,
                "correct_rate": 0.0,
                "last_study_date": None,
                "perfect_quizzes": 0,
                "expressions_learned": 0
            },
            "recent_topics": [],
            "error_notebook": [],
            "error_archive": []
        }

    def load_state(self) -> Dict[str, Any]:
        """
        Load current state from file.

        Returns:
            State dictionary with all user data, preferences, and progress.
        """
        if not self.state_file.exists():
            return self._default_state()

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            # Merge with defaults to ensure all fields exist
            return self._merge_with_defaults(state)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading state: {e}. Using defaults.")
            return self._default_state()

    def _merge_with_defaults(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded state with defaults to ensure all fields exist.

        Uses deep merge to handle nested structures properly.
        """
        defaults = self._default_state()
        return deep_merge(defaults, state)

    def save_state(self, state: Dict[str, Any]) -> None:
        """
        Save state to file with atomic write for crash recovery.

        Args:
            state: Complete state dictionary to save
        """
        # Ensure directories exist
        self._ensure_directories()

        # Write to temp file first, then rename for atomicity
        temp_file = self.state_file.with_suffix('.tmp')

        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_file.rename(self.state_file)
        except IOError as e:
            print(f"Error saving state: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def append_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Append an event to the monthly log file.

        Args:
            event_type: Type of event (e.g., 'keypoint_generated', 'quiz_completed')
            data: Event-specific data
        """
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now()
        log_file = self.logs_dir / f"events_{today.strftime('%Y-%m')}.jsonl"

        event = {
            "timestamp": today.isoformat(),
            "type": event_type,
            "data": data
        }

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except IOError as e:
            print(f"Error appending event: {e}")
            raise

    def get_today_dir(self) -> Path:
        """Get the directory for today's content."""
        today = date.today().strftime('%Y-%m-%d')
        today_dir = self.daily_dir / today
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    def get_daily_dir(self, target_date: date) -> Path:
        """
        Get the directory for a specific date's content.

        Args:
            target_date: The date to get the directory for

        Returns:
            Path to the daily directory
        """
        date_str = target_date.strftime('%Y-%m-%d')
        daily_path = self.daily_dir / date_str
        return daily_path

    def save_daily_content(self, content_type: str, content: Dict[str, Any],
                           target_date: Optional[date] = None,
                           generate_audio: bool = True) -> Path:
        """
        Save content to the daily directory.

        Args:
            content_type: Type of content ('keypoint', 'quiz', 'user_answers')
            content: Content dictionary to save
            target_date: Date for the content (defaults to today)
            generate_audio: Whether to auto-generate audio for keypoints (default True)

        Returns:
            Path to the saved file
        """
        if target_date is None:
            target_date = date.today()

        daily_path = self.get_daily_dir(target_date)
        daily_path.mkdir(parents=True, exist_ok=True)

        file_path = daily_path / f"{content_type}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        # Auto-generate audio for keypoints
        if content_type == 'keypoint' and generate_audio:
            try:
                audio_result = self.generate_keypoint_audio(target_date)
                if audio_result.get('success'):
                    audio_path = audio_result.get('audio_path')
                    # Update keypoint with audio metadata
                    content['audio'] = {
                        'composed': audio_path,
                        'duration_seconds': audio_result.get('duration_seconds'),
                        'generated_at': datetime.now().isoformat()
                    }
                    # Re-save with audio info
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Warning: Audio generation failed: {e}")

        return file_path

    def generate_keypoint_audio(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generate composed audio for a keypoint.

        Args:
            target_date: Date for the keypoint (defaults to today)

        Returns:
            Dictionary with:
                - success: bool
                - audio_path: str (relative path from data_dir)
                - duration_seconds: float
                - error_message: str (if failed)
        """
        try:
            from .audio_composer import AudioComposer
            from .tts import TTSManager
        except ImportError:
            from audio_composer import AudioComposer
            from tts import TTSManager

        if target_date is None:
            target_date = date.today()

        # Load the keypoint
        keypoint = self.load_daily_content('keypoint', target_date)
        if not keypoint:
            return {
                'success': False,
                'error_message': f'No keypoint found for {target_date}'
            }

        # Prepare output path - directly to OpenClaw media directory
        # OpenClaw only allows media from ~/.openclaw/media/
        date_str = target_date.strftime('%Y-%m-%d')
        media_dir = Path.home() / '.openclaw' / 'media' / 'eng-lang-tutor' / date_str
        media_dir.mkdir(parents=True, exist_ok=True)
        output_path = media_dir / "keypoint_full.mp3"

        try:
            # Initialize TTS and composer (handle both package and direct imports)
            try:
                from .audio_composer import AudioComposer
                from .tts import TTSManager
            except ImportError:
                from audio_composer import AudioComposer
                from tts import TTSManager

            tts = TTSManager.from_env()
            composer = AudioComposer(tts)

            # Compose audio directly to media directory
            result = composer.compose_keypoint_audio(keypoint, output_path)

            if result.success:
                # Path relative to ~/.openclaw/media/ for message tool
                audio_path = f"eng-lang-tutor/{date_str}/keypoint_full.mp3"

                # Update keypoint with audio metadata
                keypoint['audio'] = {
                    'composed': audio_path,
                    'duration_seconds': result.duration_seconds,
                    'generated_at': datetime.now().isoformat()
                }

                # Save updated keypoint
                daily_path = self.get_daily_dir(target_date)
                file_path = daily_path / "keypoint.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(keypoint, f, ensure_ascii=False, indent=2)

                return {
                    'success': True,
                    'audio_path': audio_path,
                    'duration_seconds': result.duration_seconds
                }
            else:
                return {
                    'success': False,
                    'error_message': result.error_message
                }
        except Exception as e:
            return {
                'success': False,
                'error_message': str(e)
            }

    def load_daily_content(self, content_type: str,
                           target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Load content from the daily directory.

        Args:
            content_type: Type of content to load
            target_date: Date for the content (defaults to today)

        Returns:
            Content dictionary or None if not found
        """
        if target_date is None:
            target_date = date.today()

        file_path = self.get_daily_dir(target_date) / f"{content_type}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {content_type}: {e}")
            return None

    def get_recent_daily_content(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Get content from recent N days for deduplication.

        Args:
            days: Number of days to look back

        Returns:
            List of content dictionaries from recent days
        """
        recent_content = []
        today = date.today()

        for i in range(days):
            target_date = today - __import__('datetime').timedelta(days=i)
            content = self.load_daily_content('keypoint', target_date)
            if content:
                recent_content.append(content)

        return recent_content

    def get_recent_topics(self, days: int = 14) -> List[str]:
        """
        Get topic fingerprints from recent days for deduplication.

        Args:
            days: Number of days to look back

        Returns:
            List of topic fingerprints
        """
        recent_content = self.get_recent_daily_content(days)
        return [c.get('topic_fingerprint', '') for c in recent_content if c.get('topic_fingerprint')]

    # === Error Notebook Methods (delegated to ErrorNotebookManager) ===

    def add_to_error_notebook(self, state: Dict[str, Any],
                               error: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.add_to_error_notebook(state, error)

    def get_errors_page(self, state: Dict[str, Any],
                        page: int = 1,
                        per_page: int = 5,
                        month: str = None,
                        random: int = None) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.get_errors_page(state, page, per_page, month, random)

    def get_error_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.get_error_stats(state)

    def review_error(self, state: Dict[str, Any], error_index: int,
                     correct: bool) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.review_error(state, error_index, correct)

    def increment_wrong_count(self, state: Dict[str, Any],
                              error_index: int) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.increment_wrong_count(state, error_index)

    def get_review_errors(self, state: Dict[str, Any],
                          count: int = 5) -> List[Dict[str, Any]]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.get_review_errors(state, count)

    def archive_stale_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.archive_stale_errors(state)

    def clear_reviewed_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to ErrorNotebookManager."""
        return self.error_notebook.clear_reviewed_errors(state)

    # === Completion Tracking Methods ===

    def can_take_quiz(self, state: Dict[str, Any]) -> bool:
        """
        Check if user can take today's quiz.

        Args:
            state: Current state

        Returns:
            True if quiz can be taken, False if already completed today
        """
        today = date.today().isoformat()
        completed_date = state.get("completion_status", {}).get("quiz_completed_date")
        return completed_date != today

    def mark_quiz_completed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark today's quiz as completed.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        today = date.today().isoformat()
        if "completion_status" not in state:
            state["completion_status"] = {}
        state["completion_status"]["quiz_completed_date"] = today
        return state

    # === Keypoint View Tracking ===

    def record_keypoint_view(self, state: Dict[str, Any], view_date: date = None) -> Dict[str, Any]:
        """
        Record that a keypoint was viewed.

        Args:
            state: Current state
            view_date: Date of viewed keypoint (defaults to today)

        Returns:
            Updated state
        """
        if view_date is None:
            view_date = date.today()

        if "completion_status" not in state:
            state["completion_status"] = {}

        if "keypoint_view_history" not in state["completion_status"]:
            state["completion_status"]["keypoint_view_history"] = []

        # Add view record
        state["completion_status"]["keypoint_view_history"].append({
            "date": view_date.isoformat(),
            "viewed_at": datetime.now().isoformat()
        })

        # Keep last 30 entries to avoid unbounded growth
        state["completion_status"]["keypoint_view_history"] = \
            state["completion_status"]["keypoint_view_history"][-30:]

        return state

    def has_viewed_keypoint(self, state: Dict[str, Any], view_date: date) -> bool:
        """
        Check if a keypoint for a specific date has been viewed/pushed.

        Args:
            state: Current state
            view_date: Date to check

        Returns:
            True if keypoint for that date has been viewed
        """
        history = state.get("completion_status", {}).get("keypoint_view_history", [])
        return any(entry.get("date") == view_date.isoformat() for entry in history)

    # === Initialization and Preferences ===

    def update_onboarding_step(self, state: Dict[str, Any], step: int) -> Dict[str, Any]:
        """
        Update onboarding step.

        Args:
            state: Current state
            step: New step (0-6)

        Returns:
            Updated state
        """
        state["onboarding_step"] = max(0, min(6, step))
        if step >= 6:
            state["initialized"] = True
        return state

    def update_preferences(self, state: Dict[str, Any],
                          cefr_level: str = None,
                          tutor_style: str = None,
                          oral_written_ratio: float = None,
                          topics: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Update user preferences.

        Args:
            state: Current state
            cefr_level: New CEFR level (optional)
            tutor_style: New tutor style (optional)
            oral_written_ratio: New oral/written ratio (optional)
            topics: New topic weights (optional)

        Returns:
            Updated state
        """
        if "preferences" not in state:
            state["preferences"] = {}

        if cefr_level:
            state["preferences"]["cefr_level"] = cefr_level
        if tutor_style:
            state["preferences"]["tutor_style"] = tutor_style
        if oral_written_ratio is not None:
            state["preferences"]["oral_written_ratio"] = oral_written_ratio
        if topics:
            state["preferences"]["topics"] = topics

        return state

    def update_schedule(self, state: Dict[str, Any],
                       keypoint_time: str = None,
                       quiz_time: str = None,
                       timezone: str = None) -> Dict[str, Any]:
        """
        Update schedule preferences.

        Args:
            state: Current state
            keypoint_time: Keypoint push time (HH:MM)
            quiz_time: Quiz push time (HH:MM)
            timezone: Timezone string

        Returns:
            Updated state
        """
        if "schedule" not in state:
            state["schedule"] = {}

        if keypoint_time:
            state["schedule"]["keypoint_time"] = keypoint_time
        if quiz_time:
            state["schedule"]["quiz_time"] = quiz_time
        if timezone:
            state["schedule"]["timezone"] = timezone

        return state

    def backup_state(self, backup_dir: str = "backups") -> Path:
        """
        Create a backup of the current state.

        Args:
            backup_dir: Directory to store backups

        Returns:
            Path to the backup file
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_path / f"state_backup_{timestamp}.json"

        state = self.load_state()
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        return backup_file

    def restore_from_backup(self, backup_file: Path) -> bool:
        """
        Restore state from a backup file.

        Args:
            backup_file: Path to the backup file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.save_state(state)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error restoring from backup: {e}")
            return False


# CLI interface - delegated to cli.py for better code organization
if __name__ == "__main__":
    from cli import main
    main()
