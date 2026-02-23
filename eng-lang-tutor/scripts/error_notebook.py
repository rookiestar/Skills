#!/usr/bin/env python3
"""
Error Notebook Manager - 错题本管理

管理用户的错题本功能，包括：
- 添加错题
- 分页查询
- 统计信息
- 复习标记
- 自动归档

从 state_manager.py 提取，遵循单一职责原则。
"""

from typing import Dict, Any, List
from datetime import datetime, date
from collections import Counter


class ErrorNotebookManager:
    """错题本管理器"""

    # Maximum size for error notebook before auto-archiving
    MAX_ERROR_NOTEBOOK_SIZE = 100

    def __init__(self, state_manager=None):
        """
        初始化错题本管理器

        Args:
            state_manager: StateManager 实例，用于事件日志
        """
        self.state_manager = state_manager

    def add_to_error_notebook(self, state: Dict[str, Any],
                               error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an error to the error notebook.

        Args:
            state: Current state
            error: Error entry with date, question, user_answer, correct_answer, explanation

        Returns:
            Updated state
        """
        error['date'] = date.today().isoformat()
        error['reviewed'] = False
        error['wrong_count'] = error.get('wrong_count', 1)
        # keypoint_date and question_type are optional

        errors = state.get('error_notebook', [])
        errors.append(error)

        # Auto-archive oldest if over size limit
        if len(errors) > self.MAX_ERROR_NOTEBOOK_SIZE:
            # Sort by date to find oldest
            errors.sort(key=lambda x: x.get('date', ''))
            # Archive the oldest
            oldest = errors.pop(0)
            archive = state.get('error_archive', [])
            oldest['archived_at'] = date.today().isoformat()
            oldest['archived_reason'] = 'notebook_full'
            archive.append(oldest)
            state['error_archive'] = archive

        state['error_notebook'] = errors
        return state

    def get_errors_page(self, state: Dict[str, Any],
                        page: int = 1,
                        per_page: int = 5,
                        month: str = None,
                        random: int = None) -> Dict[str, Any]:
        """
        Get paginated errors from the error notebook.

        Args:
            state: Current state
            page: Page number (1-indexed)
            per_page: Items per page (default 5)
            month: Filter by month (YYYY-MM format)
            random: Return N random errors instead of paginated

        Returns:
            Dictionary with pagination info and error items:
            {
                'total': total_count,
                'page': current_page,
                'per_page': items_per_page,
                'total_pages': total_pages,
                'has_more': bool,
                'errors': [error_items]
            }
        """
        import random as random_module

        errors = state.get('error_notebook', [])

        # Sort by date descending (newest first)
        errors = sorted(errors, key=lambda x: x.get('date', ''), reverse=True)

        # Filter by month if specified
        if month:
            errors = [e for e in errors if e.get('date', '').startswith(month)]

        total = len(errors)

        # Random mode
        if random and random > 0:
            random_count = min(random, total)
            selected = random_module.sample(errors, random_count) if total > 0 else []
            return {
                'total': total,
                'page': 1,
                'per_page': random_count,
                'total_pages': 1,
                'has_more': total > random_count,
                'mode': 'random',
                'errors': selected
            }

        # Pagination
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        start = (page - 1) * per_page
        end = start + per_page

        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_more': page < total_pages,
            'has_prev': page > 1,
            'mode': 'paginated',
            'errors': errors[start:end]
        }

    def get_error_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about the error notebook.

        Args:
            state: Current state

        Returns:
            Dictionary with error statistics
        """
        errors = state.get('error_notebook', [])

        if not errors:
            return {
                'total': 0,
                'reviewed': 0,
                'unreviewed': 0,
                'by_month': {}
            }

        reviewed = sum(1 for e in errors if e.get('reviewed', False))
        unreviewed = len(errors) - reviewed

        # Group by month
        by_month = Counter()
        for e in errors:
            date_str = e.get('date', '')
            if date_str:
                month = date_str[:7]  # YYYY-MM
                by_month[month] += 1

        # Sort by month descending
        by_month_sorted = dict(sorted(by_month.items(), reverse=True))

        return {
            'total': len(errors),
            'reviewed': reviewed,
            'unreviewed': unreviewed,
            'by_month': by_month_sorted
        }

    def review_error(self, state: Dict[str, Any], error_index: int,
                     correct: bool) -> Dict[str, Any]:
        """
        Mark an error as reviewed (correct answer) or increment wrong count.

        Args:
            state: Current state
            error_index: Index of error in error_notebook
            correct: Whether the user answered correctly

        Returns:
            Updated state
        """
        errors = state.get('error_notebook', [])
        if 0 <= error_index < len(errors):
            if correct:
                # Mark as reviewed - contributes to Error Slayer badge
                errors[error_index]['reviewed'] = True
            else:
                # Increment wrong count
                errors[error_index]['wrong_count'] = errors[error_index].get('wrong_count', 1) + 1
            state['error_notebook'] = errors
        return state

    def increment_wrong_count(self, state: Dict[str, Any],
                              error_index: int) -> Dict[str, Any]:
        """
        Increment wrong count for an error (convenience method).

        Args:
            state: Current state
            error_index: Index of error in error_notebook

        Returns:
            Updated state
        """
        return self.review_error(state, error_index, correct=False)

    def get_review_errors(self, state: Dict[str, Any],
                          count: int = 5) -> List[Dict[str, Any]]:
        """
        Get unreviewed errors for a review session.

        Args:
            state: Current state
            count: Maximum number of errors to return

        Returns:
            List of unreviewed errors (most recent first)
        """
        errors = state.get('error_notebook', [])
        # Filter unreviewed errors
        unreviewed = [e for e in errors if not e.get('reviewed', False)]
        # Sort by date descending (newest first)
        unreviewed = sorted(unreviewed, key=lambda x: x.get('date', ''), reverse=True)
        # Return up to count items
        return unreviewed[:count]

    def archive_stale_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Archive errors with wrong_count >= 3 and over 30 days old.

        Args:
            state: Current state

        Returns:
            Updated state with stale errors moved to error_archive
        """
        errors = state.get('error_notebook', [])
        archive = state.get('error_archive', [])
        today = date.today()

        remaining = []
        archived_count = 0

        for error in errors:
            # Skip already reviewed
            if error.get('reviewed', False):
                remaining.append(error)
                continue

            wrong_count = error.get('wrong_count', 1)
            error_date_str = error.get('date', '')

            # Calculate days since error was created
            try:
                error_date = datetime.strptime(error_date_str, '%Y-%m-%d').date()
                days_old = (today - error_date).days
            except (ValueError, TypeError):
                days_old = 0

            # Archive if wrong_count >= 3 and over 30 days old
            if wrong_count >= 3 and days_old >= 30:
                error['archived_at'] = today.isoformat()
                archive.append(error)
                archived_count += 1
            else:
                remaining.append(error)

        state['error_notebook'] = remaining
        state['error_archive'] = archive

        # Log archival event via state_manager
        if archived_count > 0 and self.state_manager:
            self.state_manager.append_event("errors_archived", {"count": archived_count})

        return state

    def clear_reviewed_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove reviewed errors from the notebook (keep them in archive for stats).

        Args:
            state: Current state

        Returns:
            Updated state
        """
        errors = state.get('error_notebook', [])
        # Keep only unreviewed errors
        state['error_notebook'] = [
            e for e in errors if not e.get('reviewed', False)
        ]
        return state
