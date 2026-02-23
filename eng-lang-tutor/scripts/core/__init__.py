#!/usr/bin/env python3
"""Core functionality: state management, scoring, gamification."""

from .state_manager import StateManager
from .scorer import Scorer
from .gamification import GamificationManager
from .constants import (
    LEVEL_THRESHOLDS,
    LEVEL_NAMES,
    STREAK_BONUS_PER_DAY,
    STREAK_BONUS_CAP,
    get_level_name,
    calculate_level,
    get_streak_multiplier,
)
from .error_notebook import ErrorNotebookManager

__all__ = [
    'StateManager',
    'Scorer',
    'GamificationManager',
    'ErrorNotebookManager',
    'LEVEL_THRESHOLDS',
    'LEVEL_NAMES',
    'STREAK_BONUS_PER_DAY',
    'STREAK_BONUS_CAP',
    'get_level_name',
    'calculate_level',
    'get_streak_multiplier',
]
