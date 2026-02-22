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
                "total_points": 0,
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
        """Merge loaded state with defaults to ensure all fields exist."""
        defaults = self._default_state()
        merged = defaults.copy()

        # Handle top-level boolean/integer fields
        for key in ['initialized', 'onboarding_step', 'version']:
            if key in state:
                merged[key] = state[key]

        # Handle nested objects
        for key in ['user', 'preferences', 'progress', 'completion_status', 'schedule']:
            if key in state and isinstance(state[key], dict):
                merged[key] = {**defaults.get(key, {}), **state[key]}

        # Handle arrays
        for key in ['recent_topics', 'error_notebook', 'error_archive']:
            if key in state:
                merged[key] = state[key]

        return merged

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
                           target_date: Optional[date] = None) -> Path:
        """
        Save content to the daily directory.

        Args:
            content_type: Type of content ('keypoint', 'quiz', 'user_answers')
            content: Content dictionary to save
            target_date: Date for the content (defaults to today)

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

        return file_path

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

    def add_to_error_notebook(self, state: Dict[str, Any],
                               error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an error to the error notebook.

        Args:
            state: Current state
            error: Error entry with date, question, user_answer, correct_answer, explanation

        Returns:
            Updated state
        """
        error['date'] = date.today().isoformat()
        error['reviewed'] = False
        error['wrong_count'] = error.get('wrong_count', 1)
        # keypoint_date and question_type are optional
        state['error_notebook'].append(error)
        return state

    def get_errors_page(self, state: Dict[str, Any],
                        page: int = 1,
                        per_page: int = 5,
                        month: str = None,
                        random: int = None) -> Dict[str, Any]:
        """
        Get paginated errors from the error notebook.

        Args:
            state: Current state
            page: Page number (1-indexed)
            per_page: Items per page (default 5)
            month: Filter by month (YYYY-MM format)
            random: Return N random errors instead of paginated

        Returns:
            Dictionary with pagination info and error items:
            {
                'total': total_count,
                'page': current_page,
                'per_page': items_per_page,
                'total_pages': total_pages,
                'has_more': bool,
                'errors': [error_items]
            }
        """
        import random as random_module

        errors = state.get('error_notebook', [])

        # Sort by date descending (newest first)
        errors = sorted(errors, key=lambda x: x.get('date', ''), reverse=True)

        # Filter by month if specified
        if month:
            errors = [e for e in errors if e.get('date', '').startswith(month)]

        total = len(errors)

        # Random mode
        if random and random > 0:
            random_count = min(random, total)
            selected = random_module.sample(errors, random_count) if total > 0 else []
            return {
                'total': total,
                'page': 1,
                'per_page': random_count,
                'total_pages': 1,
                'has_more': total > random_count,
                'mode': 'random',
                'errors': selected
            }

        # Pagination
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        start = (page - 1) * per_page
        end = start + per_page

        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_more': page < total_pages,
            'has_prev': page > 1,
            'mode': 'paginated',
            'errors': errors[start:end]
        }

    def get_error_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about the error notebook.

        Args:
            state: Current state

        Returns:
            Dictionary with error statistics
        """
        from collections import Counter

        errors = state.get('error_notebook', [])

        if not errors:
            return {
                'total': 0,
                'reviewed': 0,
                'unreviewed': 0,
                'by_month': {}
            }

        reviewed = sum(1 for e in errors if e.get('reviewed', False))
        unreviewed = len(errors) - reviewed

        # Group by month
        by_month = Counter()
        for e in errors:
            date_str = e.get('date', '')
            if date_str:
                month = date_str[:7]  # YYYY-MM
                by_month[month] += 1

        # Sort by month descending
        by_month_sorted = dict(sorted(by_month.items(), reverse=True))

        return {
            'total': len(errors),
            'reviewed': reviewed,
            'unreviewed': unreviewed,
            'by_month': by_month_sorted
        }

    # === Error Review Methods ===

    def review_error(self, state: Dict[str, Any], error_index: int,
                     correct: bool) -> Dict[str, Any]:
        """
        Mark an error as reviewed (correct answer) or increment wrong count.

        Args:
            state: Current state
            error_index: Index of error in error_notebook
            correct: Whether the user answered correctly

        Returns:
            Updated state
        """
        errors = state.get('error_notebook', [])
        if 0 <= error_index < len(errors):
            if correct:
                # Mark as reviewed - contributes to Error Slayer badge
                errors[error_index]['reviewed'] = True
            else:
                # Increment wrong count
                errors[error_index]['wrong_count'] = errors[error_index].get('wrong_count', 1) + 1
            state['error_notebook'] = errors
        return state

    def increment_wrong_count(self, state: Dict[str, Any],
                              error_index: int) -> Dict[str, Any]:
        """
        Increment wrong count for an error (convenience method).

        Args:
            state: Current state
            error_index: Index of error in error_notebook

        Returns:
            Updated state
        """
        return self.review_error(state, error_index, correct=False)

    def get_review_errors(self, state: Dict[str, Any],
                          count: int = 5) -> List[Dict[str, Any]]:
        """
        Get unreviewed errors for a review session.

        Args:
            state: Current state
            count: Maximum number of errors to return

        Returns:
            List of unreviewed errors (most recent first)
        """
        errors = state.get('error_notebook', [])
        # Filter unreviewed errors
        unreviewed = [e for e in errors if not e.get('reviewed', False)]
        # Sort by date descending (newest first)
        unreviewed = sorted(unreviewed, key=lambda x: x.get('date', ''), reverse=True)
        # Return up to count items
        return unreviewed[:count]

    def archive_stale_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Archive errors with wrong_count >= 3 and over 30 days old.

        Args:
            state: Current state

        Returns:
            Updated state with stale errors moved to error_archive
        """
        from datetime import timedelta

        errors = state.get('error_notebook', [])
        archive = state.get('error_archive', [])
        today = date.today()

        remaining = []
        archived_count = 0

        for error in errors:
            # Skip already reviewed
            if error.get('reviewed', False):
                remaining.append(error)
                continue

            wrong_count = error.get('wrong_count', 1)
            error_date_str = error.get('date', '')

            # Calculate days since error was created
            try:
                error_date = datetime.strptime(error_date_str, '%Y-%m-%d').date()
                days_old = (today - error_date).days
            except (ValueError, TypeError):
                days_old = 0

            # Archive if wrong_count >= 3 and over 30 days old
            if wrong_count >= 3 and days_old >= 30:
                error['archived_at'] = today.isoformat()
                archive.append(error)
                archived_count += 1
            else:
                remaining.append(error)

        state['error_notebook'] = remaining
        state['error_archive'] = archive

        # Log archival event
        if archived_count > 0:
            self.append_event("errors_archived", {"count": archived_count})

        return state

    def clear_reviewed_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove reviewed errors from the notebook (keep them in archive for stats).

        Args:
            state: Current state

        Returns:
            Updated state
        """
        errors = state.get('error_notebook', [])
        # Keep only unreviewed errors
        state['error_notebook'] = [
            e for e in errors if not e.get('reviewed', False)
        ]
        return state

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


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="State Manager for eng-lang-tutor")
    parser.add_argument('--data-dir', default=None,
                        help='Data directory path (default: ~/.openclaw/state/eng-lang-tutor or OPENCLAW_STATE_DIR env)')
    parser.add_argument('command', nargs='?',
                        choices=['show', 'backup', 'save_daily', 'record_view',
                                 'stats', 'config', 'errors', 'schedule'],
                        help='Command to execute')
    parser.add_argument('--content-type', help='Content type for save_daily (keypoint, quiz)')
    parser.add_argument('--content', help='JSON content for save_daily')
    parser.add_argument('--date', help='Date for content (YYYY-MM-DD format)')
    # Errors command options
    parser.add_argument('--page', type=int, default=1, help='Page number for errors list')
    parser.add_argument('--per-page', type=int, default=5, help='Items per page for errors')
    parser.add_argument('--month', help='Filter errors by month (YYYY-MM)')
    parser.add_argument('--random', type=int, help='Get N random errors')
    parser.add_argument('--stats', action='store_true', help='Get error statistics')
    parser.add_argument('--review', type=int, help='Get N errors for review session')
    # Config command options
    parser.add_argument('--cefr', help='Set CEFR level (A1-C2)')
    parser.add_argument('--style', help='Set tutor style')
    parser.add_argument('--oral-ratio', type=int, help='Set oral/written ratio (0-100)')
    # Schedule command options
    parser.add_argument('--keypoint-time', help='Set keypoint push time (HH:MM)')
    parser.add_argument('--quiz-time', help='Set quiz push time (HH:MM)')

    args = parser.parse_args()

    sm = StateManager(args.data_dir)

    if args.command == 'show' or not args.command:
        state = sm.load_state()
        print(json.dumps(state, indent=2, ensure_ascii=False))

    elif args.command == 'backup':
        backup_path = sm.backup_state()
        print(f"Backup created: {backup_path}")

    elif args.command == 'save_daily':
        if not args.content_type or not args.content:
            print("Error: --content-type and --content are required for save_daily")
            exit(1)

        try:
            content = json.loads(args.content)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON content: {e}")
            exit(1)

        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                exit(1)

        path = sm.save_daily_content(args.content_type, content, target_date)
        print(f"Saved to: {path}")

    elif args.command == 'record_view':
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                exit(1)

        state = sm.load_state()
        sm.record_keypoint_view(state, target_date)
        sm.save_state(state)
        print("View recorded successfully")

    elif args.command == 'stats':
        """Display learning progress summary."""
        from gamification import GamificationManager
        state = sm.load_state()
        gm = GamificationManager()
        summary = gm.get_progress_summary(state)
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    elif args.command == 'config':
        """Display or update user configuration."""
        state = sm.load_state()

        # If no update options, just show current config
        if not any([args.cefr, args.style, args.oral_ratio is not None]):
            config = {
                "cefr_level": state.get("preferences", {}).get("cefr_level", "B1"),
                "tutor_style": state.get("preferences", {}).get("tutor_style", "humorous"),
                "oral_ratio": state.get("preferences", {}).get("oral_ratio", 70),
                "topic_weights": state.get("preferences", {}).get("topic_weights", {}),
                "schedule": state.get("schedule", {})
            }
            print(json.dumps(config, indent=2, ensure_ascii=False))
        else:
            # Update configuration
            if args.cefr:
                if args.cefr not in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
                    print("Error: Invalid CEFR level. Must be A1, A2, B1, B2, C1, or C2")
                    exit(1)
                state = sm.update_preferences(state, cefr_level=args.cefr)
                print(f"Updated CEFR level to: {args.cefr}")

            if args.style:
                if args.style not in ['humorous', 'rigorous', 'casual', 'professional']:
                    print("Error: Invalid style. Must be humorous, rigorous, casual, or professional")
                    exit(1)
                state = sm.update_preferences(state, tutor_style=args.style)
                print(f"Updated tutor style to: {args.style}")

            if args.oral_ratio is not None:
                if not 0 <= args.oral_ratio <= 100:
                    print("Error: Oral ratio must be between 0 and 100")
                    exit(1)
                state = sm.update_preferences(state, oral_ratio=args.oral_ratio)
                print(f"Updated oral ratio to: {args.oral_ratio}%")

            sm.save_state(state)
            print("Configuration updated successfully")

    elif args.command == 'errors':
        """Error notebook operations."""
        state = sm.load_state()

        if args.stats:
            # Get error statistics
            stats = sm.get_error_stats(state)
            print(json.dumps(stats, indent=2, ensure_ascii=False))

        elif args.review is not None:
            # Get errors for review session
            errors = sm.get_review_errors(state, count=args.review)
            result = {
                "count": len(errors),
                "errors": errors
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            # Get paginated errors list
            result = sm.get_errors_page(
                state,
                page=args.page,
                per_page=args.per_page,
                month=args.month,
                random=args.random
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == 'schedule':
        """Display or update schedule configuration."""
        state = sm.load_state()

        # If no update options, just show current schedule
        if not any([args.keypoint_time, args.quiz_time]):
            schedule = state.get("schedule", {})
            print(json.dumps(schedule, indent=2, ensure_ascii=False))
        else:
            # Validate quiz_time must be later than keypoint_time
            current_keypoint = state.get("schedule", {}).get("keypoint_time", "06:45")
            current_quiz = state.get("schedule", {}).get("quiz_time", "22:45")

            new_keypoint = args.keypoint_time or current_keypoint
            new_quiz = args.quiz_time or current_quiz

            # Time validation
            def parse_time(t):
                h, m = map(int, t.split(':'))
                return h * 60 + m

            if parse_time(new_quiz) <= parse_time(new_keypoint):
                print("Error: Quiz time must be later than keypoint time")
                exit(1)

            state = sm.update_schedule(
                state,
                keypoint_time=new_keypoint,
                quiz_time=new_quiz
            )
            sm.save_state(state)
            print(f"Schedule updated: keypoint at {new_keypoint}, quiz at {new_quiz}")
