# eng-lang-tutor

**Authentic American English Tutor** - An OpenClaw Skill for learning authentic American English expressions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 📚 **Daily Knowledge Points** - Authentic American expressions with scene context, alternatives, and Chinglish traps
- 🔊 **Audio Keypoints** - Edge-TTS voice synthesis, free high-quality, adjustable speed
- 📝 **Quiz System** - 4 question types: multiple choice, fill blank, dialogue completion, Chinglish fix
- 🎮 **Duolingo-style Gamification** - XP, levels, streaks, badges, gems
- ⏰ **Customizable Schedule** - Set your preferred push times via cron
- 🌐 **Bilingual Support** - Commands work in both English and Chinese

## Quick Start

### Prerequisites

- OpenClaw Gateway installed on your server
- Python 3.8+
- ffmpeg (for audio synthesis)
- Discord Bot (or other IM channel)

### Installation

**Option 1: npm (Recommended)**

```bash
npm install -g @rookiestar/eng-lang-tutor
```

Installation runs automatically, skill will be installed to `~/.openclaw/skills/eng-lang-tutor/`.

**Option 2: From Source**

```bash
cd ~/.openclaw/skills/
git clone https://github.com/rookiestar/eng-lang-tutor.git
pip install -r eng-lang-tutor/requirements.txt
```

**Verify Installation:**

```bash
openclaw skills list
openclaw skills info eng-lang-tutor
```

**Restart Gateway:**

```bash
openclaw gateway restart
```

### Configure Channel

**Discord Configuration:**
```bash
openclaw config set discord.token YOUR_BOT_TOKEN
openclaw config set discord.guildId YOUR_SERVER_ID
```

### Complete Pairing

When you first message the bot, you'll receive a pairing code. Approve it:

```bash
openclaw pairing approve discord YOUR_PAIRING_CODE
```

### First Use

When you first interact with the bot, it will guide you through a 7-step onboarding:

1. Select your CEFR level (A1-C2)
2. Choose your topic interests
3. Select tutor style (humorous/rigorous/casual/professional)
4. Set oral vs written focus
5. Configure schedule (keypoint and quiz times)
6. **Voice Teaching Configuration** - Choose whether to enable audio keypoints
   - If enabled, select speech speed (0.5-1.7, default 0.9)
   - Edge-TTS is used by default (free, no configuration needed)
   - To use XunFei, set environment variables on your server first:
     ```bash
     export TTS_PROVIDER=xunfei
     export XUNFEI_APPID=your_appid
     export XUNFEI_API_KEY=your_api_key
     export XUNFEI_API_SECRET=your_api_secret
     ```
7. Confirm your settings and create cron jobs

## TTS Voice Configuration

This Skill uses **Edge-TTS** (Microsoft Edge TTS service) by default - completely free with no API key required.

### Supported TTS Providers

| Provider | Description | Configuration |
|----------|-------------|---------------|
| **edge-tts** (default) | Microsoft Edge TTS, free high-quality | No config needed |
| xunfei | XunFei TTS, stable in China | Requires env vars |

Switch Provider:
```bash
# Use Edge-TTS (default)
export TTS_PROVIDER=edge-tts

# Use XunFei (configure keys first)
export TTS_PROVIDER=xunfei
export XUNFEI_APPID=xxx
export XUNFEI_API_KEY=xxx
export XUNFEI_API_SECRET=xxx
```

### Available Voices

**Edge-TTS (en-US):**

| Role | Default Voice | Description |
|------|---------------|-------------|
| Narrator | JennyNeural | Female, friendly and conversational |
| Dialogue A | EricNeural | Male, professional and rational |
| Dialogue B | JennyNeural | Female, friendly and conversational |

**XunFei (American English):**

| Role | Default Voice | Description |
|------|---------------|-------------|
| Narrator | catherine | Female, natural and fluid |
| Dialogue A | henry | Male, calm and professional |
| Dialogue B | catherine | Female, natural and fluid |

### Speed Options

| Speed | Value | Use Case |
|-------|-------|----------|
| Very Slow | 0.5 | Beginner shadowing |
| Slow | 0.7 | Learning pronunciation |
| **Normal (Recommended)** | **0.9** | Daily learning |
| Fast | 1.3 | Listening challenge |
| Very Fast | 1.7 | Advanced training |

## Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `start` | `开始`, `初始化` | Start onboarding |
| `keypoint` | `知识点`, `today` | View today's knowledge point |
| `keypoint history` | `知识点 历史` | View historical keypoints |
| `quiz` | `测验`, `test` | Take daily quiz |
| `stats` | `进度`, `level` | View progress |
| `config` | `设置` | View settings |
| `errors` | `错题本` | View error notebook |
| `help` | `帮助` | Show commands |

## Schedule Configuration

### Crontab Setup

The skill's scheduled push relies on crontab. Cron jobs are automatically created during onboarding Step 6.

