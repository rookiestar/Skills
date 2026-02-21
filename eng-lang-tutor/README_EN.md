# eng-lang-tutor

**地道美式英语导师** - An OpenClaw Skill for learning authentic American English expressions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 📚 **Daily Knowledge Points** - Authentic American expressions with scene context, alternatives, and Chinglish traps
- 📝 **Quiz System** - 4 question types: multiple choice, fill blank, dialogue completion, Chinglish fix
- 🎮 **Duolingo-style Gamification** - XP, levels, streaks, badges, gems
- ⏰ **Customizable Schedule** - Set your preferred push times via cron
- 🌐 **Bilingual Support** - Commands work in both English and Chinese

## Quick Start

### Prerequisites

- OpenClaw Gateway installed on your server
- Python 3.8+
- Discord Bot (or other IM channel)

### Installation

1. **Clone to your OpenClaw skills directory:**

```bash
cd ~/.openclaw/skills/
git clone https://github.com/rookiestar/eng-lang-tutor.git
```

2. **Verify installation:**

```bash
openclaw skills list
openclaw skills info eng-lang-tutor
```

3. **Configure Channel:**

**Discord Configuration:**
```bash
openclaw config set discord.token YOUR_BOT_TOKEN
openclaw config set discord.guildId YOUR_SERVER_ID
```

4. **Complete pairing:**

When you first message the bot, you'll receive a pairing code. Approve it:

```bash
openclaw pairing approve discord YOUR_PAIRING_CODE
```

### First Use

When you first interact with the bot, it will guide you through a 6-step onboarding:

1. Select your CEFR level (A1-C2)
2. Choose your topic interests
3. Select tutor style (humorous/rigorous/casual/professional)
4. Set oral vs written focus
5. Configure schedule (keypoint and quiz times)
6. Confirm your settings and create cron jobs

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

### Default Schedule (UTC+8)

| Task | Time |
|------|------|
| Knowledge Point | 6:45 AM |
| Daily Quiz | 10:45 PM |

### Customize Schedule

```
set schedule keypoint 7:00
set schedule quiz 21:00
```

### Crontab Setup

```bash
# Edit crontab
crontab -e

# Add scheduled tasks
CRON_TZ=Asia/Shanghai

# 06:45 Daily keypoint
45 6 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's keypoint." --mode now

# 22:45 Daily quiz
45 22 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's quiz invitation." --mode now
```

## Gamification

### XP & Levels

This system has two independent level systems:
- **Ability Level (CEFR)**: A1-C2, determines content difficulty (language proficiency)
- **Activity Level**: 1-20, measures engagement depth (usage progression)

| Level Range | XP Required | Stage |
|-------------|-------------|-------|
| 1-5 | 0-350 | Starter (启程者) |
| 6-10 | 550-2000 | Traveler (行路人) |
| 11-15 | 2600-6000 | Explorer (探索者) |
| 16-20 | 7200-15000 | Pioneer (开拓者) |

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
│   └── cron_push.py            # Scheduled content push
├── templates/
│   ├── state_schema.json       # State JSON Schema
│   ├── keypoint_schema.json    # Keypoint JSON Schema
│   ├── quiz_schema.json        # Quiz JSON Schema
│   └── prompt_templates.md     # LLM prompt templates
├── references/
│   └── resources.md            # Themed learning resources
├── examples/
│   ├── sample_keypoint.json
│   └── sample_quiz.json
├── tests/
│   ├── conftest.py
│   ├── test_state_manager.py
│   ├── test_scorer.py
│   ├── test_gamification.py
│   ├── test_dedup.py
│   ├── test_command_parser.py
│   └── test_cron_push.py
└── data/
    ├── state.json              # Runtime state
    ├── logs/                   # Event logs
    └── daily/                  # Daily content
```

## Documentation

- [SKILL.md](SKILL.md) - Full skill documentation
- [OpenClaw Deployment Guide](docs/OPENCLAW_DEPLOYMENT.md) - Server deployment

## Development

### Run Tests

```bash
cd eng-lang-tutor
pytest tests/ -v
```

### Run Demo

```bash
python3 scripts/command_parser.py --demo
python3 scripts/cron_push.py --task status
```

## Migration

To migrate to a new server:

```bash
# On source server
cd ~/.openclaw/skills/
tar -czvf eng-lang-tutor-backup.tar.gz eng-lang-tutor/

# Transfer to new server
scp eng-lang-tutor-backup.tar.gz user@new-server:~/

# On target server
cd ~/.openclaw/skills/
tar -xzvf ~/eng-lang-tutor-backup.tar.gz
```

See [docs/OPENCLAW_DEPLOYMENT.md](docs/OPENCLAW_DEPLOYMENT.md) for detailed migration guide.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [awesome-language-learning](https://github.com/Vuizur/awesome-language-learning) - Resource inspiration
- [Duolingo](https://www.duolingo.com) - Gamification model reference
