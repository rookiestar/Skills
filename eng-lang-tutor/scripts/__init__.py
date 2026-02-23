#!/usr/bin/env python3
"""
eng-lang-tutor scripts package

Main entry points:
- StateManager: Core state persistence
- Scorer: Quiz evaluation
- GamificationManager: XP/levels/streaks/badges
- CommandParser: User command parsing
- AudioComposer: Audio generation
"""

from .core.state_manager import StateManager
from .core.scorer import Scorer
from .core.gamification import GamificationManager
from .core.constants import LEVEL_THRESHOLDS, calculate_level, get_level_name, get_streak_multiplier
from .core.error_notebook import ErrorNotebookManager

__all__ = [
    'StateManager',
    'Scorer',
    'GamificationManager',
    'ErrorNotebookManager',
    'LEVEL_THRESHOLDS',
    'calculate_level',
    'get_level_name',
    'get_streak_multiplier',
]
