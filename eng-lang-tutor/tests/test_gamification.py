"""
Unit tests for gamification.py
"""

import pytest
from datetime import date, timedelta
from gamification import GamificationManager


class TestGamificationManager:
    """Tests for GamificationManager class."""

    # === Streak Tests ===

    def test_update_streak_first_study(self, sample_state):
        """Test streak on first study day."""
        gm = GamificationManager()
        streak, continued, msg = gm.update_streak(sample_state, "2026-02-20")

        assert streak == 1
        assert continued is True
        assert "Started" in msg

    def test_update_streak_consecutive_day(self, sample_state):
        """Test streak continues on consecutive day."""
        gm = GamificationManager()
        sample_state["progress"]["last_study_date"] = "2026-02-19"
        sample_state["user"]["streak"] = 3

        streak, continued, msg = gm.update_streak(sample_state, "2026-02-20")

        assert streak == 4
        assert continued is True
        assert "continued" in msg.lower()

    def test_update_streak_same_day(self, sample_state):
        """Test streak doesn't change on same day."""
        gm = GamificationManager()
        sample_state["progress"]["last_study_date"] = "2026-02-20"
        sample_state["user"]["streak"] = 5

        streak, continued, msg = gm.update_streak(sample_state, "2026-02-20")

        assert streak == 5
        assert continued is False
        assert "Already" in msg

    def test_update_streak_broken(self, sample_state):
        """Test streak breaks after missing a day."""
        gm = GamificationManager()
        sample_state["progress"]["last_study_date"] = "2026-02-18"
        sample_state["user"]["streak"] = 10

        streak, continued, msg = gm.update_streak(sample_state, "2026-02-20")

        assert streak == 1
        assert continued is False
        assert "broken" in msg.lower()

    def test_update_streak_freeze_used(self, sample_state):
        """Test streak freeze is used when available."""
        gm = GamificationManager()
        sample_state["progress"]["last_study_date"] = "2026-02-18"
        sample_state["user"]["streak"] = 10
        sample_state["user"]["streak_freeze"] = 1

        streak, continued, msg = gm.update_streak(sample_state, "2026-02-20")

        assert streak == 11
        assert continued is True
        assert "freeze" in msg.lower()
        assert sample_state["user"]["streak_freeze"] == 0

    # === Level Tests ===

    def test_calculate_level_beginner(self):
        """Test level calculation for beginner XP."""
        gm = GamificationManager()

        assert gm.calculate_level(0) == 1
        assert gm.calculate_level(50) == 2
        assert gm.calculate_level(100) == 3
        assert gm.calculate_level(350) == 5

    def test_calculate_level_intermediate(self):
        """Test level calculation for intermediate XP."""
        gm = GamificationManager()

        assert gm.calculate_level(550) == 6
        assert gm.calculate_level(1000) == 7  # 1000 is between 800 (level 7) and 1100 (level 8)
        assert gm.calculate_level(2000) == 10

    def test_calculate_level_advanced(self):
        """Test level calculation for advanced XP."""
        gm = GamificationManager()

        assert gm.calculate_level(2600) == 11
        assert gm.calculate_level(5000) == 14
        assert gm.calculate_level(6000) == 15

    def test_calculate_level_expert(self):
        """Test level calculation for expert XP."""
        gm = GamificationManager()

        assert gm.calculate_level(7200) == 16
        assert gm.calculate_level(10000) == 18
        assert gm.calculate_level(15000) == 20

    def test_get_level_name(self):
        """Test level name mapping (Activity Level stages)."""
        gm = GamificationManager()

        assert gm.get_level_name(1) == "Starter"
        assert gm.get_level_name(5) == "Starter"
        assert gm.get_level_name(6) == "Traveler"
        assert gm.get_level_name(10) == "Traveler"
        assert gm.get_level_name(11) == "Explorer"
        assert gm.get_level_name(15) == "Explorer"
        assert gm.get_level_name(16) == "Pioneer"
        assert gm.get_level_name(20) == "Pioneer"

    def test_check_level_up(self):
        """Test level up detection."""
        gm = GamificationManager()

        # No level up
        leveled, level = gm.check_level_up(50, 80)
        assert leveled is False
        assert level is None

        # Level up
        leveled, level = gm.check_level_up(50, 100)
        assert leveled is True
        assert level == 3  # 100 XP = level 3

    def test_update_level(self, sample_state):
        """Test updating level in state."""
        gm = GamificationManager()
        sample_state["user"]["xp"] = 550

        level, leveled_up = gm.update_level(sample_state)

        assert level == 6
        assert leveled_up is True
        assert sample_state["user"]["level"] == 6

    # === Badge Tests ===

    def test_check_badges_first_steps(self, sample_state):
        """Test First Steps badge (first quiz)."""
        gm = GamificationManager()
        sample_state["progress"]["total_quizzes"] = 1

        badges = gm.check_badges(sample_state)

        assert len(badges) == 1
        assert badges[0]["id"] == "first_steps"
        assert "first_steps" in sample_state["user"]["badges"]

    def test_check_badges_week_warrior(self, sample_state):
        """Test Week Warrior badge (7-day streak)."""
        gm = GamificationManager()
        sample_state["user"]["streak"] = 7

        badges = gm.check_badges(sample_state)

        assert any(b["id"] == "week_warrior" for b in badges)

    def test_check_badges_month_master(self, sample_state):
        """Test Month Master badge (30-day streak)."""
        gm = GamificationManager()
        sample_state["user"]["streak"] = 30

        badges = gm.check_badges(sample_state)

        assert any(b["id"] == "month_master" for b in badges)

    def test_check_badges_perfect_10(self, sample_state):
        """Test Perfect 10 badge (10 perfect quizzes)."""
        gm = GamificationManager()
        sample_state["progress"]["perfect_quizzes"] = 10

        badges = gm.check_badges(sample_state)

        assert any(b["id"] == "perfect_10" for b in badges)

    def test_check_badges_vocab_hunter(self, sample_state):
        """Test Vocab Hunter badge (100 expressions)."""
        gm = GamificationManager()
        sample_state["progress"]["expressions_learned"] = 100

        badges = gm.check_badges(sample_state)

        assert any(b["id"] == "vocab_hunter" for b in badges)

    def test_check_badges_no_duplicate(self, sample_state):
        """Test badges aren't awarded twice."""
        gm = GamificationManager()
        sample_state["user"]["badges"] = ["first_steps"]
        sample_state["progress"]["total_quizzes"] = 1

        badges = gm.check_badges(sample_state)

        assert len(badges) == 0

    # === Gem Tests ===

    def test_award_gems_quiz_complete(self, sample_state):
        """Test awarding gems for quiz completion."""
        gm = GamificationManager()

        gems = gm.award_gems(sample_state, "quiz_complete")

        assert gems == 5
        assert sample_state["user"]["gems"] == 5

    def test_award_gems_perfect_quiz(self, sample_state):
        """Test awarding gems for perfect quiz."""
        gm = GamificationManager()

        gems = gm.award_gems(sample_state, "perfect_quiz")

        assert gems == 10

    def test_award_gems_level_up(self, sample_state):
        """Test awarding gems for level up."""
        gm = GamificationManager()

        gems = gm.award_gems(sample_state, "level_up")

        assert gems == 25

    def test_award_gems_custom_amount(self, sample_state):
        """Test awarding custom gem amount."""
        gm = GamificationManager()

        gems = gm.award_gems(sample_state, "badge_earned", amount=50)

        assert gems == 50
        assert sample_state["user"]["gems"] == 50

    def test_spend_gems_streak_freeze(self, sample_state):
        """Test spending gems on streak freeze."""
        gm = GamificationManager()
        sample_state["user"]["gems"] = 100

        success, cost = gm.spend_gems(sample_state, "streak_freeze")

        assert success is True
        assert cost == 50
        assert sample_state["user"]["gems"] == 50
        assert sample_state["user"]["streak_freeze"] == 1

    def test_spend_gems_insufficient(self, sample_state):
        """Test spending gems with insufficient balance."""
        gm = GamificationManager()
        sample_state["user"]["gems"] = 10

        success, cost = gm.spend_gems(sample_state, "streak_freeze")

        assert success is False
        assert cost == 0
        assert sample_state["user"]["gems"] == 10

    # === Multiplier Tests ===

    def test_get_streak_multiplier(self):
        """Test streak multiplier calculation."""
        gm = GamificationManager()

        assert gm.get_streak_multiplier(0) == 1.0
        assert gm.get_streak_multiplier(5) == 1.25
        assert gm.get_streak_multiplier(10) == 1.5
        assert gm.get_streak_multiplier(20) == 2.0
        assert gm.get_streak_multiplier(100) == 2.0  # capped

    # === Progress Summary Tests ===

    def test_get_progress_summary(self, sample_state):
        """Test getting progress summary."""
        gm = GamificationManager()
        sample_state["user"]["xp"] = 550
        sample_state["user"]["level"] = 6
        sample_state["user"]["streak"] = 5
        sample_state["user"]["gems"] = 50

        summary = gm.get_progress_summary(sample_state)

        assert summary["xp"] == 550
        assert summary["level"] == 6
        assert summary["level_name"] == "Traveler"
        assert summary["streak"] == 5
        assert summary["streak_multiplier"] == 1.25
        assert summary["gems"] == 50

    def test_get_progress_summary_xp_to_next_level(self, sample_state):
        """Test XP to next level calculation."""
        gm = GamificationManager()
        sample_state["user"]["xp"] = 150  # Level 3, in the middle of the level (100-200)
        sample_state["user"]["level"] = 3

        summary = gm.get_progress_summary(sample_state)

        assert summary["level"] == 3
        assert summary["xp_to_next_level"] == 50  # 200 - 150
        assert 0 < summary["level_progress"] < 100
