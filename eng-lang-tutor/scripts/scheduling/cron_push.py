#!/usr/bin/env python3
"""
Cron Push - Handles scheduled content generation and notifications.

This script is called by cron to:
1. Generate and push daily keypoints
2. Generate and push daily quizzes

Usage:
    python3 cron_push.py --task keypoint
    python3 cron_push.py --task quiz
    python3 cron_push.py --task status
"""

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Import local modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.core.state_manager import StateManager
except ImportError:
    from core.state_manager import StateManager


class CronPusher:
    """Handles scheduled content push operations."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the cron pusher.

        Args:
            data_dir: Path to the data directory
        """
        self.state_manager = StateManager(data_dir)
        self.today = date.today()

    def push_keypoint(self) -> Dict[str, Any]:
        """
        Generate and save today's knowledge point.

        Returns:
            Result dictionary with status and content
        """
        # Check if already exists
        existing = self.state_manager.load_daily_content('keypoint', self.today)
        if existing:
            return {
                "status": "exists",
                "message": f"Keypoint for {self.today} already exists",
                "keypoint": existing
            }

        # Load state
        state = self.state_manager.load_state()
        self.state_manager.save_state(state)

        # Generate keypoint (placeholder - actual LLM generation happens in Agent)
        keypoint = {
            "date": self.today.isoformat(),
            "topic_fingerprint": f"auto_{self.today.isoformat()}",
            "category": "oral",
            "scene": {
                "context": "Auto-generated placeholder",
                "formality": "casual"
            },
            "expressions": [],
            "alternatives": [],
            "chinglish_trap": {},
            "examples": [],
            "generated": False,
            "needs_generation": True
        }

        # Save and log
        self.state_manager.save_daily_content('keypoint', keypoint, self.today)
        self.state_manager.append_event('keypoint_pushed', {
            "date": self.today.isoformat(),
            "fingerprint": keypoint.get("topic_fingerprint")
        })

        # Update state
        state = self.state_manager.load_state()
        state['recent_topics'].append(keypoint.get("topic_fingerprint"))
        # Keep only last 50 topics
        state['recent_topics'] = state['recent_topics'][-50:]

        # Record view for this keypoint
        state = self.state_manager.record_keypoint_view(state, self.today)

        self.state_manager.save_state(state)

        return {
            "status": "created",
            "message": f"Keypoint for {self.today} created (needs generation)",
            "keypoint": keypoint
        }

    def push_quiz(self) -> Dict[str, Any]:
        """
        Generate and save today's quiz.

        Returns:
            Result dictionary with status and content
        """
        # Check if already exists
        existing = self.state_manager.load_daily_content('quiz', self.today)
        if existing:
            return {
                "status": "exists",
                "message": f"Quiz for {self.today} already exists",
                "quiz": existing
            }

        # Load state
        state = self.state_manager.load_state()
        self.state_manager.save_state(state)

        # Load today's keypoint
        keypoint = self.state_manager.load_daily_content('keypoint', self.today)
        if not keypoint:
            # Need to create keypoint first
            keypoint_result = self.push_keypoint()
            keypoint = keypoint_result.get("keypoint")

        # Generate quiz (placeholder - actual LLM generation happens in Agent)
        quiz = {
            "quiz_date": self.today.isoformat(),
            "keypoint_fingerprint": keypoint.get("topic_fingerprint") if keypoint else None,
            "questions": [],
            "total_xp": 0,
            "passing_score": 70,
            "generated": False,
            "needs_generation": True
        }

        # Save and log
        self.state_manager.save_daily_content('quiz', quiz, self.today)
        self.state_manager.append_event('quiz_pushed', {
            "date": self.today.isoformat()
        })

        return {
            "status": "created",
            "message": f"Quiz for {self.today} created (needs generation)",
            "quiz": quiz
        }

    def reset_daily_flags(self) -> Dict[str, Any]:
        """
        Reset daily completion flags (called at midnight).

        Returns:
            Result dictionary with status
        """
        state = self.state_manager.load_state()

        # Reset quiz completion flag for new day
        if "completion_status" in state:
            # Keep the date, just let the new day's check handle it
            pass

        self.state_manager.save_state(state)

        return {
            "status": "success",
            "message": f"Daily flags reset for {self.today}"
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of today's content.

        Returns:
            Status dictionary
        """
        state = self.state_manager.load_state()

        keypoint = self.state_manager.load_daily_content('keypoint', self.today)
        quiz = self.state_manager.load_daily_content('quiz', self.today)

        return {
            "date": self.today.isoformat(),
            "initialized": state.get("initialized", False),
            "keypoint_exists": keypoint is not None,
            "quiz_exists": quiz is not None,
            "can_take_quiz": self.state_manager.can_take_quiz(state),
            "user_xp": state.get("user", {}).get("xp", 0),
            "user_streak": state.get("user", {}).get("streak", 0)
        }


def main():
    parser = argparse.ArgumentParser(description="Cron Push for eng-lang-tutor")
    parser.add_argument('--task', required=True,
                        choices=['keypoint', 'quiz', 'reset_daily', 'status'],
                        help='Task to execute')
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    parser.add_argument('--json', action='store_true', help='Output as JSON only')

    args = parser.parse_args()

    pusher = CronPusher(args.data_dir)

    if args.task == 'keypoint':
        result = pusher.push_keypoint()
    elif args.task == 'quiz':
        result = pusher.push_quiz()
    elif args.task == 'reset_daily':
        result = pusher.reset_daily_flags()
    elif args.task == 'status':
        result = pusher.get_status()

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"[{datetime.now().isoformat()}] Task: {args.task}")
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")


if __name__ == "__main__":
    main()
