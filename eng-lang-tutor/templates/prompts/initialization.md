# Initialization Flow Templates

> Templates for the 7-step onboarding process when a new user starts.

**Related Files:**
- [shared_enums.md](shared_enums.md) - CEFR levels, topics, tutor styles

---

## Step 0: Welcome Message

```json
{
  "type": "init_welcome",
  "step": 0,
  "display": {
    "title": "👋 Welcome to American English Tutor!",
    "message": "Hi! I'm your personal English tutor. I'll help you learn authentic American expressions that native speakers actually use.\n\nLet me ask you a few questions to personalize your learning experience.",
    "prompt": "Ready to get started? Reply with **start** or **开始** to begin.",
    "footer": "───────────────────\n🎯 This takes about 2 minutes"
  }
}
```

---

## Step 1: CEFR Level Selection

```json
{
  "type": "init_cefr",
  "step": 1,
  "display": {
    "title": "📊 Step 1/6: Your English Level",
    "message": "What's your current English level?",
    "options": [
      "**A1-A2**: Beginner - Basic conversations, everyday words",
      "**B1-B2**: Intermediate - Work conversations, some idioms",
      "**C1-C2**: Advanced - Complex topics, nuanced expressions"
    ],
    "prompt": "Reply with your level (e.g., **B1**, **B2**, **C1**)",
    "hint": "💡 Not sure? Most working professionals are B1-B2. You can change this later."
  }
}
```

---

## Step 2: Topic Preferences

```json
{
  "type": "init_topics",
  "step": 2,
  "display": {
    "title": "🎯 Step 2/6: Your Interests",
    "message": "Which topics interest you most?",
    "topics": [
      "🎬 movies - TV shows, films",
      "📰 news - Current events",
      "🎮 gaming - Video games",
      "⚽ sports - Sports & fitness",
      "🏢 workplace - Office & business",
      "💬 social - Friends & parties",
      "🏠 daily_life - Shopping, restaurants"
    ],
    "prompt": "List your interests (e.g., **movies workplace gaming**)",
    "example": "Example: **movies workplace gaming**"
  }
}
```

---

## Step 3: Tutor Style

```json
{
  "type": "init_style",
  "step": 3,
  "display": {
    "title": "🎭 Step 3/6: Tutor Style",
    "message": "How should I teach you?",
    "options": [
      "😄 **humorous** - Fun examples, jokes, pop culture",
      "📚 **rigorous** - Detailed explanations, grammar focus",
      "😎 **casual** - Short & sweet, everyday language",
      "👔 **professional** - Business-focused, formal contexts"
    ],
    "prompt": "Reply with: **humorous**, **rigorous**, **casual**, or **professional**"
  }
}
```

---

## Step 4: Oral/Written Ratio

```json
{
  "type": "init_ratio",
  "step": 4,
  "display": {
    "title": "💬 Step 4/6: Speaking vs Writing",
    "message": "What do you want to focus on?",
    "options": [
      "🗣️ **Mostly speaking** - Daily conversations, casual chat",
      "⚖️ **Balanced** - Mix of speaking and writing",
      "✍️ **Mostly writing** - Emails, formal documents"
    ],
    "prompt": "Reply with a number 0-100 for speaking focus (e.g., **70** = 70% speaking)"
  }
}
```

---

## Step 5: Schedule Configuration

```json
{
  "type": "init_schedule",
  "step": 5,
  "display": {
    "title": "⏰ Step 5/6: Schedule Your Learning",
    "message": "When should I send you daily content?",
    "defaults": {
      "keypoint": "☀️ **Keypoint** (morning lesson): Default **06:45**",
      "quiz": "🌙 **Quiz** (evening practice): Default **22:45**"
    },
    "prompt": "Reply with times in 24-hour format (e.g., **07:00 21:30**) or press Enter for defaults.",
    "hint": "💡 Quiz time must be later than keypoint time. Example: '07:00 21:30' or just press Enter for defaults."
  }
}
```

**Validation Rules:**
- Both times must be in HH:MM format (24-hour)
- Quiz time must be later than keypoint time
- If user only provides one time, ask for the second
- If invalid format, show error and re-prompt

---

## Step 6: Voice Teaching Configuration

