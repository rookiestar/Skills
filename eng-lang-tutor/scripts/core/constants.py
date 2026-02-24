#!/usr/bin/env python3
"""
Shared constants for eng-lang-tutor.

This module contains constants used across multiple scripts to avoid duplication.
"""

# =============================================================================
# GAME MECHANICS - Activity Levels & Progression
# =============================================================================

# Level thresholds (XP needed for each level)
# Note: Level is Activity Level (活跃等级), measuring engagement depth,
# NOT language ability (which is CEFR level A1-C2)
LEVEL_THRESHOLDS = [
    0, 50, 100, 200, 350,       # 1-5 Starter (启程者)
    550, 800, 1100, 1500, 2000,  # 6-10 Traveler (行路人)
    2600, 3300, 4100, 5000, 6000,  # 11-15 Explorer (探索者)
    7200, 8500, 10000, 12000, 15000  # 16-20 Pioneer (开拓者)
]

# Level range to name mapping
LEVEL_NAMES = {
    (1, 5): "Starter",      # 启程者
    (6, 10): "Traveler",    # 行路人
    (11, 15): "Explorer",   # 探索者
    (16, 20): "Pioneer"     # 开拓者
}

# Streak bonus configuration
STREAK_BONUS_PER_DAY = 0.05  # 5% bonus per day
STREAK_BONUS_CAP = 2.0       # Maximum 2x multiplier

# Gem economy
STREAK_FREEZE_COST = 50  # gems to buy one streak freeze
HINT_COST = 10           # gems to buy a quiz hint

# =============================================================================
# QUIZ XP VALUES
# =============================================================================

QUIZ_XP = {
    "multiple_choice": 10,
    "chinglish_fix": 15,
    "fill_blank": 12,
    "dialogue_completion": 15
}
QUIZ_PASS_THRESHOLD = 2  # 2/3 correct to pass
QUIZ_QUESTIONS_PER_DAY = 3

# =============================================================================
# ERROR NOTEBOOK
# =============================================================================

ERROR_ARCHIVE_WRONG_THRESHOLD = 3   # Archive if wrong_count >= 3
ERROR_ARCHIVE_DAYS_THRESHOLD = 30   # Archive if over 30 days old
ERROR_NOTEBOOK_MAX = 100            # Maximum errors in notebook

# =============================================================================
# AUDIO PROCESSING
# =============================================================================

AUDIO_TTS_TIMEOUT = 30          # seconds, for single TTS synthesis
AUDIO_CONCAT_TIMEOUT = 120      # seconds, for concatenating segments
AUDIO_CONVERSION_TIMEOUT = 60   # seconds, for format conversion

# Audio silence durations
AUDIO_SILENCE_LEAD_IN = 1.0     # seconds, after lead-in phrase
AUDIO_SILENCE_SECTION = 2.0     # seconds, between sections
AUDIO_SILENCE_DIALOGUE = 0.5    # seconds, between dialogue lines

# =============================================================================
# DEDUPLICATION
# =============================================================================

DEDUP_DEFAULT_DAYS = 14  # Default days for content deduplication


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_level_name(level: int) -> str:
    """
    Get the journey stage name for a level.

    Args:
        level: Activity level (1-20)

    Returns:
        Stage name (Starter/Traveler/Explorer/Pioneer)
    """
    for (min_level, max_level), name in LEVEL_NAMES.items():
        if min_level <= level <= max_level:
            return name
    return "Unknown"


def calculate_level(xp: int) -> int:
    """
    Calculate level from total XP.

    Args:
        xp: Total experience points

    Returns:
        Level (1-20)
    """
    for i in range(len(LEVEL_THRESHOLDS) - 1, -1, -1):
        if xp >= LEVEL_THRESHOLDS[i]:
            return i + 1
    return 1


def get_streak_multiplier(streak: int) -> float:
    """
    Calculate XP multiplier based on streak.

    Args:
        streak: Number of consecutive days

    Returns:
        Multiplier (1.0 - 2.0)
    """
    return min(1.0 + (streak * STREAK_BONUS_PER_DAY), STREAK_BONUS_CAP)
