#!/usr/bin/env python3
"""
Helper utilities 单元测试

测试内容：
- safe_divide() 函数
- deep_merge() 函数
"""

import pytest


class TestSafeDivide:
    """测试 safe_divide 函数"""

    def test_normal_division(self):
        """测试正常除法"""
        from scripts.utils.helpers import safe_divide

        assert safe_divide(10, 2) == 5.0
        assert safe_divide(100, 10) == 10.0
        assert safe_divide(7, 2) == 3.5

    def test_division_by_zero_returns_default(self):
        """测试除以零返回默认值"""
        from scripts.utils.helpers import safe_divide

        assert safe_divide(10, 0) == 0.0
        assert safe_divide(100, 0) == 0.0

    def test_custom_default_value(self):
        """测试自定义默认值"""
        from scripts.utils.helpers import safe_divide

        assert safe_divide(10, 0, default=100) == 100.0
        assert safe_divide(10, 0, default=-1) == -1.0
        assert safe_divide(10, 0, default=float('inf')) == float('inf')

    def test_negative_numbers(self):
        """测试负数"""
        from scripts.utils.helpers import safe_divide

        assert safe_divide(-10, 2) == -5.0
        assert safe_divide(10, -2) == -5.0
        assert safe_divide(-10, -2) == 5.0

    def test_float_numbers(self):
        """测试浮点数"""
        from scripts.utils.helpers import safe_divide

        assert safe_divide(10.5, 2) == 5.25
        assert safe_divide(10, 2.5) == 4.0
        assert safe_divide(10.5, 2.5) == 4.2


class TestDeepMerge:
    """测试 deep_merge 函数"""

    def test_simple_merge(self):
        """测试简单合并"""
        from scripts.utils.helpers import deep_merge

        base = {"a": 1, "b": 2}
        override = {"c": 3}

        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_override_replaces_value(self):
        """测试 override 替换 base 的值"""
        from scripts.utils.helpers import deep_merge

        base = {"a": 1, "b": 2}
        override = {"b": 3}

        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3}

    def test_nested_merge(self):
        """测试嵌套字典合并"""
        from scripts.utils.helpers import deep_merge

        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}

        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_deeply_nested_merge(self):
        """测试深层嵌套合并"""
        from scripts.utils.helpers import deep_merge

        base = {"a": {"b": {"c": 1}}}
        override = {"a": {"b": {"d": 2}}}

        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 2}}}

    def test_override_adds_new_nested_key(self):
        """测试 override 添加新的嵌套键"""
        from scripts.utils.helpers import deep_merge

        base = {"a": {"x": 1}}
        override = {"b": {"y": 2}}

        result = deep_merge(base, override)
        assert result == {"a": {"x": 1}, "b": {"y": 2}}

    def test_empty_override(self):
        """测试空 override"""
        from scripts.utils.helpers import deep_merge

        base = {"a": 1, "b": 2}
        override = {}

        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_empty_base(self):
        """测试空 base"""
        from scripts.utils.helpers import deep_merge

        base = {}
        override = {"a": 1, "b": 2}

        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_non_dict_override_replaces(self):
        """测试非字典 override 直接替换"""
        from scripts.utils.helpers import deep_merge

        base = {"a": {"x": 1}}
        override = {"a": "string"}

        result = deep_merge(base, override)
        assert result == {"a": "string"}

    def test_does_not_modify_original(self):
        """测试不修改原始字典"""
        from scripts.utils.helpers import deep_merge

        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}

        base_copy = {"a": {"x": 1}}
        override_copy = {"a": {"y": 2}}

        result = deep_merge(base, override)

        # 原始字典应该没有被修改
        assert base == base_copy
        assert override == override_copy

    def test_complex_real_world_merge(self):
        """测试复杂的真实场景合并"""
        from scripts.utils.helpers import deep_merge

        base = {
            "user": {
                "name": "John",
                "preferences": {
                    "theme": "dark",
                    "language": "en"
                }
            },
            "settings": {
                "notifications": True
            }
        }

        override = {
            "user": {
                "preferences": {
                    "language": "zh",
                    "timezone": "Asia/Shanghai"
                }
            },
            "settings": {
                "sound": False
            }
        }

        result = deep_merge(base, override)

        expected = {
            "user": {
                "name": "John",
                "preferences": {
                    "theme": "dark",
                    "language": "zh",
                    "timezone": "Asia/Shanghai"
                }
            },
            "settings": {
                "notifications": True,
                "sound": False
            }
        }

        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
