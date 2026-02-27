#!/usr/bin/env python3
"""
Scorer - Answer evaluation and XP calculation for eng-lang-tutor.

XP Rules (Duolingo-style):
- Correct answer: +10-15 XP (based on difficulty)
- Perfect quiz (100%): +20 bonus XP
- Streak multiplier: 1.0 + (streak_days * 0.05), max 2.0
- Wrong answer: 0 XP, add to error notebook
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from .constants import LEVEL_THRESHOLDS, calculate_level, get_streak_multiplier


class Scorer:
    """Handles answer evaluation and XP calculation."""

    # Base XP values by question type
    BASE_XP = {
        'multiple_choice': 10,
        'fill_blank': 12,
        'dialogue_completion': 15,
        'chinglish_fix': 15
    }

    # Bonus XP
    PERFECT_QUIZ_BONUS = 20

    def __init__(self, state_manager=None):
        """
        Initialize the scorer.

        Args:
            state_manager: Optional StateManager instance for state updates
        """
        self.state_manager = state_manager

    # Wrapper methods for backward compatibility with tests
    def calculate_level(self, xp: int) -> int:
        """Wrapper for calculate_level function."""
        return calculate_level(xp)

    def get_streak_multiplier(self, streak: int) -> float:
        """Wrapper for get_streak_multiplier function."""
        return get_streak_multiplier(streak)

    def evaluate_quiz(
        self,
        quiz: Dict[str, Any],
        user_answers: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Evaluate user answers and calculate XP.

        Args:
            quiz: Quiz dictionary with questions and correct answers
            user_answers: User's answers (question_id -> answer)
            state: Current state dictionary

        Returns:
            Tuple of (results, updated_state)
        """
        results = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'quiz_date': quiz.get('quiz_date', ''),
            'total_questions': len(quiz.get('questions', [])),
            'correct_count': 0,
            'wrong_count': 0,
            'base_xp': 0,
            'streak_multiplier': 1.0,
            'bonus_xp': 0,
            'total_xp_earned': 0,
            'accuracy': 0.0,
            'passed': False,
            'details': [],
            'errors': []
        }

        questions = quiz.get('questions', [])
        total_base_xp = 0
        correct_count = 0

        for question in questions:
            qid = str(question.get('id', ''))
            user_answer = user_answers.get(qid, '').strip()
            is_correct = self._check_answer(question, user_answer)

            question_type = question.get('type', 'multiple_choice')
            base_xp = self.BASE_XP.get(question_type, 10)

            detail = {
                'question_id': qid,
                'question_type': question_type,
                'user_answer': user_answer,
                'correct_answer': str(question.get('correct_answer', '')),
                'is_correct': is_correct,
                'base_xp': base_xp if is_correct else 0
            }

            if is_correct:
                total_base_xp += base_xp
                correct_count += 1
            else:
                # Record error
                results['errors'].append({
                    'question_id': qid,
                    'question': question.get('question', ''),
                    'question_type': question_type,
                    'user_answer': user_answer,
                    'correct_answer': question.get('correct_answer', ''),
                    'explanation': question.get('explanation', '')
                })

            results['details'].append(detail)

        # Calculate accuracy
        total_questions = len(questions)
        accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0

        # Calculate streak multiplier
        streak = state.get('user', {}).get('streak', 0)
        streak_multiplier = get_streak_multiplier(streak)

        # Calculate total XP with streak bonus
        total_xp = int(total_base_xp * streak_multiplier)

        # Perfect quiz bonus
        bonus_xp = 0
        if correct_count == total_questions and total_questions > 0:
            bonus_xp = self.PERFECT_QUIZ_BONUS
            total_xp += bonus_xp

        # Update results
        results['correct_count'] = correct_count
        results['wrong_count'] = total_questions - correct_count
        results['base_xp'] = total_base_xp
        results['streak_multiplier'] = streak_multiplier
        results['bonus_xp'] = bonus_xp
        results['total_xp_earned'] = total_xp
        results['accuracy'] = round(accuracy, 1)
        results['passed'] = accuracy >= quiz.get('passing_score', 70)

        # Update state
        updated_state = self._update_state(state, results)

        return results, updated_state

    def _check_answer(self, question: Dict[str, Any], user_answer: str) -> bool:
        """
        Check if user answer matches correct answer.

        Args:
            question: Question dictionary with correct_answer
            user_answer: User's answer string

        Returns:
            True if correct, False otherwise
        """
        correct = str(question.get('correct_answer', '')).strip()
        user = user_answer.strip()

        # Case-insensitive comparison
        return user.lower() == correct.lower()

    def _update_state(self, state: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update state with quiz results (modifies state in place).

        Args:
            state: Current state (will be modified)
            results: Quiz evaluation results

        Returns:
            The same state dict (for convenience)
        """
        # Update XP
        state['user']['xp'] = state.get('user', {}).get('xp', 0) + results['total_xp_earned']

        # Update progress
        progress = state.get('progress', {})
        old_total = progress.get('total_quizzes', 0)
        old_rate = progress.get('correct_rate', 0.0)

        # Update correct rate (running average)
        new_total = old_total + 1
        new_rate = ((old_rate * old_total) + results['accuracy']) / new_total

        progress['total_quizzes'] = new_total
        progress['correct_rate'] = round(new_rate, 1)
        progress['last_study_date'] = results['date']

        # Track perfect quizzes
        if results['accuracy'] == 100:
            progress['perfect_quizzes'] = progress.get('perfect_quizzes', 0) + 1

        state['progress'] = progress

        # Add errors to notebook
        if results['errors']:
            error_notebook = state.get('error_notebook', [])
            for error in results['errors']:
                error_entry = {
                    'date': results['date'],
                    'question': error.get('question', ''),
                    'user_answer': error.get('user_answer', ''),
                    'correct_answer': error.get('correct_answer', ''),
                    'explanation': error.get('explanation', ''),
                    'reviewed': False
                }
                error_notebook.append(error_entry)
            state['error_notebook'] = error_notebook

        return state

    def get_xp_for_next_level(self, current_xp: int) -> Tuple[int, int]:
        """
        Get XP needed for next level.

        Args:
            current_xp: Current total XP

        Returns:
            Tuple of (xp_needed, xp_into_current_level)
        """
        current_level = calculate_level(current_xp)

        if current_level >= 20:
            return (0, current_xp - LEVEL_THRESHOLDS[-1])

        next_threshold = LEVEL_THRESHOLDS[current_level]
        current_threshold = LEVEL_THRESHOLDS[current_level - 1]

        xp_needed = next_threshold - current_xp
        xp_into_level = current_xp - current_threshold

        return (xp_needed, xp_into_level)


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scorer for eng-lang-tutor")
    parser.add_argument('--quiz', type=str, help='Path to quiz JSON file')
    parser.add_argument('--answers', type=str, help='Path to user answers JSON file')
    parser.add_argument('--state', type=str, help='Path to state JSON file')
    parser.add_argument('--demo', action='store_true', help='Run demo')

    args = parser.parse_args()

    scorer = Scorer()

    if args.demo:
        # Demo quiz
        quiz = {
            "quiz_date": datetime.now().strftime('%Y-%m-%d'),
            "questions": [
                {"id": 1, "type": "multiple_choice", "correct_answer": "B", "xp_value": 10},
                {"id": 2, "type": "fill_blank", "correct_answer": "gonna", "xp_value": 12},
                {"id": 3, "type": "dialogue_completion", "correct_answer": "Touch base", "xp_value": 15}
            ],
            "passing_score": 70
        }

        # Demo answers (2 correct, 1 wrong)
        answers = {"1": "B", "2": "gonna", "3": "wrong answer"}

        # Demo state
        state = {
            "user": {"xp": 100, "streak": 5, "level": 2},
            "progress": {"total_quizzes": 10, "correct_rate": 75.0}
        }

        results, updated = scorer.evaluate_quiz(quiz, answers, state)
        print("Results:")
        print(json.dumps(results, indent=2))
        print("\nUpdated State (user section):")
        print(json.dumps(updated['user'], indent=2))
        print(json.dumps(updated['progress'], indent=2))

    elif args.quiz and args.answers and args.state:
        with open(args.quiz) as f:
            quiz = json.load(f)
        with open(args.answers) as f:
            answers = json.load(f)
        with open(args.state) as f:
            state = json.load(f)

        results, updated = scorer.evaluate_quiz(quiz, answers, state)
        print(json.dumps(results, indent=2))
