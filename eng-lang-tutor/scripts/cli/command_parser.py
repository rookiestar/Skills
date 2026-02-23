#!/usr/bin/env python3
"""
Command Parser - Parses user messages and routes to appropriate handlers.

Handles:
- Command recognition via regex patterns
- Parameter extraction from messages
- Initialization flow detection
- Bilingual support (English/Chinese)
"""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta


class CommandParser:
    """Parses user messages to determine intent and extract parameters."""

    # Command patterns with bilingual support
    COMMAND_PATTERNS = {
        # Initialization commands
        "init_start": r"(?i)^(start|begin|开始|初始化|你好|hello|hi|嗨|hey).*$",

        # Keypoint commands
        "keypoint_today": r"(?i)(keypoint|知识点|今天|today).*(?!.*(历史|history|昨天|yesterday|前天|上周))",
        "keypoint_history": r"(?i)(keypoint|知识点).*(历史|history|昨天|yesterday|前天|previous|上周)",
        "keypoint_date": r"(?i)(keypoint|知识点).*?(\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}[日号]?)",

        # Quiz commands
        "quiz_take": r"(?i)(quiz|测验|test|测试|答题|考试)",

        # Stats commands
        "stats_view": r"(?i)(stats|progress|进度|统计|等级|level|xp|连胜|streak|成就|achievement)",

        # Config commands
        "config_view": r"(?i)(config|settings?|设置|配置|偏好|preference)(?!.*(change|改|set|设|更新))",
        "config_change_cefr": r"(?i)(cefr|等级|level).*(A1|A2|B1|B2|C1|C2)",
        "config_change_style": r"(?i)(style|风格|导师).*(humorous|rigorous|casual|professional|幽默|严谨|随意|专业)",
        "config_change_topics": r"(?i)(topic|主题|配比|权重|兴趣)",
        "config_change_ratio": r"(?i)(ratio|比例).*(口语|oral|书面|written|speaking|writing)",

        # Schedule commands
        "schedule_view": r"(?i)(schedule|时间表|推送时间|定时)(?!.*(change|改|set|设))",
        "schedule_change": r"(?i)(schedule|时间表|推送时间).*(change|改|set|设|调整)",

        # Error notebook commands
        "errors_view": r"(?i)(errors?|错题本|mistakes?|wrong|错误|错题)(?!.*(更多|more|随机|random|清空|clear|删除|remove|\d{4}-\d{2}))",
        "errors_more": r"(?i)(errors?|错题本).*(更多|more|下一页|next)",
        "errors_page": r"(?i)(errors?|错题本).*(第\s*\d+\s*页|page\s*\d+)",
        "errors_month": r"(?i)(errors?|错题本).*(\d{4}-\d{2})(?!.*\d{2})",  # YYYY-MM format
        "errors_random": r"(?i)(errors?|错题本).*(随机|random)",
        "errors_clear": r"(?i)(errors?|错题本).*(clear|清空|删除|remove)",
        "errors_stats": r"(?i)(errors?|错题本).*(统计|stats|statistics)",
        "errors_review": r"(?i)(errors?|错题本).*(复习|review|练习|practice)(?!.*(更多|more|随机|random|清空|clear|删除|remove|统计|stats))",

        # Help command
        "help": r"(?i)(help|帮助|usage|怎么用|how to use|command|命令|指令|功能)",
    }

    # Onboarding step patterns for collecting user input
    ONBOARDING_PATTERNS = {
        "cefr_level": r"(?i)(A1|A2|B1|B2|C1|C2)",
        "tutor_style": r"(?i)(humorous|rigorous|casual|professional|幽默|严谨|随意|专业)",
        "topics": r"(?i)(movies?|新闻?|news|游戏?|gaming|体育?|sports?|职场?|workplace|社交?|social|生活?|daily)",
        "ratio": r"(\d{1,3})\s*(%|percent|百分比)?",
    }

    def __init__(self, state_manager=None):
        """
        Initialize the command parser.

        Args:
            state_manager: Optional StateManager instance for context
        """
        self.state_manager = state_manager

    def parse(self, message: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user message and return command info.

        Args:
            message: User's message text
            state: Current state dictionary

        Returns:
            Dictionary with:
            - command: Command name
            - params: Extracted parameters
            - requires_init: Whether command requires initialization
            - onboarding_input: If in onboarding, the detected input type
        """
        # Check if user is in onboarding flow
        if not state.get("initialized", False):
            return self._handle_uninitialized(message, state)

        # Parse for initialized users
        return self._parse_command(message)

    def _handle_uninitialized(self, message: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messages from uninitialized users."""
        step = state.get("onboarding_step", 0)

        if step == 0:
            # Check for start command
            if re.search(self.COMMAND_PATTERNS["init_start"], message):
                return {
                    "command": "init_start",
                    "params": {},
                    "requires_init": False,
                    "onboarding_input": None
                }
            else:
                # Any other message triggers welcome
                return {
                    "command": "init_welcome",
                    "params": {},
                    "requires_init": False,
                    "onboarding_input": None
                }

        # User is in onboarding, detect what they're providing
        onboarding_input = self._detect_onboarding_input(message, step)

        return {
            "command": "init_continue",
            "params": {"step": step},
            "requires_init": False,
            "onboarding_input": onboarding_input
        }

    def _detect_onboarding_input(self, message: str, step: int) -> Optional[Dict[str, Any]]:
        """Detect user input during onboarding based on current step."""
        result = {"type": None, "value": None}

        if step == 1:  # CEFR level
            match = re.search(self.ONBOARDING_PATTERNS["cefr_level"], message)
            if match:
                result = {"type": "cefr_level", "value": match.group(1).upper()}

        elif step == 2:  # Topics
            topics = {}
            topic_keywords = {
                "movies": ["movie", "film", "影视", "电影", "美剧"],
                "news": ["news", "新闻"],
                "gaming": ["game", "gaming", "游戏"],
                "sports": ["sport", "sports", "体育", "运动"],
                "workplace": ["work", "workplace", "office", "职场", "工作"],
                "social": ["social", "社交"],
                "daily_life": ["daily", "life", "生活", "日常"]
            }

            for topic, keywords in topic_keywords.items():
                for kw in keywords:
                    if kw.lower() in message.lower():
                        topics[topic] = 0.2  # Default weight
                        break

            if topics:
                # Normalize weights to sum to 1.0
                total = sum(topics.values())
                topics = {k: round(v / total, 2) for k, v in topics.items()}
                result = {"type": "topics", "value": topics}

        elif step == 3:  # Tutor style
            style_map = {
                "humorous": ["humorous", "幽默"],
                "rigorous": ["rigorous", "严谨"],
                "casual": ["casual", "随意", "轻松"],
                "professional": ["professional", "专业"]
            }
            for style, keywords in style_map.items():
                for kw in keywords:
                    if kw.lower() in message.lower():
                        result = {"type": "tutor_style", "value": style}
                        break
                if result["value"]:
                    break

        elif step == 4:  # Oral/written ratio
            match = re.search(self.ONBOARDING_PATTERNS["ratio"], message)
            if match:
                ratio = int(match.group(1)) / 100.0
                ratio = max(0, min(1, ratio))  # Clamp to 0-1
                result = {"type": "oral_written_ratio", "value": ratio}

        return result if result["type"] else None

    def _parse_command(self, message: str) -> Dict[str, Any]:
        """Parse message for an initialized user."""
        result = {
            "command": "unknown",
            "params": {},
            "requires_init": False,
            "onboarding_input": None
        }

        # Check each command pattern
        for cmd_name, pattern in self.COMMAND_PATTERNS.items():
            match = re.search(pattern, message)
            if match:
                result["command"] = cmd_name
                result["params"] = self._extract_params(cmd_name, match, message)
                result["requires_init"] = not cmd_name.startswith("init") and cmd_name != "help"
                break

        return result

    def _extract_params(self, cmd_name: str, match: re.Match, message: str) -> Dict[str, Any]:
        """Extract parameters from matched command."""
        params = {}

        # Extract date from keypoint queries
        if "date" in cmd_name or cmd_name in ["keypoint_today", "keypoint_history"]:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", message)
            if date_match:
                params["date"] = date_match.group(1)
            elif "history" in cmd_name or "昨天" in message or "yesterday" in message.lower():
                params["date"] = (date.today() - timedelta(days=1)).isoformat()
            elif "前天" in message:
                params["date"] = (date.today() - timedelta(days=2)).isoformat()
            else:
                params["date"] = date.today().isoformat()

        # Extract CEFR level
        if "cefr" in cmd_name:
            level_match = re.search(r"(A1|A2|B1|B2|C1|C2)", message, re.I)
            if level_match:
                params["cefr_level"] = level_match.group(1).upper()

        # Extract style
        if "style" in cmd_name:
            style_map = {
                "humorous": "humorous", "幽默": "humorous",
                "rigorous": "rigorous", "严谨": "rigorous",
                "casual": "casual", "随意": "casual", "轻松": "casual",
                "professional": "professional", "专业": "professional"
            }
            for keyword, style in style_map.items():
                if keyword in message.lower():
                    params["tutor_style"] = style
                    break

        # Extract ratio
        if "ratio" in cmd_name:
            ratio_match = re.search(r"(\d{1,3})\s*(%|percent|百分比)?", message)
            if ratio_match:
                params["oral_written_ratio"] = int(ratio_match.group(1)) / 100.0

        # Extract error notebook pagination params
        if cmd_name and cmd_name.startswith("errors"):
            # Page number
            page_match = re.search(r"(第\s*)?(\d+)(\s*页|page)", message, re.I)
            if page_match:
                params["page"] = int(page_match.group(2))

            # Month filter (YYYY-MM)
            month_match = re.search(r"(\d{4}-\d{2})(?!-\d{2})", message)
            if month_match:
                params["month"] = month_match.group(1)

            # Random count
            random_match = re.search(r"(随机|random)\s*(\d*)", message, re.I)
            if random_match:
                count = int(random_match.group(2)) if random_match.group(2) else 5
                params["random"] = count

            # Default page for "more" command
            if "more" in cmd_name:
                params["page"] = params.get("page", 2)

            # Review count (for errors_review command)
            if "review" in cmd_name:
                count_match = re.search(r"(复习|review|练习|practice)\s*(\d*)", message, re.I)
                if count_match and count_match.group(2):
                    params["count"] = int(count_match.group(2))
                else:
                    params["count"] = 5  # Default 5 questions per session

        return params

    def get_command_suggestions(self, context: str = "general") -> list:
        """
        Get suggested commands based on context.

        Args:
            context: Context for suggestions (general, after_quiz, morning, etc.)

        Returns:
            List of suggested command strings
        """
        suggestions = {
            "general": ["keypoint", "quiz", "stats", "help"],
            "after_quiz": ["stats", "errors", "keypoint"],
            "morning": ["keypoint", "quiz"],
            "evening": ["quiz", "stats"]
        }
        return suggestions.get(context, suggestions["general"])


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Command Parser for eng-lang-tutor")
    parser.add_argument('--message', type=str, help='Message to parse')
    parser.add_argument('--demo', action='store_true', help='Run demo')

    args = parser.parse_args()

    cp = CommandParser()

    if args.demo:
        test_messages = [
            "start",
            "今天知识点",
            "keypoint today",
            "quiz",
            "我的进度",
            "stats",
            "config",
            "设置 CEFR 为 B2",
            "help",
            "错题本"
        ]

        print("=== Command Parser Demo ===\n")
        for msg in test_messages:
            result = cp._parse_command(msg)
            print(f"Message: {msg}")
            print(f"Result:  {json.dumps(result, indent=2)}\n")

    elif args.message:
        result = cp._parse_command(args.message)
        print(json.dumps(result, indent=2, ensure_ascii=False))
