# Changelog

All notable changes to this project will be documented in this file.

## [1.0.15] - 2025-02-23

### Added
- Backward compatible audio sending with `FEISHU_VOICE_BUBBLE_ENABLED` environment variable
  - Standard mode: sends audio file attachment only
  - Enhanced mode: sends voice bubble + file attachment (requires OpenClaw plugin support)

### Changed
- Audio files now generate directly to `~/.openclaw/media/eng-lang-tutor/{date}/` directory
- Removed intermediate audio file copy step

### Fixed
- Audio field no longer displays as plain text in IM output
- `[AUDIO:...]` tags prohibited in keypoint generation template

## [1.0.14] - 2025-02-23

### Added
- Audio Composer integration for automatic TTS audio generation
- XunFei TTS support with environment variable configuration

### Changed
- Keypoint JSON schema extended with `audio` metadata field

## [1.0.13] - 2025-02-23

### Changed
- Audio message format upgraded to use voice player UI

## [1.0.12] - 2025-02-23

### Fixed
- Audio handling workflow improvements
- Explicit audio sending instructions in SKILL.md

## [1.0.11] - 2025-02-23

### Fixed
- Audio display bugfix - prevented plain text audio tags in output

## [1.0.10] - 2025-02-22

### Added
- Initial audio support for keypoint content
