"""
Unit tests for scorer.py
"""

import pytest
from scripts.core.scorer import Scorer


class TestScorer:
    """Tests for Scorer class."""

    def test_check_answer_multiple_choice_correct(self):
        """Test correct multiple choice answer."""
        scorer = Scorer()
        question = {
            "type": "multiple_choice",
            "correct_answer": "B"
        }

        is_correct = scorer._check_answer(question, "B")
        assert is_correct is True

    def test_check_answer_multiple_choice_wrong(self):
        """Test wrong multiple choice answer."""
        scorer = Scorer()
        question = {
            "type": "multiple_choice",
            "correct_answer": "B"
        }

        is_correct = scorer._check_answer(question, "A")
        assert is_correct is False

    def test_check_answer_fill_blank_correct(self):
        """Test correct fill in blank answer."""
        scorer = Scorer()
        question = {
            "type": "fill_blank",
            "correct_answer": "touch base"
        }

        is_correct = scorer._check_answer(question, "touch base")
        assert is_correct is True

    def test_check_answer_fill_blank_case_insensitive(self):
        """Test fill blank is case insensitive."""
        scorer = Scorer()
        question = {
            "type": "fill_blank",
            "correct_answer": "touch base"
        }

        is_correct = scorer._check_answer(question, "Touch Base")
        assert is_correct is True

    def test_check_answer_fill_blank_whitespace(self):
        """Test fill blank handles extra whitespace."""
        scorer = Scorer()
        question = {
            "type": "fill_blank",
            "correct_answer": "touch base"
        }

        is_correct = scorer._check_answer(question, "  touch base  ")
        assert is_correct is True

    def test_check_answer_dialogue_completion_correct(self):
        """Test correct dialogue completion."""
        scorer = Scorer()
        question = {
            "type": "dialogue_completion",
            "correct_answer": "B"
        }

        is_correct = scorer._check_answer(question, "B")
        assert is_correct is True

    def test_check_answer_chinglish_fix_correct(self):
        """Test correct Chinglish fix."""
        scorer = Scorer()
        question = {
            "type": "chinglish_fix",
            "correct_answer": "touch base"
        }

        is_correct = scorer._check_answer(question, "touch base")
        assert is_correct is True

    def test_evaluate_quiz_all_correct(self, sample_quiz, sample_state):
        """Test evaluating a quiz with all correct answers."""
        scorer = Scorer()
        answers = {"1": "B", "2": "touch base", "3": "touch base"}

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert results["correct_count"] == 3
        assert results["total_questions"] == 3
        assert results["accuracy"] == 100.0
        assert results["base_xp"] == 37  # 10 + 15 + 12
        assert results["passed"] is True

    def test_evaluate_quiz_partial_correct(self, sample_quiz, sample_state):
        """Test evaluating a quiz with partial correct answers."""
        scorer = Scorer()
        answers = {
            "1": "B",      # correct
            "2": "wrong",  # wrong
            "3": "touch base"  # correct
        }

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert results["correct_count"] == 2
        assert results["total_questions"] == 3
        assert results["accuracy"] == pytest.approx(66.67, rel=0.01)
        assert results["base_xp"] == 22  # 10 + 0 + 12
        assert results["passed"] is False  # 66.67% < 70%

    def test_evaluate_quiz_all_wrong(self, sample_quiz, sample_state):
        """Test evaluating a quiz with all wrong answers."""
        scorer = Scorer()
        answers = {"1": "A", "2": "wrong", "3": "wrong"}

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert results["correct_count"] == 0
        assert results["accuracy"] == 0.0
        assert results["base_xp"] == 0
        assert results["passed"] is False

    def test_evaluate_quiz_with_streak_multiplier(self, sample_quiz):
        """Test streak multiplier affects XP."""
        scorer = Scorer()

        # No streak
        state1 = {"user": {"xp": 0, "streak": 0}, "progress": {}}
        answers = {"1": "B", "2": "touch base", "3": "touch base"}
        results1, _ = scorer.evaluate_quiz(sample_quiz, answers, state1)

        # With streak 10 (1.5x multiplier)
        state2 = {"user": {"xp": 0, "streak": 10}, "progress": {}}
        results2, _ = scorer.evaluate_quiz(sample_quiz, answers, state2)

        # Streak should give more XP
        assert results2["streak_multiplier"] == 1.5
        assert results2["total_xp_earned"] > results1["total_xp_earned"]

    def test_evaluate_quiz_perfect_bonus(self, sample_quiz, sample_state):
        """Test perfect quiz bonus."""
        scorer = Scorer()
        answers = {"1": "B", "2": "touch base", "3": "touch base"}

        results, _ = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert results["accuracy"] == 100.0
        assert results["bonus_xp"] == 20  # Perfect quiz bonus

    def test_evaluate_quiz_records_errors(self, sample_quiz, sample_state):
        """Test that wrong answers are recorded."""
        scorer = Scorer()
        answers = {"1": "A", "2": "wrong", "3": "touch base"}  # 2 wrong, 1 correct

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert len(results["errors"]) == 2  # 2 wrong answers
        assert len(updated_state["error_notebook"]) == 2

    def test_evaluate_quiz_updates_state_xp(self, sample_quiz, sample_state):
        """Test that XP is added to state."""
        scorer = Scorer()
        initial_xp = sample_state["user"]["xp"]
        answers = {"1": "B", "2": "touch base", "3": "touch base"}

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert updated_state["user"]["xp"] > initial_xp

    def test_evaluate_quiz_updates_progress(self, sample_quiz, sample_state):
        """Test that progress stats are updated."""
        scorer = Scorer()
        answers = {"1": "B", "2": "touch base", "3": "touch base"}

        results, updated_state = scorer.evaluate_quiz(sample_quiz, answers, sample_state)

        assert updated_state["progress"]["total_quizzes"] == 1
        assert updated_state["progress"]["last_study_date"] is not None

    def test_calculate_level_beginner(self):
        """Test level calculation for beginner XP."""
        scorer = Scorer()

        assert scorer.calculate_level(0) == 1
        assert scorer.calculate_level(50) == 2
        assert scorer.calculate_level(100) == 3
        assert scorer.calculate_level(350) == 5

    def test_calculate_level_intermediate(self):
        """Test level calculation for intermediate XP."""
        scorer = Scorer()

        assert scorer.calculate_level(550) == 6
        assert scorer.calculate_level(1000) == 7  # 1000 is between 800 and 1100
        assert scorer.calculate_level(2000) == 10

    def test_calculate_level_advanced(self):
        """Test level calculation for advanced XP."""
        scorer = Scorer()

        assert scorer.calculate_level(2600) == 11
        assert scorer.calculate_level(5000) == 14
        assert scorer.calculate_level(6000) == 15

    def test_calculate_level_expert(self):
        """Test level calculation for expert XP."""
        scorer = Scorer()

        assert scorer.calculate_level(7200) == 16
        assert scorer.calculate_level(10000) == 18
        assert scorer.calculate_level(15000) == 20

    def test_get_xp_for_next_level(self):
        """Test XP needed for next level calculation."""
        scorer = Scorer()

        # Level 1 with 0 XP -> need 50 for level 2
        needed, into = scorer.get_xp_for_next_level(0)
        assert needed == 50
        assert into == 0

        # Level 1 with 25 XP -> need 25 more for level 2
        needed, into = scorer.get_xp_for_next_level(25)
        assert needed == 25
        assert into == 25

    def test_get_xp_for_next_level_max(self):
        """Test XP for next level at max level."""
        scorer = Scorer()

        # At max level, no XP needed
        needed, into = scorer.get_xp_for_next_level(20000)
        assert needed == 0

    def test_xp_values_by_type(self, sample_state):
        """Test XP values for different question types."""
        scorer = Scorer()

        # multiple_choice: 10 XP
        quiz1 = {"quiz_date": "2026-02-20", "questions": [{"id": 1, "type": "multiple_choice", "correct_answer": "A"}], "passing_score": 70}
        results1, _ = scorer.evaluate_quiz(quiz1, {"1": "A"}, sample_state)
        assert results1["base_xp"] == 10

        # fill_blank: 12 XP
        quiz2 = {"quiz_date": "2026-02-20", "questions": [{"id": 1, "type": "fill_blank", "correct_answer": "test"}], "passing_score": 70}
        results2, _ = scorer.evaluate_quiz(quiz2, {"1": "test"}, sample_state)
        assert results2["base_xp"] == 12

        # dialogue_completion: 15 XP
        quiz3 = {"quiz_date": "2026-02-20", "questions": [{"id": 1, "type": "dialogue_completion", "correct_answer": "A"}], "passing_score": 70}
        results3, _ = scorer.evaluate_quiz(quiz3, {"1": "A"}, sample_state)
        assert results3["base_xp"] == 15

        # chinglish_fix: 15 XP
        quiz4 = {"quiz_date": "2026-02-20", "questions": [{"id": 1, "type": "chinglish_fix", "correct_answer": "test"}], "passing_score": 70}
        results4, _ = scorer.evaluate_quiz(quiz4, {"1": "test"}, sample_state)
        assert results4["base_xp"] == 15

    def test_streak_multiplier_cap(self):
        """Test streak multiplier is capped at 2.0."""
        scorer = Scorer()

        # High streak should cap at 2.0
        state = {"user": {"xp": 0, "streak": 100}, "progress": {}}
        quiz = {"quiz_date": "2026-02-20", "questions": [{"id": 1, "type": "multiple_choice", "correct_answer": "A"}], "passing_score": 70}

        results, _ = scorer.evaluate_quiz(quiz, {"1": "A"}, state)

        assert results["streak_multiplier"] == 2.0  # Capped