```json
{
  "type": "init_voice",
  "step": 6,
  "display": {
    "title": "🔊 Step 6/6: Voice Teaching",
    "message": "Would you like audio versions of knowledge points for listening practice?",
    "options": [
      "🔊 **Yes** - Enable voice teaching (recommended)",
      "🔇 **No** - Text only, no audio"
    ],
    "speed_options": {
      "description": "If yes, choose your preferred speech speed:",
      "options": [
        "**1** - Very slow (0.5x) - Beginner shadowing",
        "**2** - Slow (0.7x) - Learning pronunciation",
        "**3** - Normal (0.9x) - Daily learning (recommended)",
        "**4** - Fast (1.3x) - Listening challenge",
        "**5** - Very fast (1.7x) - Advanced training"
      ]
    },
    "prompt": "Reply **yes** or **no**. If yes, also specify speed (e.g., **yes 3** or **yes normal**)",
    "hint": "💡 You can change this anytime with the **config** command."
  }
}
```

**Speed Mapping:**
| User Input | Speed Value | Description |
|------------|-------------|-------------|
| 1, very slow | 0.5 | Beginner shadowing |
| 2, slow | 0.7 | Learning pronunciation |
| 3, normal (default) | 0.9 | Daily learning |
| 4, fast | 1.3 | Listening challenge |
| 5, very fast | 1.7 | Advanced training |

**State Update:**
```json
{
  "tts_settings": {
    "enabled": true,
    "provider": "edge-tts",
    "speed": 0.9,
    "voices": {
      "narrator": null,
      "dialogue_a": null,
      "dialogue_b": null
    }
  }
}
```
- If `voices` values are null, use provider defaults

---

## Step 7: Confirmation

```json
{
  "type": "init_confirm",
  "step": 7,
  "display": {
    "title": "✅ All Set! Here's Your Profile:",
    "summary": {
      "level": "📊 Level: {cefr_level}",
      "topics": "🎯 Topics: {top_topics}",
      "style": "🎭 Style: {tutor_style}",
      "focus": "💬 Focus: {oral_ratio}% speaking",
      "schedule": "⏰ Schedule: Keypoint at {keypoint_time}, Quiz at {quiz_time}",
      "voice": "🔊 Voice: {voice_status}"
    },
    "prompt": "Does this look right? Reply **yes** to confirm or **change** to adjust.",
    "footer": "───────────────────\n🚀 Your first lesson starts tomorrow!"
  }
}
```

**Voice Status Display:**
- If enabled: "Enabled, {speed_desc} speed"
- If disabled: "Disabled (text only)"

---

## Completion

```json
{
  "type": "init_complete",
  "display": {
    "title": "🎉 Welcome Aboard!",
    "message": "You're all set! Here's what happens next:\n\n"
      "☀️ **{keypoint_time}** - Daily knowledge point\n"
      "🌙 **{quiz_time}** - Daily quiz",
    "cron_setup": "I'll create cron jobs for your schedule now. You can change this anytime with the **schedule** command.",
    "first_lesson": "Want your first lesson now? Reply **keypoint** or **知识点**",
    "footer": "───────────────────\n💡 Say **help** anytime to see all commands"
  }
}
```

---

## Cron Job Creation (after Step 7 confirmation)

After user confirms with "yes", MUST execute the following bash commands to create cron jobs:

```bash
# Parse times from schedule
KEYPOINT_TIME="06:45"  # Default, replace with user's keypoint_time
QUIZ_TIME="22:45"      # Default, replace with user's quiz_time

# Extract hour and minute
KEYPOINT_HOUR=$(echo $KEYPOINT_TIME | cut -d: -f1)
KEYPOINT_MIN=$(echo $KEYPOINT_TIME | cut -d: -f2)
QUIZ_HOUR=$(echo $QUIZ_TIME | cut -d: -f1)
QUIZ_MIN=$(echo $QUIZ_TIME | cut -d: -f2)

# Create cron jobs using openclaw
# Keypoint job
${KEYPOINT_MIN} ${KEYPOINT_HOUR} * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's keypoint." --mode now

# Quiz job
${QUIZ_MIN} ${QUIZ_HOUR} * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's quiz invitation." --mode now
```

**IMPORTANT:** The cron job creation requires:
1. Parse user's `keypoint_time` and `quiz_time` from state.json schedule
2. Execute the bash command to register each cron job
3. Log the event using `state_manager.py append_event`
