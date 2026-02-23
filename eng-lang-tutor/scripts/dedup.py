#!/usr/bin/env python3
"""
Deduplication - Prevents repeated content within 14-day window for eng-lang-tutor.

Methods:
1. Topic fingerprint matching
2. Expression similarity check
3. Phrase root matching
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import re


class DeduplicationManager:
    """Manages content deduplication to avoid repetitive learning."""

    def __init__(self, lookback_days: int = 14):
        """
        Initialize the deduplication manager.

        Args:
            lookback_days: Number of days to look back for duplicates
        """
        self.lookback_days = lookback_days

    def get_excluded_topics(self, state: Dict[str, Any]) -> List[str]:
        """
        Get topic fingerprints from recent days.

        Args:
            state: Current state with recent_topics

        Returns:
            List of topic fingerprints to exclude
        """
        recent = state.get('recent_topics', [])
        # Return last 50 topics (or all if fewer)
        return recent[-50:] if len(recent) > 50 else recent

    def check_duplicate(
        self,
        new_content: Dict[str, Any],
        recent_content: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        Check if new content duplicates recent content.

        Args:
            new_content: New knowledge point to check
            recent_content: List of recent knowledge points

        Returns:
            Tuple of (is_duplicate, reason)
        """
        new_fingerprint = new_content.get('topic_fingerprint', '')

        # Check fingerprint match
        for old in recent_content:
            if old.get('topic_fingerprint') == new_fingerprint:
                return (True, f"Topic fingerprint matches: {new_fingerprint}")

        # Check expression overlap
        new_expressions = self._extract_expressions(new_content)
        for old in recent_content:
            old_expressions = self._extract_expressions(old)
            overlap = new_expressions & old_expressions

            # If more than 50% overlap, consider it duplicate
            if len(overlap) > 0:
                overlap_ratio = len(overlap) / max(len(new_expressions), 1)
                if overlap_ratio > 0.5:
                    return (True, f"Expression overlap: {overlap}")

        # Check phrase root similarity
        new_roots = self._extract_phrase_roots(new_content)
        for old in recent_content:
            old_roots = self._extract_phrase_roots(old)
            root_overlap = new_roots & old_roots

            if len(root_overlap) >= 2:
                return (True, f"Phrase root overlap: {root_overlap}")

        return (False, "")

    def _extract_expressions(self, content: Dict[str, Any]) -> Set[str]:
        """
        Extract normalized expressions from content.

        Args:
            content: Knowledge point content

        Returns:
            Set of normalized expression strings
        """
        expressions = set()

        # Main expressions
        for expr in content.get('expressions', []):
            phrase = expr.get('phrase', '').lower().strip()
            # Normalize: remove punctuation, collapse whitespace
            normalized = re.sub(r'[^\w\s]', '', phrase)
            normalized = ' '.join(normalized.split())
            if normalized:
                expressions.add(normalized)

        # Alternatives
        for alt in content.get('alternatives', []):
            normalized = re.sub(r'[^\w\s]', '', alt.lower())
            normalized = ' '.join(normalized.split())
            if normalized:
                expressions.add(normalized)

        return expressions

    def _extract_phrase_roots(self, content: Dict[str, Any]) -> Set[str]:
        """
        Extract phrase roots/concepts from content.

        Args:
            content: Knowledge point content

        Returns:
            Set of phrase root strings
        """
        roots = set()

        # From fingerprint
        fingerprint = content.get('topic_fingerprint', '')
        if fingerprint:
            # Split by underscore and get key concepts
            parts = fingerprint.split('_')
            for part in parts:
                if len(part) > 3:  # Skip short words
                    roots.add(part)

        # From expressions (first significant word)
        for expr in content.get('expressions', []):
            phrase = expr.get('phrase', '').lower()
            words = phrase.split()
            for word in words:
                # Skip common words
                if word not in ['the', 'a', 'an', 'to', 'for', 'and', 'or', 'is', 'are']:
                    if len(word) > 3:
                        roots.add(word)
                        break

        return roots

    def add_to_recent_topics(self, state: Dict[str, Any],
                              fingerprint: str) -> Dict[str, Any]:
        """
        Add a topic fingerprint to recent topics list.

        Args:
            state: Current state
            fingerprint: Topic fingerprint to add

        Returns:
            Updated state
        """
        recent = state.get('recent_topics', [])
        recent.append(fingerprint)

        # Keep only last 50
        state['recent_topics'] = recent[-50:]
        return state

    def generate_excluded_list_prompt(self, excluded_topics: List[str]) -> str:
        """
        Generate a prompt-friendly list of excluded topics.

        Args:
            excluded_topics: List of topic fingerprints

        Returns:
            Formatted string for LLM prompt
        """
        if not excluded_topics:
            return "None (first content or no recent topics)"

        # Group by prefix (e.g., "asking_", "workplace_")
        grouped = {}
        for topic in excluded_topics:
            parts = topic.split('_')
            if len(parts) > 1:
                prefix = parts[0]
            else:
                prefix = 'other'

            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append(topic)

        lines = []
        for prefix, topics in sorted(grouped.items()):
            lines.append(f"- {prefix}: {', '.join(topics[:3])}{'...' if len(topics) > 3 else ''}")

        return '\n'.join(lines)

    def suggest_alternative_topic(
        self,
        excluded_topics: List[str],
        available_topics: List[str]
    ) -> Optional[str]:
        """
        Suggest an alternative topic that hasn't been used recently.

        TODO: This function is defined but not currently used in production code.
        Could be integrated with LLM generation to suggest topics when duplicates detected.

        Args:
            excluded_topics: Topics to avoid
            available_topics: All available topics

        Returns:
            A topic not in excluded list, or None if all exhausted
        """
        excluded_set = set(excluded_topics)

        for topic in available_topics:
            if topic not in excluded_set:
                return topic

        return None

    def get_content_diversity_score(
        self,
        recent_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate content diversity metrics.

        TODO: This function is defined but not currently used in production code.
        Could be used for analytics dashboard or adaptive content generation.

        Args:
            recent_content: List of recent content

        Returns:
            Dictionary with diversity metrics
        """
        if not recent_content:
            return {
                'total_content': 0,
                'unique_topics': 0,
                'topic_diversity': 1.0,
                'category_distribution': {}
            }

        topics = set()
        categories = {'oral': 0, 'written': 0}
        topic_themes = {}

        for content in recent_content:
            fingerprint = content.get('topic_fingerprint', '')
            if fingerprint:
                topics.add(fingerprint)
                # Extract theme
                theme = fingerprint.split('_')[0] if '_' in fingerprint else fingerprint
                topic_themes[theme] = topic_themes.get(theme, 0) + 1

            category = content.get('category', 'oral')
            categories[category] = categories.get(category, 0) + 1

        total = len(recent_content)
        unique = len(topics)

        return {
            'total_content': total,
            'unique_topics': unique,
            'topic_diversity': unique / total if total > 0 else 1.0,
            'category_distribution': categories,
            'theme_distribution': topic_themes
        }


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Deduplication for eng-lang-tutor")
    parser.add_argument('--demo', action='store_true', help='Run demo')

    args = parser.parse_args()

    dm = DeduplicationManager()

    if args.demo:
        # Simulate recent content
        recent = [
            {
                "topic_fingerprint": "asking_favor_casual",
                "category": "oral",
                "expressions": [{"phrase": "Can you do me a favor?"}]
            },
            {
                "topic_fingerprint": "workplace_meeting",
                "category": "oral",
                "expressions": [{"phrase": "Let's circle back"}]
            },
            {
                "topic_fingerprint": "gaming_slang",
                "category": "oral",
                "expressions": [{"phrase": "GG, that was clutch"}]
            }
        ]

        # Test duplicate detection
        new_content = {
            "topic_fingerprint": "asking_favor_formal",
            "category": "oral",
            "expressions": [{"phrase": "Could you help me out?"}]
        }

        is_dup, reason = dm.check_duplicate(new_content, recent)
        print(f"Is duplicate: {is_dup}")
        print(f"Reason: {reason}")

        # Test diversity score
        print("\n=== Diversity Score ===")
        score = dm.get_content_diversity_score(recent)
        print(json.dumps(score, indent=2))

        # Test excluded list prompt
        print("\n=== Excluded Topics (for LLM prompt) ===")
        excluded = ['asking_favor_casual', 'workplace_meeting', 'gaming_slang',
                    'social_greeting', 'news_vocabulary']
        print(dm.generate_excluded_list_prompt(excluded))
