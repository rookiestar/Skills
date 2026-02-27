# Changelog

All notable changes to this project will be documented in this file.

## [1.2.7] - 2026-02-28

### Fixed
- **CLI config display**: Fixed `topic_weights` field name mismatch
  - Changed from `topic_weights` to `topics` to match actual state storage
- **state_manager.py imports**: Fixed fallback import paths for audio modules
  - Changed `from audio.composer` to `from scripts.audio.composer`
- **audio/utils.py timeout**: Added 30-second timeout to `get_audio_duration()`
  - Prevents infinite hang if ffmpeg stalls
- **CronPusher data_dir**: Fixed default value to use StateManager's default
  - Changed `data_dir: str = "data"` to `data_dir: str = None`
- **CLI generate_audio**: Added keypoint existence check before audio generation
  - Provides clearer error message when keypoint doesn't exist

## [1.2.6] - 2026-02-28

### Fixed
- **TTSManager missing method**: Added `get_voice_by_role()` method to TTSManager class
  - Fixes `'TTSManager' object has no attribute 'get_voice_by_role'` error during audio synthesis
- **CLI oral_ratio parameter**: Fixed parameter name mismatch in config command
  - Changed `oral_ratio` to `oral_written_ratio` with proper percentage-to-decimal conversion
  - Fixed both read (line 115) and write (line 140) operations

## [1.2.5] - 2026-02-27

### Added
- **Release management**: Three-layer file distribution system
  - `.gitattributes` for git archive export filtering
  - `package.json` files field in whitelist mode
  - `scripts/release.py` for distribution analysis
- **Uninstall guide**: Added comprehensive uninstall instructions to README

### Changed
- **npm package**: Optimized file inclusion with whitelist approach
  - Includes: scripts/, templates/, examples/, references/, SKILL.md, README.md, requirements.txt
  - Excludes: tests/, docs/, CLAUDE.md, bin/, setup.py
- **.gitignore**: Added Python egg-info, test cache, npm cache, and Claude Code entries

## [1.2.4] - 2026-02-27

### Fixed
- **TTS voice selection**: Audio composer now automatically selects appropriate voices based on TTS provider
  - Edge-TTS: `en-US-JennyNeural`, `en-US-EricNeural`
  - XunFei: `catherine`, `henry`
- **CLI import paths**: Fixed broken imports in `state_manager.py` CLI module

### Changed
- **npm package**: Removed automatic `pip install` from postinstall script
  - Added `eng-lang-tutor-setup` CLI tool for manual dependency installation
  - Supports `--venv`, `--user`, and `--check` options
- **Test coverage**: Added 38 new tests covering:
  - `scripts/audio/utils.py` (6 tests)
  - `scripts/audio/converter.py` (16 tests)
  - `scripts/utils/helpers.py` (16 tests)
- **Test fixes**: Fixed pre-existing test failures in CLI and TTS modules

## [1.2.3] - 2026-02-27

### Changed
- Version bump for npm publishing

## [1.2.0] - 2026-02-27

### Changed
- Initial npm package setup

## [1.0.1] - 2025-02-27

### Fixed
- **TTS voice selection**: Audio composer now automatically selects appropriate voices based on TTS provider
  - Edge-TTS: `en-US-JennyNeural`, `en-US-EricNeural`
  - XunFei: `catherine`, `henry`
- **CLI import paths**: Fixed broken imports in `state_manager.py` CLI module

### Changed
- **npm package**: Removed automatic `pip install` from postinstall script
  - Added `eng-lang-tutor-setup` CLI tool for manual dependency installation
  - Supports `--venv`, `--user`, and `--check` options
- **Test coverage**: Added 38 new tests covering:
  - `scripts/audio/utils.py` (6 tests)
  - `scripts/audio/converter.py` (16 tests)
  - `scripts/utils/helpers.py` (16 tests)
- **Test fixes**: Fixed pre-existing test failures in CLI and TTS modules

## [1.0.1] - 2025-02-27

### Changed
- Version bump for npm publishing (1.0.0 was previously unpublished)

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
