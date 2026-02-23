---
name: eng-lang-tutor
description: |
  地道美式英语导师 - 提供每日知识点、Quiz测验等学习内容。
  支持游戏化学习（XP/连胜/等级/徽章）。
  触发场景：学习英语、英语知识点、Quiz、错题本、学习进度。
  被 cron job 调用以实现定期内容推送。
---

# American English Tutor

## Overview

Teaches authentic American English expressions, avoiding Chinglish patterns.
Delivers personalized content via daily knowledge points and quizzes.
Includes Duolingo-style gamification (XP, streaks, levels, badges).

## Core Workflow

### 1. Daily Knowledge Point Generation

```
Input: state.json (user preferences, CEFR level, recent topics)
Process:
  1. Load user preferences from state.json
  2. Load recent topic fingerprints (14 days) for deduplication
  3. Select topic based on user preference weights
  4. Generate knowledge point via LLM (pure JSON output)
  5. Validate JSON schema
  6. Save to daily/YYYY-MM-DD/keypoint.json
  7. Update state.json recent_topics
  8. Append event to logs/events_YYYY-MM.jsonl
Output: keypoint.json
```

### 2. Quiz Generation

```
Input: keypoint.json
Process:
  1. Read today's keypoint.json
  2. Generate 3 questions (fixed pattern):
     - 1 multiple_choice (10 XP)
     - 1 chinglish_fix (15 XP)
     - 1 fill_blank OR dialogue_completion (12 XP, random)
  3. Save to daily/YYYY-MM-DD/quiz.json (with answers)
Output: quiz.json (~37 XP total)
```

### 3. Answer Evaluation

```
Input: quiz.json, user_answers.json
Process:
  1. Compare user answers with correct answers
  2. Calculate XP (base + streak multiplier + perfect bonus)
  3. Update state.json (XP, streak, level, badges)
  4. Record wrong answers to error_notebook
Output: results.json, updated state.json
```

## Quiz Types