For manual configuration or modification:

```bash
# Edit crontab
crontab -e

# Add scheduled tasks (example: 06:45 keypoint, 22:45 quiz in Beijing time)
CRON_TZ=Asia/Shanghai

# Keypoint push
45 6 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's keypoint." --mode now

# Quiz push
45 22 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's quiz invitation." --mode now
```

### Modify Schedule

To change push times:

1. **Send command to Bot via IM** to update preferences:

```
set schedule keypoint 7:00    # Set keypoint push time to 7:00 AM
set schedule quiz 21:00       # Set quiz push time to 9:00 PM
```

2. **Update crontab accordingly** (modify the corresponding times):

```bash
crontab -e
# Change 45 6 to 0 7, and 45 22 to 0 21
```

**Note:** Quiz time must be later than keypoint time. Time format is 24-hour (HH:MM).

## Gamification

### XP & Levels

This system has two independent level systems:
- **Ability Level (CEFR)**: A1-C2, determines content difficulty (language proficiency)
- **Activity Level**: 1-20, measures engagement depth (usage progression)

| Level Range | XP Required | Stage |
|-------------|-------------|-------|
| 1-5 | 0-350 | Starter |
| 6-10 | 550-2000 | Traveler |
| 11-15 | 2600-6000 | Explorer |
| 16-20 | 7200-15000 | Pioneer |

### Badges

| Badge | Requirement | Gems |
|-------|-------------|------|
| First Steps | Complete first quiz | 10 |
| Week Warrior | 7-day streak | 25 |
| Month Master | 30-day streak | 100 |
| Perfect 10 | 10 perfect quizzes | 50 |
| Vocab Hunter | Learn 100 expressions | 75 |
| Error Slayer | Clear 30 errors | 30 |

## Project Structure

```
eng-lang-tutor/
├── SKILL.md                    # Skill documentation
├── scripts/
│   ├── state_manager.py        # State persistence & events
│   ├── scorer.py               # Answer evaluation & XP
│   ├── gamification.py         # Streak/level/badge logic
│   ├── dedup.py                # 14-day deduplication
│   ├── command_parser.py       # User command parsing
│   ├── cron_push.py            # Scheduled content push
│   ├── constants.py            # Shared constants (level thresholds)
│   ├── utils.py                # Utility functions (safe divide, deep merge)
│   ├── cli.py                  # CLI entry point
│   └── audio/                  # Audio module
│       ├── tts/                # TTS voice synthesis
│       │   ├── base.py         # TTS abstract base class
│       │   ├── manager.py      # TTS manager
│       │   └── providers/      # TTS providers
│       │       ├── edge.py     # Edge-TTS (default)
│       │       └── xunfei.py   # XunFei TTS
│       ├── composer.py         # Audio composition
│       ├── converter.py        # Format conversion
│       └── feishu_voice.py     # Feishu voice sender
├── templates/
│   ├── state_schema.json       # State JSON Schema
│   ├── keypoint_schema.json    # Keypoint JSON Schema
│   ├── quiz_schema.json        # Quiz JSON Schema
│   ├── prompt_templates.md     # LLM prompt templates index
│   └── prompts/                # Split prompt templates
│       ├── keypoint_generation.md
│       ├── quiz_generation.md
│       ├── display_guide.md
│       ├── initialization.md
│       └── responses.md
├── references/
│   └── resources.md            # Themed learning resources
├── examples/
│   ├── sample_keypoint.json    # Sample keypoint
│   └── sample_quiz.json        # Sample quiz
└── docs/
    └── OPENCLAW_DEPLOYMENT.md  # Deployment docs
```

**Data Location:** `~/.openclaw/state/eng-lang-tutor/`

Customize via `OPENCLAW_STATE_DIR` environment variable.

## Documentation

- [SKILL.md](SKILL.md) - Full skill documentation
- [OpenClaw Deployment Guide](docs/OPENCLAW_DEPLOYMENT.md) - Server deployment

## Development

### Local Debugging

```bash
python3 scripts/command_parser.py --demo
python3 scripts/cron_push.py --task status
```

## Migration

**Migrate Learning Data:**

```bash
# On source server, backup data
tar -czvf eng-lang-tutor-data.tar.gz -C ~/.openclaw/state eng-lang-tutor

# Transfer to new server
scp eng-lang-tutor-data.tar.gz user@new-server:~/

# On target server, extract
mkdir -p ~/.openclaw/state
tar -xzvf ~/eng-lang-tutor-data.tar.gz -C ~/.openclaw/state
```

**Reinstall Skill:**

```bash
npm install -g @rookiestar/eng-lang-tutor
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [awesome-language-learning](https://github.com/Vuizur/awesome-language-learning) - Resource inspiration
- [Duolingo](https://www.duolingo.com) - Gamification model reference
