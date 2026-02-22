#!/usr/bin/env python3
"""
Utility functions for eng-lang-tutor.

Common utilities used across multiple modules.
"""

from typing import Dict, Any


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division that returns default if denominator is zero.

    Args:
        numerator: The number to divide
        denominator: The number to divide by
        default: Value to return if denominator is zero

    Returns:
        Result of division, or default if denominator is zero

    Examples:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
        >>> safe_divide(10, 0, default=100)
        100.0
    """
    return numerator / denominator if denominator != 0 else default


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge override dictionary into base dictionary.

    Creates a new dictionary with values from base, updated with values from override.
    Nested dictionaries are merged recursively; other values are overwritten.

    Args:
        base: Base dictionary (not modified)
        override: Dictionary with values to override/add

    Returns:
        New merged dictionary

    Examples:
        >>> base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        >>> override = {'b': {'c': 10}}
        >>> deep_merge(base, override)
        {'a': 1, 'b': {'c': 10, 'd': 3}}
    """
    import copy
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value to a range.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Value clamped to [min_val, max_val]
    """
    return max(min_val, min(max_val, value))