> See [templates/prompts/shared_enums.md](templates/prompts/shared_enums.md#quiz-question-types-题型) for full definitions.

| Type | XP | Daily |
|------|-----|-------|
| multiple_choice | 10 | 1 (required) |
| chinglish_fix | 15 | 1 (required) |
| fill_blank / dialogue_completion | 12 | 0-1 (random) |

**Daily Quiz:** 3 questions, ~37 XP, pass with 2/3 correct

## Gamification System

### XP & Levels

This system has two independent level systems:
- **Ability Level (CEFR)**: A1-C2, determines content difficulty
- **Activity Level (Level)**: 1-20, measures engagement depth

> See [templates/prompts/shared_enums.md](templates/prompts/shared_enums.md) for level stages and badge definitions.

### Streak System
- Consecutive days of study builds streak
- Streak multiplier: `1.0 + (streak * 0.05)`, max 2.0x
- Streak freeze costs 50 gems

## Key Scripts

| Script | Purpose |
|--------|---------|
| state_manager.py | State persistence, event logging, error notebook |
| cron_push.py | Scheduled content push (keypoint/quiz placeholders) |
| scorer.py | Answer evaluation, XP calculation |
| gamification.py | Streak/level/badge logic |
| dedup.py | 14-day content deduplication |
| command_parser.py | Natural language command parsing |
| constants.py | Shared constants (level thresholds, level names) |
| utils.py | Utility functions (safe divide, deep merge) |
| cli.py | CLI entry point for state management |

## CLI Commands

> These bash commands are used by the Agent to execute operations. Data is stored in `~/.openclaw/state/eng-lang-tutor/` by default. Do NOT specify `--data-dir` unless using a custom location.

### Content Management
```bash
# Save daily content (keypoint/quiz)
python3 scripts/state_manager.py save_daily --content-type keypoint --content '<JSON>'

# Record keypoint view
python3 scripts/state_manager.py record_view [--date YYYY-MM-DD]
```

### Stats & Config
```bash
# Display learning progress
python3 scripts/state_manager.py stats

# Display current configuration
python3 scripts/state_manager.py config

# Update configuration
python3 scripts/state_manager.py config --cefr B2
python3 scripts/state_manager.py config --style professional
python3 scripts/state_manager.py config --oral-ratio 80
```

### Error Notebook
```bash
# List errors (paginated)
python3 scripts/state_manager.py errors [--page 1] [--per-page 5] [--month YYYY-MM]

# Get random errors for review
python3 scripts/state_manager.py errors --random 5

# Get error statistics
python3 scripts/state_manager.py errors --stats

# Get errors for review session
python3 scripts/state_manager.py errors --review 5
```

### Schedule
```bash
# Display current schedule
python3 scripts/state_manager.py schedule

# Update schedule (quiz_time must be later than keypoint_time)
python3 scripts/state_manager.py schedule --keypoint-time 07:00 --quiz-time 21:00
```

## Core Principles

> See [templates/prompts/keypoint_generation.md](templates/prompts/keypoint_generation.md) for detailed generation rules.

1. **Always output valid JSON** - No markdown, no extra text
2. **Focus on "How Americans say it"** - NOT translation
3. **Every knowledge point must include**: Scene context, alternatives, Chinglish trap
4. **14-day deduplication** - No repeated topics or expressions

## File Structure

```
~/.openclaw/state/eng-lang-tutor/  # Default data location
  state.json              # Core state (streak/xp/preferences)
  logs/
    events_2026-02.jsonl  # Monthly event log
  daily/
    2026-02-20/
      keypoint.json       # Today's knowledge point
      quiz.json           # Today's quiz
      user_answers.json   # User's answers
```

**Note:** Data location can be customized via `OPENCLAW_STATE_DIR` environment variable.

## JSON Schemas

See templates/ directory:
- state_schema.json
- keypoint_schema.json
- quiz_schema.json

## Resource References

**Prompt Templates** (templates/prompts/):
- [shared_enums.md](templates/prompts/shared_enums.md) - Topics, CEFR levels, styles, badges
- [output_rules.md](templates/prompts/output_rules.md) - JSON/markdown formatting rules
- [keypoint_generation.md](templates/prompts/keypoint_generation.md) - Knowledge point generation
- [quiz_generation.md](templates/prompts/quiz_generation.md) - Quiz generation
- [display_guide.md](templates/prompts/display_guide.md) - Emoji and formatting guide
- [initialization.md](templates/prompts/initialization.md) - Onboarding flow
- [responses.md](templates/prompts/responses.md) - Response templates

**Other Resources:**
- [references/resources.md](references/resources.md) - Themed English learning resources
- [templates/prompt_templates.md](templates/prompt_templates.md) - Prompt template index

## Examples

See examples/ directory for sample outputs.

---

## User Commands

The bot recognizes these natural language commands:

### Initialization
| Command | Aliases | Description |
|---------|---------|-------------|
| `start` | `begin`, `开始`, `初始化`, `你好` | Start the onboarding process |

### Learning Content
| Command | Aliases | Description |
|---------|---------|-------------|
| `keypoint` | `知识点`, `今天`, `today` | View today's knowledge point |
| `keypoint history` | `知识点 历史`, `昨天`, `yesterday` | View historical keypoints |
| `quiz` | `测验`, `test`, `测试` | Take today's quiz (once per day) |

### Progress & Stats
| Command | Aliases | Description |
|---------|---------|-------------|
| `stats` | `进度`, `统计`, `level`, `XP` | View learning progress |
| `errors` | `错题本`, `mistakes` | View error notebook (recent 5) |
| `errors more` | `错题本 更多` | Next 5 errors |
| `errors 2026-02` | `错题本 2026-02` | Filter by month |
| `errors random 5` | `错题本 随机5` | Random 5 for review |
| `errors stats` | `错题本 统计` | Show error statistics |
| `errors review` | `错题本 复习`, `错题复习` | Start error review session (5 questions) |

### Settings
| Command | Aliases | Description |
|---------|---------|-------------|
| `config` | `设置`, `preferences` | View current settings |
| `set level B2` | `设置等级 B2` | Change CEFR level |
| `set style professional` | `设置风格 专业` | Change tutor style |
| `schedule` | `时间表`, `推送时间` | View/change schedule |

### Help
| Command | Aliases | Description |
|---------|---------|-------------|
| `help` | `帮助`, `怎么用` | Show available commands |

---

## Initialization Flow

> See [templates/prompts/initialization.md](templates/prompts/initialization.md) for detailed onboarding templates.

6-step onboarding: Welcome → CEFR Level → Topic Interests → Tutor Style → Oral/Written Ratio → Schedule → Confirm

**Step 6 Completion:** Set `initialized=true` + Create cron jobs for keypoint/quiz push times.

**State Fields:**
- `initialized`: Boolean - Whether user completed onboarding
- `onboarding_step`: Integer (0-6) - Current step

---

## Response Scenarios

> **TIMEZONE AWARENESS:** All "today" date checks should use `state.json schedule.timezone` (default: Asia/Shanghai) to ensure consistent behavior across server locations. File paths like `daily/2026-02-21/` are timezone-specific.

---

## ⛔ MANDATORY BASH COMMANDS - READ THIS FIRST ⛔

**When generating content via LLM, you MUST execute bash commands to persist data to disk.**

### After Keypoint Generation (MANDATORY)
```
Step 1: LLM generates keypoint JSON
Step 2: ⛔ EXECUTE THIS BASH COMMAND (do NOT skip):
        python3 scripts/state_manager.py save_daily --content-type keypoint --content '<ESCAPED_JSON>'
        (This auto-generates audio and saves to audio/YYYY-MM-DD/keypoint_full.mp3)
Step 3: ⛔ EXECUTE THIS BASH COMMAND (do NOT skip):
        python3 scripts/state_manager.py record_view
Step 4: Send audio file via message tool (if audio exists):
        - Read keypoint.json and check if audio.composed field exists
        - If exists, send audio file using message tool with media parameter
        - Audio path: ~/.openclaw/state/eng-lang-tutor/{audio.composed}
Step 5: Display formatted content to user
```

### Audio File Sending (After Keypoint Save)

When keypoint is saved, audio is auto-generated. Send it to user with backward compatibility:

**Step 1: Check voice bubble capability**
```bash
echo $FEISHU_VOICE_BUBBLE_ENABLED
```

**Step 2a: If FEISHU_VOICE_BUBBLE_ENABLED=true (enhanced mode)**

Send BOTH voice bubble AND file attachment for best compatibility:

```json
// Voice bubble (handled by enhanced OpenClaw gateway)
{
  "action": "send",
  "media": "~/.openclaw/media/{audio.composed}",
  "asVoice": true
}

// File attachment (fallback for progress bar control)
{
  "action": "send",
  "media": "~/.openclaw/media/{audio.composed}",
  "caption": "🔊 今日知识点语音版"
}
```

**Step 2b: If FEISHU_VOICE_BUBBLE_ENABLED not set or false (standard mode)**

Only send file attachment:
```json
{
  "action": "send",
  "media": "~/.openclaw/media/{audio.composed}",
  "caption": "🔊 今日知识点语音版"
}
```

**Audio file info is stored in keypoint.json:**
```json
{
  "audio": {
    "composed": "eng-lang-tutor/2026-02-23/keypoint_full.mp3",
    "duration_seconds": 37.7,
    "generated_at": "2026-02-23T02:20:14"
  }
}
```

**IMPORTANT:**
- Audio is saved to `~/.openclaw/media/` (OpenClaw's allowed media directory)
- Always send audio file BEFORE displaying text content
- The `audio.composed` field contains the path relative to `~/.openclaw/media/`
- Enhanced mode (voice bubble) requires OpenClaw gateway patch for Feishu

### After Quiz Generation (MANDATORY)
```
Step 1: LLM generates quiz JSON
Step 2: ⛔ EXECUTE THIS BASH COMMAND (do NOT skip):
        python3 scripts/state_manager.py save_daily --content-type quiz --content '<ESCAPED_JSON>'
Step 3: Present quiz questions to user
```

**JSON Escaping Rules:**
- Wrap content in single quotes: `'{"key": "value"}'`
- Escape internal single quotes: `'` → `'\''`
- Example: `'{"title": "It'\''s a test"}'`

**⛔ FAILURE TO EXECUTE BASH COMMANDS = DATA LOSS ⛔**

---

### Quiz Already Completed
```
User: "quiz"
Bot checks: completion_status.quiz_completed_date == today?
  → YES: "You've already completed today's quiz! 🎉 Score: X/Y"
  → NO: Check quiz.json exists (~/.openclaw/state/eng-lang-tutor/daily/YYYY-MM-DD/quiz.json) and quiz.generated == true?
      → YES: Load quiz and present questions
      → NO:
         1. Check if keypoint.json exists for today
            → If NO: Generate keypoint via LLM first
            → ⛔ EXECUTE: python3 scripts/state_manager.py save_daily --content-type keypoint --content '<ESCAPED_JSON>'
         2. Generate quiz via LLM
         3. Set generated=true in the JSON content
         4. ⛔ EXECUTE: python3 scripts/state_manager.py save_daily --content-type quiz --content '<ESCAPED_JSON>'
         5. Present questions to user
```

**⛔ CRITICAL: You MUST execute bash commands to save BEFORE presenting to user.**

### Manual Quiz Before Keypoint Push
```
User manually requests quiz before scheduled keypoint push time
Bot checks: Does keypoint.json exist for today?
  → NO:
     1. IMMEDIATELY generate keypoint via LLM (do NOT say "will notify later")
     2. ⛔ EXECUTE: python3 scripts/state_manager.py save_daily --content-type keypoint --content '<ESCAPED_JSON>'
     3. Generate quiz via LLM
     4. ⛔ EXECUTE: python3 scripts/state_manager.py save_daily --content-type quiz --content '<ESCAPED_JSON>'
     5. Present quiz questions to user
     → All in ONE response - user should receive quiz immediately
  → YES: Proceed with quiz generation normally (see Quiz Already Completed section)

This ensures learning sequence is preserved even for early learners.
```

**⛔ CRITICAL: NEVER tell user "will generate later and notify" - always generate immediately.**
**⛔ CRITICAL: You MUST execute the bash save commands BEFORE presenting content to user.**

### Keypoint Query
```
User: "keypoint" or "知识点" or Cron Push
Bot checks: Does keypoint.json exist for today (~/.openclaw/state/eng-lang-tutor/daily/YYYY-MM-DD/keypoint.json)?
  → NO:
     1. Generate new keypoint via LLM
     2. Set generated=true in the JSON content
     3. ⛔ EXECUTE: python3 scripts/state_manager.py save_daily --content-type keypoint --content '<ESCAPED_JSON>'
     4. ⛔ EXECUTE: python3 scripts/state_manager.py record_view
     5. Send audio file via message tool (if audio.composed exists)
     6. Display formatted content to user (REMOVE any [AUDIO:...] tags from text)
  → YES: Check keypoint.generated
      → TRUE: ⛔ EXECUTE: python3 scripts/state_manager.py record_view, then send audio and display
      → FALSE: Follow steps 1-6 above
```

**⛔ CRITICAL:**
1. **You MUST execute bash commands to save BEFORE displaying to user**
2. **You MUST remove `[AUDIO:...]` tags from display text** - these are NOT supported and will show as plain text
3. **You SHOULD send audio via message tool** if `audio.composed` field exists

**Display Fields (from keypoint.json `display` object):**

| Field | Description |
|-------|-------------|
| `title` | Main title with emoji |
| `topic_tag` | Topic label |
| `formality_tag` | Formality level |
| `scene_text` | Scene description |
| `expressions_formatted` | Array of formatted expressions |
| `alternatives_formatted` | Bullet list of alternatives |
| `chinglish_formatted` | Wrong/Correct comparison |
| `examples_formatted` | Array of dialogue examples |
| `extended_formatted` | Extended learning content |
| `references_formatted` | Reference links |
| `footer` | Date and footer info |

> **IMPORTANT:**
> - Output assembled Markdown text directly, NOT JSON
> - **DO NOT display the `audio` field in text** - it's for message tool media sending only
> - See `templates/prompt_templates.md` Section 10.3 for full assembly template

### Keypoint History
```
User: "keypoint history" or "知识点 历史"
Bot scans: ~/.openclaw/state/eng-lang-tutor/daily/ directory for YYYY-MM-DD/keypoint.json files
  → NO files found: "📚 No history yet. Start learning with 'keypoint' today!"
  → YES: List keypoints (most recent first), max 10 entries:
      - {date}: {title/topic} (e.g., "2026-02-20: Touch Base - 工作沟通")
```

**Display Format:**
```markdown
📚 **知识点历史记录**

| 日期 | 主题 | 查看 |
|------|------|------|
| 2026-02-20 | Touch Base - 工作沟通 | 输入 `keypoint 2026-02-20` |
| 2026-02-19 | Gonna/Wanna - 口语缩写 | 输入 `keypoint 2026-02-19` |
...

💡 输入 `keypoint 日期` 查看历史知识点详情
```

### Historical Keypoint
```
User: "keypoint 昨天" or "keypoint 2026-02-19"
Bot checks: Does keypoint.json exist for that date?
  → YES: Display
  → NO: "No keypoint found for that date. Try 'keypoint today'."
```

### Config Display
```
User: "config" or "设置"
Bot reads: state.json preferences
Output: Card format with formatted text (see Output Format below)
```

### Stats Display
```
User: "stats" or "进度"
Bot reads: state.json user + progress
Output: Card format with emoji and formatted text
```

---

## Response Output Format

> IMPORTANT: All responses use platform-agnostic Markdown format. See `templates/prompt_templates.md` Section 10 for detailed formatting rules and `examples/` for sample outputs.

### Quick Reference

- **Format**: Standard Markdown (compatible with Feishu, Discord, Telegram, Slack)
- **Bold**: `**text**`
- **Links**: `[text](url)`
- **Emojis**: Use liberally for visual sections
- **Dividers**: `───────────────────`

### Response Templates

All response templates are documented in `templates/prompt_templates.md` Section 10:

| Template | Section | Description |
|----------|---------|-------------|
| Keypoint Display | 10.3 | Daily knowledge point output |
| Stats Display | 10.4 | Learning progress stats |
| Config Display | 10.5 | User settings display |
| Errors Display | 10.6 | Error notebook (paginated) |
| Error Review | 10.7 | Error review session flow |
| Quiz Result | 10.8 | Quiz completion results |

---

## Completion Tracking

### State Fields

```json
{
  "completion_status": {
    "quiz_completed_date": "2026-02-20",
    "keypoint_view_history": [
      {"date": "2026-02-20", "viewed_at": "2026-02-20T06:45:00"}
    ]
  }
}
```

### Rules

1. **Quiz**: Can only take once per day (resets at midnight)
2. **Keypoint**: Can view multiple times (including historical pushed keypoints)

---

## Cron Configuration

### Default Schedule (UTC+8 / Asia/Shanghai)

| Task | Default Time | Description |
|------|--------------|-------------|
| Keypoint Push | 06:45 | Daily knowledge point |
| Quiz Push | 22:45 | Daily quiz |

### Crontab Template

```bash
# /etc/cron.d/eng-lang-tutor
CRON_TZ=Asia/Shanghai

# 6:45 AM - Keypoint push
45 6 * * * openclaw agent --channel discord --message "☕ Good morning!" --agent eng-lang-tutor

# 10:45 PM - Quiz push
45 22 * * * openclaw agent --channel discord --message "🌙 Quiz time!" --agent eng-lang-tutor
```

### User-Customizable Schedule

Users can customize their schedule via commands:
```
set schedule keypoint 7:00
set schedule quiz 21:00
```

Stored in `state.json`:
```json
{
  "schedule": {
    "keypoint_time": "07:00",
    "quiz_time": "21:00",
    "timezone": "Asia/Shanghai"
  }
}

---

## Additional Scripts

| Script | Purpose |
|--------|---------|
| command_parser.py | Parse user messages to determine intent |
| cron_push.py | Handle scheduled content generation |

