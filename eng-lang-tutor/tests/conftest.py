"""
Pytest configuration and shared fixtures for eng-lang-tutor tests.
"""

import pytest
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture
def sample_state():
    """Sample state dictionary for testing."""
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
        "error_notebook": []
    }


@pytest.fixture
def sample_keypoint():
    """Sample knowledge point for testing."""
    return {
        "date": "2026-02-20",
        "topic_fingerprint": "workplace_touch_base",
        "category": "oral",
        "topic": "workplace",
        "expressions": [
            {"phrase": "Let's touch base", "usage_note": "Quick check-in"}
        ],
        "chinglish_trap": {
            "wrong": "Let's discuss together",
            "correct": "Let's touch base"
        }
    }


@pytest.fixture
def sample_quiz():
    """Sample quiz for testing."""
    return {
        "quiz_date": "2026-02-20",
        "keypoint_fingerprint": "workplace_touch_base",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "What does 'touch base' mean?",
                "options": ["A. Formal meeting", "B. Quick check-in", "C. Cancel", "D. Write report"],
                "correct_answer": "B",
                "xp_value": 10
            },
            {
                "id": 2,
                "type": "chinglish_fix",
                "question": "Fix the Chinglish",
                "correct_answer": "touch base",
                "xp_value": 15
            },
            {
                "id": 3,
                "type": "fill_blank",
                "question": "Fill in the blank",
                "correct_answer": "touch base",
                "xp_value": 12
            }
        ],
        "total_xp": 37,
        "passing_score": 70
    }


@pytest.fixture
def sample_user_answers():
    """Sample user answers for testing."""
    return {
        "quiz_date": "2026-02-20",
        "answers": {
            "1": "B",
            "2": "touch base",
            "3": "touch base"
        }
    }
