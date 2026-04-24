#!/usr/bin/env python3
"""
CLI interface for eng-lang-tutor state management.

This module provides command-line access to state management operations.
"""

import argparse
import json
from datetime import datetime
from typing import Optional

try:
    from ..core.state_manager import StateManager
except ImportError:
    from scripts.core.state_manager import StateManager


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="State Manager for eng-lang-tutor")
    parser.add_argument('--data-dir', default=None,
                        help='Data directory path (default: ~/.openclaw/state/eng-lang-tutor or OPENCLAW_STATE_DIR env)')
    parser.add_argument('command', nargs='?',
                        choices=['show', 'backup', 'save_daily', 'record_view',
                                 'stats', 'config', 'errors', 'schedule',
                                 'generate_audio'],
                        help='Command to execute')
    parser.add_argument('--content-type', help='Content type for save_daily (keypoint, quiz)')
    parser.add_argument('--content', help='JSON content for save_daily')
    parser.add_argument('--date', help='Date for content (YYYY-MM-DD format)')
    # Errors command options
    parser.add_argument('--page', type=int, default=1, help='Page number for errors list')
    parser.add_argument('--per-page', type=int, default=5, help='Items per page for errors')
    parser.add_argument('--month', help='Filter errors by month (YYYY-MM)')
    parser.add_argument('--random', type=int, help='Get N random errors')
    parser.add_argument('--stats', action='store_true', help='Get error statistics')
    parser.add_argument('--review', type=int, help='Get N errors for review session')
    # Config command options
    parser.add_argument('--cefr', help='Set CEFR level (A1-C2)')
    parser.add_argument('--style', help='Set tutor style')
    parser.add_argument('--oral-ratio', type=int, help='Set oral/written ratio (0-100)')
    # Schedule command options
    parser.add_argument('--keypoint-time', help='Set keypoint push time (HH:MM)')
    parser.add_argument('--quiz-time', help='Set quiz push time (HH:MM)')

    args = parser.parse_args()

    sm = StateManager(args.data_dir)

    if args.command == 'show' or not args.command:
        state = sm.load_state()
        print(json.dumps(state, indent=2, ensure_ascii=False))

    elif args.command == 'backup':
        backup_path = sm.backup_state()
        print(f"Backup created: {backup_path}")

    elif args.command == 'save_daily':
        if not args.content_type or not args.content:
            print("Error: --content-type and --content are required for save_daily")
            exit(1)

        try:
            content = json.loads(args.content)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON content: {e}")
            exit(1)

        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                exit(1)

        path = sm.save_daily_content(args.content_type, content, target_date)
        print(f"Saved to: {path}")

    elif args.command == 'record_view':
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                exit(1)

        state = sm.load_state()
        sm.record_keypoint_view(state, target_date)
        sm.save_state(state)
        print("View recorded successfully")

    elif args.command == 'stats':
        """Display learning progress summary."""
        try:
            from ..core.gamification import GamificationManager
        except ImportError:
            from scripts.core.gamification import GamificationManager
        state = sm.load_state()
        gm = GamificationManager()
        summary = gm.get_progress_summary(state)
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    elif args.command == 'config':
        """Display or update user configuration."""
        state = sm.load_state()

        # If no update options, just show current config
        if not any([args.cefr, args.style, args.oral_ratio is not None]):
            config = {
                "cefr_level": state.get("preferences", {}).get("cefr_level", "B1"),
                "tutor_style": state.get("preferences", {}).get("tutor_style", "humorous"),
                "oral_ratio": int(state.get("preferences", {}).get("oral_written_ratio", 0.7) * 100),
                "topics": state.get("preferences", {}).get("topics", {}),
                "schedule": state.get("schedule", {})
            }
            print(json.dumps(config, indent=2, ensure_ascii=False))
        else:
            # Update configuration
            if args.cefr:
                if args.cefr not in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
                    print("Error: Invalid CEFR level. Must be A1, A2, B1, B2, C1, or C2")
                    exit(1)
                state = sm.update_preferences(state, cefr_level=args.cefr)
                print(f"Updated CEFR level to: {args.cefr}")

            if args.style:
                if args.style not in ['humorous', 'rigorous', 'casual', 'professional']:
                    print("Error: Invalid style. Must be humorous, rigorous, casual, or professional")
                    exit(1)
                state = sm.update_preferences(state, tutor_style=args.style)
                print(f"Updated tutor style to: {args.style}")

            if args.oral_ratio is not None:
                if not 0 <= args.oral_ratio <= 100:
                    print("Error: Oral ratio must be between 0 and 100")
                    exit(1)
                state = sm.update_preferences(state, oral_written_ratio=args.oral_ratio/100)
                print(f"Updated oral ratio to: {args.oral_ratio}%")

            sm.save_state(state)
            print("Configuration updated successfully")

    elif args.command == 'errors':
        """Error notebook operations."""
        state = sm.load_state()

        if args.stats:
            # Get error statistics
            stats = sm.get_error_stats(state)
            print(json.dumps(stats, indent=2, ensure_ascii=False))

        elif args.review is not None:
            # Get errors for review session
            errors = sm.get_review_errors(state, count=args.review)
            result = {
                "count": len(errors),
                "errors": errors
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            # Get paginated errors list
            result = sm.get_errors_page(
                state,
                page=args.page,
                per_page=args.per_page,
                month=args.month,
                random=args.random
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == 'schedule':
        """Display or update schedule configuration."""
        state = sm.load_state()

        # If no update options, just show current schedule
        if not any([args.keypoint_time, args.quiz_time]):
            schedule = state.get("schedule", {})
            print(json.dumps(schedule, indent=2, ensure_ascii=False))
        else:
            # Validate quiz_time must be later than keypoint_time
            current_keypoint = state.get("schedule", {}).get("keypoint_time", "06:45")
            current_quiz = state.get("schedule", {}).get("quiz_time", "22:45")

            new_keypoint = args.keypoint_time or current_keypoint
            new_quiz = args.quiz_time or current_quiz

            # Time validation
            def parse_time(t):
                h, m = map(int, t.split(':'))
                return h * 60 + m

            if parse_time(new_quiz) <= parse_time(new_keypoint):
                print("Error: Quiz time must be later than keypoint time")
                exit(1)

            state = sm.update_schedule(
                state,
                keypoint_time=new_keypoint,
                quiz_time=new_quiz
            )
            sm.save_state(state)
            print(f"Schedule updated: keypoint at {new_keypoint}, quiz at {new_quiz}")

    elif args.command == 'generate_audio':
        """Generate audio for a keypoint."""
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                print("Error: Invalid date format. Use YYYY-MM-DD")
                exit(1)

        # Check if keypoint exists first
        keypoint = sm.load_daily_content('keypoint', target_date)
        if not keypoint:
            date_str = target_date.isoformat() if target_date else datetime.now().strftime('%Y-%m-%d')
            print(f"Error: No keypoint found for {date_str}")
            exit(1)

        result = sm.generate_keypoint_audio(target_date)

        if result.get('success'):
            print(f"Audio generated: {result.get('audio_path')}")
            print(f"Duration: {result.get('duration_seconds', 0):.1f} seconds")
        else:
            print(f"Failed to generate audio: {result.get('error_message')}")
            exit(1)


if __name__ == "__main__":
    main()
