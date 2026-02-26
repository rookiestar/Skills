# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-02-26

Initial release.

### Added

**Core Features:**
- Daily knowledge points with authentic American English expressions
- Quiz system with 4 question types (multiple choice, Chinglish fix, fill blank, dialogue completion)
- Duolingo-style gamification (XP, levels 1-20, streaks, badges, gems)
- Error notebook for tracking and reviewing mistakes
- 14-day content deduplication

**CEFR Support:**
- Complete CEFR level definitions (A1-C2) with Can-Do Statements
- 12 sample JSON files covering all 6 CEFR levels
- Content difficulty adjusted by user's CEFR level

**Audio:**
- TTS audio generation (Edge-TTS default, XunFei optional)
- Async audio generation with background threading
- Context manager pattern for reliable temp file cleanup

**Configuration:**
- 7-step onboarding flow
- Initialization guard check before content generation
- Centralized configuration constants
- Prompt version control via `_meta.prompt_version` field

**Documentation:**
- SKILL.md, README.md, CLAUDE.md
- OpenClaw deployment guide
- Prompt templates (keypoint generation, quiz generation, etc.)
