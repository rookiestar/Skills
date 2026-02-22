#!/usr/bin/env python3
"""
Gamification - Duolingo-style achievement system for eng-lang-tutor.

Components:
1. XP & Levels: XP accumulates, levels up at thresholds
2. Streaks: Consecutive days of study, with freeze protection
3. Badges: Achievement milestones
4. Gems: Currency for streak freeze, hints

Note: Leagues removed - not applicable for single-user scenario.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, date, timedelta

from constants import LEVEL_THRESHOLDS, get_level_name, calculate_level


class GamificationManager:
    """Manages gamification elements: levels, streaks, badges, gems."""

    # Use shared constants
    LEVEL_THRESHOLDS = LEVEL_THRESHOLDS

    # Badge definitions
    BADGES = {
        'first_steps': {
            'name': 'First Steps',
            'description': 'Complete your first quiz',
            'condition': 'total_quizzes >= 1',
            'gem_reward': 10
        },
        'week_warrior': {
            'name': 'Week Warrior',
            'description': '7-day streak',
            'condition': 'streak >= 7',
            'gem_reward': 25
        },
        'month_master': {
            'name': 'Month Master',
            'description': '30-day streak',
            'condition': 'streak >= 30',
            'gem_reward': 100
        },
        'perfect_10': {
            'name': 'Perfect 10',
            'description': '10 perfect quizzes',
            'condition': 'perfect_quizzes >= 10',
            'gem_reward': 50
        },
        'vocab_hunter': {
            'name': 'Vocab Hunter',
            'description': 'Learn 100 expressions',
            'condition': 'expressions_learned >= 100',
            'gem_reward': 75
        },
        'error_slayer': {
            'name': 'Error Slayer',
            'description': 'Clear 30 errors from notebook',
            'condition': 'errors_cleared >= 30',
            'gem_reward': 30
        }
    }

    # Gem costs
    STREAK_FREEZE_COST = 50
    HINT_COST = 5

    def __init__(self, state_manager=None):
        """
        Initialize the gamification manager.

        Args:
            state_manager: Optional StateManager instance
        """
        self.state_manager = state_manager

    def update_streak(self, state: Dict[str, Any], study_date: str) -> Tuple[int, bool, str]:
        """
        Update streak based on study activity.

        Args:
            state: Current state dictionary
            study_date: Date of study (YYYY-MM-DD)

        Returns:
            Tuple of (new_streak, streak_continued, message)
        """
        user = state.get('user', {})
        progress = state.get('progress', {})

        last_study = progress.get('last_study_date')
        current_streak = user.get('streak', 0)

        try:
            today = datetime.strptime(study_date, '%Y-%m-%d').date()
        except ValueError:
            return (current_streak, False, "Invalid date format")

        if last_study:
            try:
                last = datetime.strptime(last_study, '%Y-%m-%d').date()
            except ValueError:
                last = None

            if last == today:
                # Already studied today
                return (current_streak, False, "Already studied today")

            days_diff = (today - last).days

            if days_diff == 1:
                # Consecutive day - streak continues
                new_streak = current_streak + 1
                state['user']['streak'] = new_streak
                return (new_streak, True, f"Streak continued! {new_streak} days")

            elif days_diff == 2 and user.get('streak_freeze', 0) > 0:
                # Use streak freeze - preserves streak continuity
                state['user']['streak_freeze'] -= 1
                new_streak = current_streak + 1
                state['user']['streak'] = new_streak
                state['user']['last_freeze_used'] = study_date  # Track for display
                remaining = state['user']['streak_freeze']
                return (new_streak, True, f"Streak freeze used! {new_streak} days ({remaining} freeze remaining)")

            else:
                # Streak broken
                state['user']['streak'] = 1
                return (1, False, f"Streak broken. Starting over at 1 day")

        else:
            # First study ever
            state['user']['streak'] = 1
            return (1, True, "Started your streak!")

    def calculate_level(self, xp: int) -> int:
        """
        Calculate level from total XP.

        Args:
            xp: Total experience points

        Returns:
            Level (1-20)
        """
        return calculate_level(xp)

    def get_level_name(self, level: int) -> str:
        """Get the name for a level range (Journey Stage).

        Note: This is Activity Level (活跃等级), measuring engagement depth,
        NOT language ability. For language ability, see CEFR level.
        """
        return get_level_name(level)

    def check_level_up(self, old_xp: int, new_xp: int) -> Tuple[bool, Optional[int]]:
        """
        Check if user leveled up.

        Args:
            old_xp: XP before this session
            new_xp: XP after this session

        Returns:
            Tuple of (leveled_up, new_level)
        """
        old_level = self.calculate_level(old_xp)
        new_level = self.calculate_level(new_xp)

        if new_level > old_level:
            return (True, new_level)
        return (False, None)

    def update_level(self, state: Dict[str, Any]) -> Tuple[int, bool]:
        """
        Update level based on current XP.

        Args:
            state: Current state (will be modified in place)

        Returns:
            Tuple of (level, just_leveled_up)
        """
        xp = state.get('user', {}).get('xp', 0)
        current_level = state.get('user', {}).get('level', 1)
        new_level = self.calculate_level(xp)

        state['user']['level'] = new_level

        leveled_up = new_level > current_level
        return (new_level, leveled_up)

    def _check_badge_condition(self, badge_id: str, check_data: Dict[str, int]) -> bool:
        """
        Check if a badge condition is met using explicit condition functions.

        Args:
            badge_id: Badge identifier
            check_data: Dictionary with stats for condition checking

        Returns:
            True if condition is met, False otherwise
        """
        # Explicit condition functions for each badge (no eval() for security)
        conditions = {
            'first_steps': lambda d: d.get('total_quizzes', 0) >= 1,
            'week_warrior': lambda d: d.get('streak', 0) >= 7,
            'month_master': lambda d: d.get('streak', 0) >= 30,
            'perfect_10': lambda d: d.get('perfect_quizzes', 0) >= 10,
            'vocab_hunter': lambda d: d.get('expressions_learned', 0) >= 100,
            'error_slayer': lambda d: d.get('errors_cleared', 0) >= 30,
        }
        checker = conditions.get(badge_id)
        return checker(check_data) if checker else False

    def check_badges(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check and award new badges.

        Args:
            state: Current state

        Returns:
            List of newly earned badges with details
        """
        earned = []
        current_badges = state.get('user', {}).get('badges', [])
        progress = state.get('progress', {})
        user = state.get('user', {})

        # Prepare badge check data
        check_data = {
            'total_quizzes': progress.get('total_quizzes', 0),
            'streak': user.get('streak', 0),
            'perfect_quizzes': progress.get('perfect_quizzes', 0),
            'expressions_learned': progress.get('expressions_learned', 0),
            'errors_cleared': sum(1 for e in state.get('error_notebook', []) if e.get('reviewed'))
        }

        for badge_id, badge_info in self.BADGES.items():
            if badge_id in current_badges:
                continue

            if self._check_badge_condition(badge_id, check_data):
                earned.append({
                    'id': badge_id,
                    'name': badge_info['name'],
                    'description': badge_info['description'],
                    'gem_reward': badge_info['gem_reward']
                })
                current_badges.append(badge_id)

        state['user']['badges'] = current_badges
        return earned

    def award_gems(self, state: Dict[str, Any], action: str, amount: int = 0) -> int:
        """
        Award gems for various actions.

        Args:
            state: Current state
            action: Type of action
            amount: Specific amount (overrides default)

        Returns:
            Number of gems awarded
        """
        GEM_REWARDS = {
            'quiz_complete': 5,
            'perfect_quiz': 10,
            'streak_milestone': 20,
            'level_up': 25,
            'badge_earned': 0,  # Use badge-specific amount
            'daily_goal': 15
        }

        gems = amount if amount > 0 else GEM_REWARDS.get(action, 0)
        state['user']['gems'] = state.get('user', {}).get('gems', 0) + gems

        return gems

    def spend_gems(self, state: Dict[str, Any], action: str) -> Tuple[bool, int]:
        """
        Spend gems on items.

        Args:
            state: Current state
            action: What to spend gems on

        Returns:
            Tuple of (success, gems_spent)
        """
        GEM_COSTS = {
            'streak_freeze': self.STREAK_FREEZE_COST,
            'hint': self.HINT_COST
        }

        cost = GEM_COSTS.get(action, 0)
        current_gems = state.get('user', {}).get('gems', 0)

        if current_gems >= cost:
            state['user']['gems'] = current_gems - cost

            if action == 'streak_freeze':
                state['user']['streak_freeze'] = state.get('user', {}).get('streak_freeze', 0) + 1

            return (True, cost)

        return (False, 0)

    def get_streak_multiplier(self, streak: int) -> float:
        """
        Calculate XP multiplier based on streak.

        Args:
            streak: Current streak days

        Returns:
            Multiplier (1.0 to 2.0)
        """
        return min(1.0 + (streak * 0.05), 2.0)

    def get_progress_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of user's progress.

        Args:
            state: Current state

        Returns:
            Summary dictionary
        """
        user = state.get('user', {})
        progress = state.get('progress', {})

        xp = user.get('xp', 0)
        level = user.get('level', 1)

        # Calculate XP to next level
        next_threshold = self.LEVEL_THRESHOLDS[min(level, 19)]
        current_threshold = self.LEVEL_THRESHOLDS[level - 1]
        xp_in_level = xp - current_threshold
        xp_to_next = next_threshold - xp if level < 20 else 0

        # Safe division for level progress
        threshold_diff = next_threshold - current_threshold
        if level < 20 and threshold_diff > 0:
            level_progress = (xp_in_level / threshold_diff) * 100
        else:
            level_progress = 100.0 if level >= 20 else 0.0

        return {
            'xp': xp,
            'level': level,
            'level_name': self.get_level_name(level),
            'xp_in_level': xp_in_level,
            'xp_to_next_level': xp_to_next,
            'level_progress': round(level_progress, 1),
            'streak': user.get('streak', 0),
            'streak_multiplier': self.get_streak_multiplier(user.get('streak', 0)),
            'gems': user.get('gems', 0),
            'badges': len(user.get('badges', [])),
            'total_badges': len(self.BADGES)
        }


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Gamification for eng-lang-tutor")
    parser.add_argument('--demo', action='store_true', help='Run demo')
    parser.add_argument('--state', type=str, help='Path to state JSON file')

    args = parser.parse_args()

    gm = GamificationManager()

    if args.demo:
        state = {
            "user": {
                "xp": 1250,
                "level": 7,
                "streak": 5,
                "streak_freeze": 2,
                "gems": 100,
                "badges": ["first_steps"]
            },
            "progress": {
                "total_quizzes": 15,
                "perfect_quizzes": 3,
                "expressions_learned": 45,
                "last_study_date": "2026-02-19"
            },
            "error_notebook": [
                {"reviewed": True}, {"reviewed": True}, {"reviewed": False}
            ]
        }

        print("=== Progress Summary ===")
        summary = gm.get_progress_summary(state)
        print(json.dumps(summary, indent=2))

        print("\n=== Update Streak (today: 2026-02-20) ===")
        streak, continued, msg = gm.update_streak(state, "2026-02-20")
        print(f"Streak: {streak}, Continued: {continued}, Message: {msg}")

        print("\n=== Check Badges ===")
        new_badges = gm.check_badges(state)
        print(f"New badges earned: {new_badges}")

    elif args.state:
        with open(args.state) as f:
            state = json.load(f)

        summary = gm.get_progress_summary(state)
        print(json.dumps(summary, indent=2))
