#!/usr/bin/env python3
"""
Tests for ErrorNotebookManager
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from scripts.core.error_notebook import ErrorNotebookManager


class TestErrorNotebookManager:
    """Tests for ErrorNotebookManager class."""

    @pytest.fixture
    def manager(self):
        """Create an ErrorNotebookManager instance."""
        return ErrorNotebookManager()

    @pytest.fixture
    def manager_with_state_manager(self):
        """Create an ErrorNotebookManager with mock state_manager."""
        mock_sm = MagicMock()
        return ErrorNotebookManager(state_manager=mock_sm)

    @pytest.fixture
    def state_with_errors(self):
        """Create a state with some errors."""
        return {
            "error_notebook": [
                {
                    "date": "2026-02-20",
                    "question": "What does 'touch base' mean?",
                    "user_answer": "A. Formal meeting",
                    "correct_answer": "B. Quick check-in",
                    "explanation": "'Touch base' means a brief check-in.",
                    "reviewed": False,
                    "wrong_count": 1
                },
                {
                    "date": "2026-02-19",
                    "question": "Fix: 'I want to communicate with you'",
                    "user_answer": "talk to you",
                    "correct_answer": "touch base",
                    "explanation": "Use 'touch base' for quick check-ins.",
                    "reviewed": True,
                    "wrong_count": 1
                },
                {
                    "date": "2026-02-18",
                    "question": "Complete: Let's ___ on the project.",
                    "user_answer": "discuss",
                    "correct_answer": "touch base",
                    "explanation": "'Touch base' is the natural expression.",
                    "reviewed": False,
                    "wrong_count": 2
                }
            ],
            "error_archive": []
        }

    # === add_to_error_notebook tests ===

    def test_add_error_basic(self, manager):
        """Test adding a basic error to empty notebook."""
        state = {"error_notebook": []}
        error = {
            "question": "Test question?",
            "user_answer": "Wrong",
            "correct_answer": "Right",
            "explanation": "Explanation here"
        }

        result = manager.add_to_error_notebook(state, error)

        assert len(result["error_notebook"]) == 1
        added = result["error_notebook"][0]
        assert added["question"] == "Test question?"
        assert added["date"] == date.today().isoformat()
        assert added["reviewed"] is False
        assert added["wrong_count"] == 1

    def test_add_error_preserves_wrong_count(self, manager):
        """Test that wrong_count is preserved if provided."""
        state = {"error_notebook": []}
        error = {
            "question": "Test?",
            "user_answer": "Wrong",
            "correct_answer": "Right",
            "explanation": "Exp",
            "wrong_count": 3
        }

        result = manager.add_to_error_notebook(state, error)
        assert result["error_notebook"][0]["wrong_count"] == 3

    def test_add_error_auto_archive(self, manager):
        """Test auto-archiving when notebook exceeds max size."""
        state = {
            "error_notebook": [
                {"date": f"2026-01-{i:02d}", "question": f"Q{i}", "reviewed": False}
                for i in range(1, 101)  # 100 errors (at max)
            ],
            "error_archive": []
        }

        error = {
            "question": "New error",
            "user_answer": "Wrong",
            "correct_answer": "Right",
            "explanation": "Exp"
        }

        result = manager.add_to_error_notebook(state, error)

        # Should still have 100 errors (one archived, one added)
        assert len(result["error_notebook"]) == 100
        # Should have one archived error
        assert len(result["error_archive"]) == 1
        assert result["error_archive"][0]["archived_reason"] == "notebook_full"

    # === get_errors_page tests ===

    def test_get_errors_page_basic(self, manager, state_with_errors):
        """Test basic pagination."""
        result = manager.get_errors_page(state_with_errors, page=1, per_page=2)

        assert result["total"] == 3
        assert result["page"] == 1
        assert result["per_page"] == 2
        assert result["total_pages"] == 2
        assert result["has_more"] is True
        assert len(result["errors"]) == 2

    def test_get_errors_page_second_page(self, manager, state_with_errors):
        """Test second page of pagination."""
        result = manager.get_errors_page(state_with_errors, page=2, per_page=2)

        assert result["page"] == 2
        assert result["has_more"] is False
        assert len(result["errors"]) == 1

    def test_get_errors_page_sorted_descending(self, manager, state_with_errors):
        """Test that errors are sorted by date descending."""
        result = manager.get_errors_page(state_with_errors, page=1, per_page=10)

        dates = [e["date"] for e in result["errors"]]
        assert dates == ["2026-02-20", "2026-02-19", "2026-02-18"]

    def test_get_errors_page_filter_by_month(self, manager, state_with_errors):
        """Test filtering by month."""
        result = manager.get_errors_page(state_with_errors, month="2026-02")

        assert result["total"] == 3

        # Add an error from different month
        state_with_errors["error_notebook"].append({
            "date": "2026-01-15",
            "question": "Old question"
        })
        result = manager.get_errors_page(state_with_errors, month="2026-01")
        assert result["total"] == 1

    def test_get_errors_page_random(self, manager, state_with_errors):
        """Test random selection mode."""
        result = manager.get_errors_page(state_with_errors, random=2)

        assert result["mode"] == "random"
        assert len(result["errors"]) == 2
        assert result["total"] == 3  # Total available

    def test_get_errors_page_empty(self, manager):
        """Test with empty notebook."""
        state = {"error_notebook": []}
        result = manager.get_errors_page(state)

        assert result["total"] == 0
        assert result["errors"] == []

    # === get_error_stats tests ===

    def test_get_error_stats_basic(self, manager, state_with_errors):
        """Test basic statistics."""
        result = manager.get_error_stats(state_with_errors)

        assert result["total"] == 3
        assert result["reviewed"] == 1
        assert result["unreviewed"] == 2
        assert "2026-02" in result["by_month"]
        assert result["by_month"]["2026-02"] == 3

    def test_get_error_stats_empty(self, manager):
        """Test statistics with empty notebook."""
        state = {"error_notebook": []}
        result = manager.get_error_stats(state)

        assert result["total"] == 0
        assert result["reviewed"] == 0
        assert result["unreviewed"] == 0
        assert result["by_month"] == {}

    # === review_error tests ===

    def test_review_error_correct(self, manager, state_with_errors):
        """Test marking error as reviewed (correct)."""
        result = manager.review_error(state_with_errors, 0, correct=True)

        assert result["error_notebook"][0]["reviewed"] is True

    def test_review_error_wrong(self, manager, state_with_errors):
        """Test incrementing wrong count."""
        result = manager.review_error(state_with_errors, 0, correct=False)

        assert result["error_notebook"][0]["wrong_count"] == 2  # Was 1

    def test_review_error_invalid_index(self, manager, state_with_errors):
        """Test with invalid index (should not crash)."""
        original = state_with_errors.copy()
        result = manager.review_error(state_with_errors, 999, correct=True)

        # Should return unchanged state
        assert result["error_notebook"] == original["error_notebook"]

    # === get_review_errors tests ===

    def test_get_review_errors(self, manager, state_with_errors):
        """Test getting unreviewed errors for review session."""
        result = manager.get_review_errors(state_with_errors, count=5)

        assert len(result) == 2  # 2 unreviewed
        # Should be sorted by date descending
        assert result[0]["date"] == "2026-02-20"

    def test_get_review_errors_limited(self, manager, state_with_errors):
        """Test limiting review errors count."""
        result = manager.get_review_errors(state_with_errors, count=1)

        assert len(result) == 1

    # === archive_stale_errors tests ===

    def test_archive_stale_errors_basic(self, manager):
        """Test archiving stale errors."""
        old_date = (date.today() - timedelta(days=31)).isoformat()
        state = {
            "error_notebook": [
                {
                    "date": old_date,
                    "question": "Old stubborn error",
                    "wrong_count": 3,
                    "reviewed": False
                },
                {
                    "date": "2026-02-20",
                    "question": "Recent error",
                    "wrong_count": 3,
                    "reviewed": False
                }
            ],
            "error_archive": []
        }

        result = manager.archive_stale_errors(state)

        assert len(result["error_notebook"]) == 1
        assert len(result["error_archive"]) == 1
        assert result["error_archive"][0]["archived_at"] == date.today().isoformat()

    def test_archive_stale_errors_preserves_reviewed(self, manager):
        """Test that reviewed errors are not archived."""
        old_date = (date.today() - timedelta(days=31)).isoformat()
        state = {
            "error_notebook": [
                {
                    "date": old_date,
                    "question": "Old but reviewed",
                    "wrong_count": 3,
                    "reviewed": True
                }
            ],
            "error_archive": []
        }

        result = manager.archive_stale_errors(state)

        # Reviewed errors should remain in notebook
        assert len(result["error_notebook"]) == 1
        assert len(result["error_archive"]) == 0

    def test_archive_stale_errors_logs_event(self, manager_with_state_manager):
        """Test that archiving logs event via state_manager."""
        old_date = (date.today() - timedelta(days=31)).isoformat()
        state = {
            "error_notebook": [
                {
                    "date": old_date,
                    "question": "Old error",
                    "wrong_count": 3,
                    "reviewed": False
                }
            ],
            "error_archive": []
        }

        manager_with_state_manager.archive_stale_errors(state)

        # Should have called append_event
        manager_with_state_manager.state_manager.append_event.assert_called_once()
        call_args = manager_with_state_manager.state_manager.append_event.call_args
        assert call_args[0][0] == "errors_archived"
        assert call_args[0][1]["count"] == 1

    # === clear_reviewed_errors tests ===

    def test_clear_reviewed_errors(self, manager, state_with_errors):
        """Test clearing reviewed errors."""
        result = manager.clear_reviewed_errors(state_with_errors)

        assert len(result["error_notebook"]) == 2  # Only unreviewed remain
        for error in result["error_notebook"]:
            assert error["reviewed"] is False

    # === increment_wrong_count tests ===

    def test_increment_wrong_count(self, manager, state_with_errors):
        """Test convenience method for incrementing wrong count."""
        result = manager.increment_wrong_count(state_with_errors, 0)

        assert result["error_notebook"][0]["wrong_count"] == 2
