# Initialization Flow Templates

> Templates for the 7-step onboarding process when a new user starts.

**Related Files:**
- [shared_enums.md](shared_enums.md) - CEFR levels, topics, tutor styles

**IMPORTANT Display Rules:**
- Every step MUST display ALL options with numbers (1, 2, 3...)
- Every step MUST show the recommended/default option clearly
- Model MUST NOT skip any options or abbreviate the list
- User can reply with number or text (both should work)

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
    "title": "📊 Step 1/7: Your English Level",
    "message": "What's your current English level?",
    "options": [
      "**1.** A1-A2 - Beginner: Basic conversations, everyday words",
      "**2.** B1-B2 - Intermediate: Work conversations, some idioms ⭐ Recommended",
      "**3.** C1-C2 - Advanced: Complex topics, nuanced expressions"
    ],
    "default": "B1",
    "prompt": "Reply with a number (1-3) or level (e.g., **2** or **B1**)",
    "hint": "💡 Not sure? Most working professionals are B1-B2. You can change this later."
  }
}
```

**Input Mapping:**
| User Input | Value |
|------------|-------|
| 1, A1, A2, beginner | A2 |
| 2, B1, B2, intermediate | B1 |
| 3, C1, C2, advanced | C1 |

---

## Step 2: Topic Preferences

```json
{
  "type": "init_topics",
  "step": 2,
  "display": {
    "title": "🎯 Step 2/7: Your Interests",
    "message": "Which topics interest you most? (Select multiple)",
    "options": [
      "**1.** 🎬 movies - TV shows, films",
      "**2.** 📰 news - Current events",
      "**3.** 🎮 gaming - Video games",
      "**4.** ⚽ sports - Sports & fitness",
      "**5.** 🏢 workplace - Office & business ⭐ Popular",
      "**6.** 💬 social - Friends & parties",
      "**7.** 🏠 daily_life - Shopping, restaurants"
    ],
    "default": "workplace, social, daily_life",
    "prompt": "Reply with numbers (e.g., **1 5 6** or **movies workplace social**)",
    "hint": "💡 Select 2-4 topics. Popular combo: 5 6 7 (workplace + social + daily_life)"
  }
}
```

**Input Mapping:**
| User Input | Value |
|------------|-------|
| 1, movies | movies |
| 2, news | news |
| 3, gaming | gaming |
| 4, sports | sports |
| 5, workplace | workplace |
| 6, social | social |
| 7, daily, daily_life | daily_life |

---

## Step 3: Tutor Style

```json
{
  "type": "init_style",
  "step": 3,
  "display": {
    "title": "🎭 Step 3/7: Tutor Style",
    "message": "How should I teach you?",
    "options": [
      "**1.** 😄 humorous - Fun examples, jokes, pop culture ⭐ Recommended",
      "**2.** 📚 rigorous - Detailed explanations, grammar focus",
      "**3.** 😎 casual - Short & sweet, everyday language",
      "**4.** 👔 professional - Business-focused, formal contexts"
    ],
    "default": "humorous",
    "prompt": "Reply with a number (1-4) or style name (e.g., **1** or **humorous**)"
  }
}
```

**Input Mapping:**
| User Input | Value |
|------------|-------|
| 1, humorous, funny | humorous |
| 2, rigorous, serious | rigorous |
| 3, casual, relaxed | casual |
| 4, professional, formal | professional |

---

## Step 4: Oral/Written Ratio

```json
{
  "type": "init_ratio",
  "step": 4,
  "display": {
    "title": "💬 Step 4/7: Speaking vs Writing",
    "message": "What do you want to focus on?",
    "options": [
      "**1.** 🗣️ Mostly speaking (80%) - Daily conversations, casual chat",
      "**2.** ⚖️ Balanced (50%) - Mix of speaking and writing",
      "**3.** ✍️ Mostly writing (20%) - Emails, formal documents"
    ],
    "default": "70",
    "prompt": "Reply with a number (1-3) or percentage 0-100 (e.g., **1** or **70**)",
    "hint": "💡 Recommended: 70% speaking (most learners want to speak better)"
  }
}
```

**Input Mapping:**
| User Input | Value |
|------------|-------|
| 1, mostly speaking | 80 |
| 2, balanced | 50 |
| 3, mostly writing | 20 |
| 0-100 (number) | that number |

---

## Step 5: Schedule Configuration

```json
{
  "type": "init_schedule",
  "step": 5,
  "display": {
    "title": "⏰ Step 5/7: Schedule Your Learning",
    "message": "When should I send you daily content?",
    "options": [
      "**1.** Morning person: Keypoint 06:45, Quiz 22:45 ⭐ Recommended",
      "**2.** Late riser: Keypoint 08:00, Quiz 23:00",
      "**3.** Custom times (you specify)"
    ],
    "defaults": {
      "keypoint": "06:45",
      "quiz": "22:45"
    },
    "prompt": "Reply with a number (1-3) or custom times (e.g., **1** or **07:00 21:30**)",
    "hint": "💡 Quiz time must be later than keypoint time. Press Enter for defaults."
  }
}
```

**Input Mapping:**
| User Input | Keypoint | Quiz |
|------------|----------|------|
| 1, default, enter | 06:45 | 22:45 |
| 2, late | 08:00 | 23:00 |
| 3, HH:MM HH:MM | first time | second time |

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
    "title": "🔊 Step 6/7: Voice Teaching",
    "message": "Would you like audio versions of knowledge points for listening practice?",
    "options": [
      "**1.** 🔊 Yes - Enable voice teaching ⭐ Recommended",
      "**2.** 🔇 No - Text only, no audio"
    ],
    "speed_options": {
      "description": "If yes, choose your preferred speech speed:",
      "options": [
        "**1.** Very slow (0.5x) - Beginner shadowing",
        "**2.** Slow (0.7x) - Learning pronunciation",
        "**3.** Normal (0.9x) - Daily learning ⭐ Recommended",
        "**4.** Fast (1.3x) - Listening challenge",
        "**5.** Very fast (1.7x) - Advanced training"
      ]
    },
    "default": "yes 3",
    "prompt": "Reply with **1** or **2**. If yes, also pick speed (e.g., **1** or **1 3** or **yes 3**)",
    "hint": "💡 Recommended: Yes with normal speed (option 3). Great for commute listening!"
  }
}
```

**Input Mapping:**
| User Input | Enabled | Speed |
|------------|---------|-------|
| 1, yes, y | true | 0.9 (default) |
| 2, no, n | false | - |
| 1 3, yes 3 | true | 0.9 |
| 1 1, yes 1 | true | 0.5 |
| 1 2, yes 2 | true | 0.7 |
| 1 4, yes 4 | true | 1.3 |
| 1 5, yes 5 | true | 1.7 |

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
    "options": [
      "**1.** ✅ Yes, confirm and start learning",
      "**2.** ✏️ Change something"
    ],
    "prompt": "Reply with **1** or **yes** to confirm, or **2** to adjust.",
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

After user confirms with "yes" or "1", MUST execute the following bash commands to create cron jobs:

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
