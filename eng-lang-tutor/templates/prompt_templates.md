# LLM Prompt Templates

> Templates for generating English learning content.
> Use these templates with state.json data to generate personalized content.

---

## 1. Knowledge Point Generation Template

```markdown
You are an authentic American English tutor. Generate a daily knowledge point.

## USER CONTEXT
- CEFR Level: {cefr_level} (A1=Beginner to C2=Proficient)
- Topic Focus: {topic} (movies/news/gaming/sports/workplace/social/daily_life)
- Tutor Style: {tutor_style} (humorous/rigorous/casual/professional)
- Expression Type: {oral_written_ratio}% oral expressions, {written_ratio}% written

## RESOURCE REFERENCES
{topic_resources}

## STRICT RULES
1. Output ONLY valid JSON - no markdown, no code blocks, no extra text
2. Focus on "How Americans say it" - NOT Chinese translations
3. Must include: scene context, alternatives, Chinglish trap + correction
4. Use authentic expressions from the resource references above
5. Include pronunciation tips for casual speech (gonna, gotta, wanna, etc.)
6. AVOID these recent topics (14-day dedup): {excluded_topics}
7. **End sentences with proper punctuation** - periods for statements, question marks for questions
8. **Include reference links** - provide authoritative sources for verification
9. **Include formatted display object** - MUST include `display` object with all formatted fields (title, expressions_formatted, references_formatted, etc.) using `**text**` for bold
10. **Never use strikethrough** - Use ❌ emoji for wrong answers instead of `~~text~~`

## REFERENCE SOURCES

When generating knowledge points, include links to these authoritative sources:

| Type | Source | URL Pattern | Description |
|------|--------|-------------|-------------|
| **Dictionary** | Merriam-Webster | `https://www.merriam-webster.com/dictionary/{phrase}` | Most authoritative American English dictionary |
| **Usage** | YouGlish | `https://youglish.com/pronounce/{phrase}/english/us` | Real YouTube videos with the phrase |
| **Etymology** | Etymonline | `https://www.etymonline.com/word/{word}` | Word origin and history |
| **Frequency** | Google Ngram | `https://books.google.com/ngrams/graph?content={phrase}` | Usage frequency over time |

**URL Encoding:** Replace spaces with `%20` in URLs.

**Reference Requirements:**
- `dictionary` is REQUIRED - always include Merriam-Webster link
- `usage_context` is REQUIRED - YouGlish helps users hear real usage
- `etymology` is OPTIONAL - include for interesting origin stories
- `frequency` is OPTIONAL - include for frequency comparison

**Example:**
```json
{
  "references": {
    "dictionary": {
      "source": "merriam-webster",
      "url": "https://www.merriam-webster.com/dictionary/touch%20base",
      "note": "Official definition and usage examples"
    },
    "usage_context": {
      "source": "youglish",
      "url": "https://youglish.com/pronounce/touch%20base/english/us",
      "note": "Hear it in 1000+ real YouTube videos"
    }
  }
}
```

## CONTENT GUIDELINES

### Scene
- Describe a realistic situation where this expression is used
- Include formality level (casual/neutral/formal)
- Make it relatable to the CEFR level

### Expressions
- Primary expression + 1-2 alternatives
- Include pronunciation tips for natural speech
- Usage notes explaining when to use

### Chinglish Trap
- Show what Chinese speakers TYPICALLY say (the wrong version)
- Provide the correct American expression
- Explain WHY the wrong version sounds unnatural

### Examples
- Use dialogue format with 2-3 exchanges
- Make conversations feel natural and authentic
- Include context for each dialogue

## OUTPUT SCHEMA (JSON only)
{
  "date": "{today_date}",
  "topic_fingerprint": "unique_lowercase_with_underscores",
  "category": "oral|written",
  "topic": "{topic}",
  "scene": {
    "context": "Brief description of the situation",
    "formality": "casual|neutral|formal"
  },
  "expressions": [
    {
      "phrase": "The American expression",
      "pronunciation_tip": "How to say it naturally",
      "usage_note": "When and how to use this"
    }
  ],
  "alternatives": [
    "Another way to say it 1",
    "Another way to say it 2"
  ],
  "chinglish_trap": {
    "wrong": "What Chinese speakers typically say",
    "correct": "The natural American way",
    "explanation": "Why the wrong version sounds off"
  },
  "examples": [
    {
      "situation": "Context for example",
      "dialogue": ["Speaker A: ...", "Speaker B: ..."]
    }
  ],
  "extended_learning": {
    "related_phrases": ["phrase1", "phrase2"],
    "cultural_note": "Brief cultural context",
    "common_mistakes": ["mistake1"]
  },
  "references": {
    "dictionary": {
      "source": "merriam-webster",
      "url": "https://www.merriam-webster.com/dictionary/{phrase}",
      "note": "Definition and usage examples"
    },
    "usage_context": {
      "source": "youglish",
      "url": "https://youglish.com/pronounce/{phrase}/english/us",
      "note": "Hear it in real YouTube videos"
    }
  },
  "display": {
    "title": "🏢 今日知识点 | Today's Knowledge Point",
    "topic_tag": "🏷️ 主题: **{topic_name}** | {topic_name_en}",
    "formality_tag": "📊 正式度: **{formality}**",
    "scene_intro": "🎬 场景 | Scene",
    "scene_text": "{scene_context}",
    "expressions_title": "💬 核心表达 | Key Expressions",
    "expressions_formatted": [
      {
        "emoji": "✨",
        "phrase": "**{phrase}**",
        "phrase_plain": "{phrase}",
        "pronunciation": "🔊 {pronunciation_tip}",
        "usage": "💡 {usage_note}"
      }
    ],
    "alternatives_title": "🔄 其他说法 | Alternatives",
    "alternatives_formatted": "• **{alt_1}**\n• **{alt_2}**",
    "chinglish_title": "⚠️ Chinglish 陷阱 | Chinglish Trap",
    "chinglish_formatted": "❌ Wrong: \"{wrong}\"\n✅ Correct: **{correct}**\n\n📝 {explanation}",
    "examples_title": "🗣️ 对话示例 | Example Dialogues",
    "examples_formatted": [
      {
        "situation_emoji": "☕",
        "situation": "{situation_name}",
        "dialogue": "💬 A: {line_1}\n💬 B: {line_2}",
        "key_phrase_highlight": "**{key_phrase}**"
      }
    ],
    "extended_title": "📚 延伸学习 | Extended Learning",
    "extended_formatted": "🔗 Related: **{related_1}** | **{related_2}**\n\n🌎 {cultural_note}",
    "references_title": "📖 权威参考 | References",
    "references_formatted": "📚 [Merriam-Webster]({dict_url}) - {dict_note}\n🎬 [YouGlish]({usage_url}) - {usage_note}",
    "footer": "───────────────────\n📅 {date} | 📝 Take the quiz to earn XP!"
  }
}
```

---

## 2. Quiz Generation Template

```markdown
Based on today's knowledge point, generate a light 3-question quiz.

## KNOWLEDGE POINT
{keypoint_json}

## QUESTION TYPE REQUIREMENTS (3 questions total)
1. **multiple_choice** (required): Test expression recognition - 10 XP
2. **chinglish_fix** (required): Identify and correct Chinglish - 15 XP
3. **fill_blank OR dialogue_completion** (random): Pick one randomly - 12 XP

## QUESTION GUIDELINES

### Multiple Choice (10 XP)
- 4 options (A, B, C, D)
- Only 1 correct answer
- Distractors should be plausible but clearly wrong
- Test understanding of meaning or usage

### Chinglish Fix (15 XP)
- Show a sentence with Chinglish expressions
- Ask to identify the issue and provide correct version
- Include explanation in the answer

### Fill in the Blank (12 XP)
- Use "___" for the blank
- Provide word bank with 3 options
- Test the main expression from the knowledge point

### Dialogue Completion (12 XP)
- Show partial dialogue with context
- Ask what should come next
- Test natural conversation flow

## STRICT RULES
1. Output ONLY valid JSON - no markdown, no extra text
2. All questions must relate to today's knowledge point
3. Keep it light and fun - don't make questions too hard
4. Include encouraging feedback in display fields
5. Total XP should be around 35-40
6. **End sentences with proper punctuation** - periods for statements, question marks for questions

## OUTPUT SCHEMA (JSON only)
{
  "quiz_date": "{today_date}",
  "keypoint_fingerprint": "{fingerprint}",
  "questions": [
    {
      "id": 1,
      "type": "multiple_choice",
      "question": "The question text",
      "context": "Optional scenario description",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B",
      "explanation": "Why this is correct...",
      "xp_value": 10,
      "display": {
        "type_emoji": "🔤",
        "type_name": "选择题 | Multiple Choice",
        "question_formatted": "💬 {question_with_bold_key_phrase}",
        "context_formatted": "📱 {context}",
        "options_formatted": ["⬜ A. ...", "⬜ B. ...", "⬜ C. ...", "⬜ D. ..."],
        "correct_feedback": "✅ Correct! **{key_phrase}** = {meaning}",
        "wrong_feedback": "❌ Not quite. **{key_phrase}** means...",
        "key_phrase": "**{key_phrase}**",
        "xp_display": "💎 +10 XP"
      }
    },
    {
      "id": 2,
      "type": "chinglish_fix",
      "question": "Identify and fix the Chinglish",
      "context": "...",
      "correct_answer": "...",
      "explanation": "...",
      "xp_value": 15,
      "display": {
        "type_emoji": "🔧",
        "type_name": "Chinglish 修正 | Fix the Chinglish",
        "question_formatted": "🔧 {question}",
        "email_formatted": "📧 {email_content}",
        "hint": "💡 Hint: How would an American say this?",
        "correct_feedback": "✅ Fixed! **{correct_phrase}** sounds much better!",
        "wrong_feedback": "❌ '{wrong}' → **{correct}**",
        "answer_formatted": "📝 Better: {corrected_sentence}",
        "key_phrase": "**{key_phrase}**",
        "xp_display": "💎 +15 XP"
      }
    },
    {
      "id": 3,
      "type": "fill_blank",
      "question": "Complete the sentence",
      "context": "...",
      "word_bank": ["option1", "option2", "option3"],
      "correct_answer": "option1",
      "explanation": "...",
      "xp_value": 12,
      "display": {
        "type_emoji": "✏️",
        "type_name": "填空题 | Fill in the Blank",
        "question_formatted": "✏️ {question}",
        "context_formatted": "💼 {context_with_blank}",
        "word_bank_formatted": "📦 Word Bank: [ **{opt1}** | {opt2} | {opt3} ]",
        "correct_feedback": "✅ Perfect! **{answer}** is correct!",
        "wrong_feedback": "❌ Try **{correct_answer}** instead!",
        "key_phrase": "**{key_phrase}**",
        "xp_display": "💎 +12 XP"
      }
    }
  ],
  "total_xp": 37,
  "passing_score": 70,
  "display": {
    "header": "📝 今日测验 | Daily Quiz",
    "date": "📅 {quiz_date}",
    "topic": "🏷️ Topic: **{keypoint_fingerprint}**",
    "instructions": "🎯 3道小题，答对2道就过关！3 questions, get 2 right to pass!",
    "progress_bar": "⬜⬜⬜ 0/3 questions",
    "key_phrase_summary": "🔑 Key Phrase: **{key_phrase}** = {translation}",
    "xp_summary": "💎 Total XP: {total_xp} | 🏆 Pass: 2/3 correct",
    "footer": "───────────────────\n💪 Good luck! 加油! 🚀"
  }
}
```

---

## 3. Topic Resource Injection

When generating content, inject topic-specific resources:

```python
TOPIC_RESOURCES = {
    "movies": """
    Reference expressions from TV shows:
    - Friends: "How you doin'?", "Could I BE any more...?"
    - The Office: "That's what she said", "Touch base"
    - Gossip Girl: "No offense", "None taken", "Done and done"
    Focus on: dialogue patterns, humor, sarcasm, casual speech
    """,

    "news": """
    Reference vocabulary from:
    - CNN 10: Current events, clear explanations
    - VOA: Simplified news vocabulary
    Focus on: formal register, topic-specific vocabulary, clear structure
    """,

    "gaming": """
    Reference gaming terminology:
    - Core: NPC, spawn, loot, grind, level up, buff, nerf
    - Multiplayer: party, squad, GG, clutch, carry
    - Slang in daily use: "That was clutch", "GG"
    Focus on: casual speech, slang, gaming-specific vocabulary
    """,

    "sports": """
    Reference sports vocabulary:
    - Basketball: dunk, buzzer beater, pick and roll
    - Sports idioms: "step up to the plate", "ballpark figure"
    Focus on: energetic expressions, idioms used in business
    """,

    "workplace": """
    Reference workplace expressions:
    - Office idioms: touch base, circle back, bandwidth
    - Meeting phrases: "Let's get the ball rolling", "wrap up"
    - Email language: formal yet natural
    Focus on: professional communication, formal/informal switching
    """,

    "social": """
    Reference social expressions:
    - Greetings: "What's up?", "How's it going?"
    - Making plans: "Let's hang out", "grab coffee"
    - Casual responses: "Not much, you?", "Can't complain"
    Focus on: casual speech, fillers, natural conversation flow
    """,

    "daily_life": """
    Reference daily life expressions:
    - Shopping: "Just looking", "Can I get a discount?"
    - Restaurant: "I'd like the...", "Check, please"
    - Services: Asking for help, making requests
    Focus on: practical communication, politeness strategies
    """
}
```

---

## 5. CEFR Level Guidelines

Adjust content complexity based on CEFR level:

| Level | Vocabulary | Sentence Length | Topics |
|-------|------------|-----------------|--------|
| A1-A2 | Basic, high-frequency | Short, simple | Daily routines, shopping |
| B1-B2 | Intermediate, some idioms | Medium, some complex | Work, travel, social |
| C1-C2 | Advanced, nuanced | Varied, sophisticated | Abstract, professional |

### A1-A2 Guidelines
- Use very common expressions
- Short dialogues (2-3 exchanges)
- Simple Chinglish traps
- Everyday situations

### B1-B2 Guidelines
- Include common idioms
- Medium dialogues (3-4 exchanges)
- Nuanced Chinglish traps
- Work and social situations

### C1-C2 Guidelines
- Complex expressions and idioms
- Longer dialogues (4+ exchanges)
- Subtle Chinglish traps (tone, formality)
- Professional and abstract topics

---

## 6. Tutor Style Variations

Adjust tone based on tutor_style:

### Humorous
- Include funny examples
- Light-hearted explanations
- Pop culture references
- Jokes in cultural notes

### Rigorous
- Detailed explanations
- Multiple examples
- Grammar focus
- Formal language

### Casual
- Conversational tone
- Short, punchy explanations
- Everyday examples
- Slang-friendly

### Professional
- Business-appropriate examples
- Formal language focus
- Workplace scenarios
- Email/communication tips

---

## 7. Emoji Display Guidelines

> Add emoji decorations to make IM conversations more engaging and scannable.

### 7.1 Topic Emojis

| Topic | Emoji | Chinese Label |
|-------|-------|---------------|
| movies | 🎬 | 影视 |
| news | 📰 | 新闻 |
| gaming | 🎮 | 游戏 |
| sports | ⚽ | 体育 |
| workplace | 🏢 | 职场 |
| social | 💬 | 社交 |
| daily_life | 🏠 | 生活 |

### 7.2 Category Emojis

| Category | Emoji |
|----------|-------|
| oral | 💬 口语 |
| written | ✍️ 书面 |

### 7.3 Formality Emojis

| Formality | Emoji |
|-----------|-------|
| casual | 😎 随意 |
| neutral | 😐 中性 |
| formal | 🤵 正式 |

### 7.4 Section Emojis

| Section | Emoji | Example |
|---------|-------|---------|
| Title | 🏢 | `🏢 今日知识点 \| Today's Knowledge Point` |
| Scene | 🎬 | `🎬 场景 \| Scene` |
| Expressions | ✨💬 | `✨ Let's touch base` |
| Pronunciation | 🔊 | `🔊 Sounds like 'touch base'` |
| Usage | 💡 | `💡 Brief, informal check-in` |
| Alternatives | 🔄 | `🔄 其他说法 \| Alternatives` |
| Chinglish | ⚠️❌✅ | `❌ Wrong ... ✅ Correct` |
| Examples | 🗣️💭 | `🗣️ 对话示例 \| Example Dialogues` |
| Extended | 📚 | `📚 延伸学习 \| Extended Learning` |
| Cultural | 🌎 | `🌎 Cultural Note` |
| Mistakes | 🚫 | `🚫 Common Mistakes` |
| Related | 🔗 | `🔗 Related phrases` |

### 7.5 Quiz Type Emojis

| Question Type | Emoji | Label |
|---------------|-------|-------|
| multiple_choice | 🔤 | 选择题 \| Multiple Choice |
| fill_blank | ✏️ | 填空题 \| Fill in the Blank |
| dialogue_completion | 💬 | 对话补全 \| Dialogue Completion |
| chinglish_fix | 🔧 | Chinglish 修正 \| Fix the Chinglish |

### 7.6 Feedback Emojis

| Feedback | Emoji | Example |
|----------|-------|---------|
| Correct | ✅ | `✅ Correct! 'Touch base' = quick check-in` |
| Wrong | ❌ | `❌ Not quite. Try again!` |
| XP | 💎 | `💎 +10 XP` |
| Progress | ⬜⬜⬜⬜ | `⬜⬜⬜⬜ 0/4 questions` |
| Encourage | 💪🚀 | `💪 Good luck! 加油! 🚀` |

### 7.7 Situation Emojis for Examples

| Situation | Emoji |
|-----------|-------|
| Morning/coffee | ☕ |
| Email/message | 📧 |
| Meeting | 🤝 |
| Phone call | 📱 |
| Office chat | 💬 |
| Lunch break | 🍱 |
| Slack/Teams | 💬 |

### 7.8 Display Object Structure

When generating content, include a `display` object with formatted strings:

```json
{
  "display": {
    "title": "🏢 今日知识点 | Today's Knowledge Point",
    "topic_tag": "🏷️ 主题: 职场口语 | Workplace Oral",
    "formality_tag": "📊 正式度: 中性 | Neutral",
    "scene_intro": "🎬 场景 | Scene",
    "expressions_title": "💬 核心表达 | Key Expressions",
    "chinglish_title": "⚠️ Chinglish 陷阱 | Chinglish Trap",
    "examples_title": "🗣️ 对话示例 | Example Dialogues",
    "footer": "───────────────────\n📅 2026-02-20 | 📝 Take the quiz to earn XP!"
  }
}
```

### 7.9 Emoji Usage Rules

1. **Keep it readable**: Don't overuse emojis; 1-2 per line maximum
2. **Be consistent**: Use the same emoji for the same concept
3. **Bilingual labels**: Include both Chinese and English when appropriate
4. **Visual hierarchy**: Use emojis to create visual sections
5. **Positive tone**: Use encouraging emojis for feedback
6. **Cultural sensitivity**: Avoid emojis that might be confusing across cultures

---

## 8. Text Formatting Guidelines

> Use Markdown formatting to highlight key phrases and create visual emphasis in IM displays.

### 8.1 Bold for Key Phrases

Use `**phrase**` for the main expressions being taught:

| Use Case | Format | Example |
|----------|--------|---------|
| Key phrase | `**touch base**` | ✨ **Let's touch base** |
| Correct answer | `**Correct: "touch base"**` | ✅ Correct: **Let's touch base!** |
| Important term | `**first mention**` | The phrase **'touch base'** comes from baseball |

### 8.2 Wrong Answers Format (Feishu-Compatible)

> IMPORTANT: Do NOT use `~~strikethrough~~` - it doesn't work in Feishu cards. Use ❌ emoji + quotes instead.

| Use Case | Format | Example |
|----------|--------|---------|
| Wrong expression | `❌ "discuss together"` | ❌ "Let's discuss together" |
| Chinglish | `❌ "communicate with you"` | ❌ "I want to communicate with you" |

### 8.3 Formatting Combinations

Combine formatting with emojis for maximum impact:

```
❌ Wrong: "Let's discuss together."
✅ Correct: **Let's touch base!**

💬 A: "Can we **touch base** on those mockups?"
```

### 8.4 Key Phrase Highlighting in Dialogues

In examples, always highlight the key phrase:

```json
{
  "dialogue": "💬 A: Hey, can we **touch base** on those mockups?\n💬 B: Sure, I'll swing by after lunch.",
  "key_phrase_highlight": "**touch base**"
}
```

### 8.5 Display Object Fields for Formatting

| Field | Purpose | Example |
|-------|---------|---------|
| `phrase` | Bold key phrase | `**Let's touch base**` |
| `phrase_plain` | Unformatted version | `Let's touch base` |
| `key_phrase` | Question key phrase | `**touch base**` |
| `key_phrase_highlight` | Highlighted in context | `**touch base**` |
| `correct_pattern` | Pattern explanation | `**Agree + suggest time**` |
| `key_phrase_summary` | Quiz summary | `🔑 Key Phrase: **touch base** = 快速沟通` |

### 8.6 Formatting Rules

1. **Bold all key phrases** in display sections
2. **Use ❌ emoji for wrong answers** in Chinglish traps and quizzes (NOT strikethrough)
3. **Keep original text** in data fields (phrase, alternatives, etc.)
4. **Add formatting only** in display fields
5. **Be consistent** - always format the same phrase the same way
6. **Don't over-format** - only highlight the key learning points

---

## 9. Initialization Flow Templates

> Templates for the 6-step onboarding process when a new user starts.

### 9.1 Welcome Message (Step 0)

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

### 9.2 CEFR Level Selection (Step 1)

```json
{
  "type": "init_cefr",
  "step": 1,
  "display": {
    "title": "📊 Step 1/5: Your English Level",
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

### 9.3 Topic Preferences (Step 2)

```json
{
  "type": "init_topics",
  "step": 2,
  "display": {
    "title": "🎯 Step 2/5: Your Interests",
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

### 9.4 Tutor Style (Step 3)

```json
{
  "type": "init_style",
  "step": 3,
  "display": {
    "title": "🎭 Step 3/5: Tutor Style",
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

### 9.5 Oral/Written Ratio (Step 4)

```json
{
  "type": "init_ratio",
  "step": 4,
  "display": {
    "title": "💬 Step 4/5: Speaking vs Writing",
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

### 9.6 Schedule Configuration (Step 5)

```json
{
  "type": "init_schedule",
  "step": 5,
  "display": {
    "title": "⏰ Step 5/5: Schedule Your Learning",
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

### 9.7 Confirmation (Step 6)

```json
{
  "type": "init_confirm",
  "step": 6,
  "display": {
    "title": "✅ All Set! Here's Your Profile:",
    "summary": {
      "level": "📊 Level: {cefr_level}",
      "topics": "🎯 Topics: {top_topics}",
      "style": "🎭 Style: {tutor_style}",
      "focus": "💬 Focus: {oral_ratio}% speaking",
      "schedule": "⏰ Schedule: Keypoint at {keypoint_time}, Quiz at {quiz_time}"
    },
    "prompt": "Does this look right? Reply **yes** to confirm or **change** to adjust.",
    "footer": "───────────────────\n🚀 Your first lesson starts tomorrow!"
  }
}
```

### 9.8 Completion

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

**Cron Job Creation (after Step 6 confirmation):**

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

---

## 10. Response Templates

> Templates for various response scenarios.

### 10.1 Already Completed Responses

```json
{
  "quiz_already_done": {
    "display": {
      "title": "✅ Already Completed!",
      "message": "You've already finished today's quiz. Great job! 🎉",
      "stats": "Your score: {score}/{total} | XP earned: {xp}",
      "next_quiz": "Come back tomorrow at 10:45 PM for a new quiz!",
      "alternative": "💡 Want to review? Say **errors** to see your wrong answers."
    }
  }
}
```

### 10.2 Not Available Responses

```json
{
  "keypoint_not_found": {
    "display": {
      "title": "📅 No Keypoint Found",
      "message": "No knowledge point exists for {date}.",
      "hint": "Try **keypoint today** for today's content.",
      "history": "Or say **keypoint history** to see recent keypoints."
    }
  },
  "quiz_not_ready": {
    "display": {
      "title": "⏰ Quiz Not Ready Yet",
      "message": "Today's quiz will be available at 10:45 PM.",
      "alternative": "Want to study? Say **keypoint** to review today's content!"
    }
  }
}
```

### 10.2.1 Keypoint History Response

**When user says:** `keypoint history`, `知识点 历史`, `昨天`, `yesterday`

**Logic:**
1. Scan `data/daily/` directory for all `YYYY-MM-DD/keypoint.json` files
2. Sort by date descending (most recent first)
3. Extract `display.title` or `topic` from each keypoint

**Empty History Response:**
```markdown
📚 **知识点历史记录**

暂无历史记录。从今天开始学习吧！

💡 输入 **keypoint** 或 **知识点** 获取今日内容
```

**With History Response:**
```markdown
📚 **知识点历史记录**

| 日期 | 主题 |
|------|------|
| 2026-02-21 | 🏢 Touch Base - 工作沟通 |
| 2026-02-20 | 🎮 GG - 游戏用语 |
| 2026-02-19 | 🗣️ Gonna/Wanna - 口语缩写 |

💡 输入 **keypoint 日期** 查看详情，如 `keypoint 2026-02-20`
```

**CRITICAL:** The history list is populated from persisted `data/daily/YYYY-MM-DD/keypoint.json` files. If keypoints are not saved to this location, history will be empty.

### 10.3 Keypoint Display Template

> IMPORTANT: Use `**text**` for bold. Never use `~~strikethrough~~`. Output Markdown text directly, NOT JSON.

**Assembly Flow:**

When displaying a keypoint, read the `display` object and assemble fields in this order:

```markdown
{title}

| 主题 | **{topic_name}** |
|------|------------------|
| 正式度 | **{formality}** |

───────────────────
{scene_intro}

{scene_text}

───────────────────
{expressions_title}

{for each item in expressions_formatted:
  {emoji} {phrase}
  {pronunciation}
  {usage}

}

───────────────────
{alternatives_title}

{alternatives_formatted}

───────────────────
{chinglish_title}

{chinglish_formatted}

───────────────────
{examples_title}

{for each item in examples_formatted:
  {situation_emoji} {situation}
  {dialogue}

}

───────────────────
{extended_title}

{extended_formatted}

───────────────────
{references_title}

{references_formatted}

───────────────────
{footer}
```

**Display Object Structure (for generation):**

```json
{
  "display": {
    "title": "🏢 今日知识点 | Today's Knowledge Point",
    "topic_tag": "🏷️ 主题: **{topic_name}** | {topic_name_en}",
    "formality_tag": "📊 正式度: **{formality}**",
    "scene_intro": "🎬 场景 | Scene",
    "scene_text": "{scene_context}",
    "expressions_title": "💬 核心表达 | Key Expressions",
    "expressions_formatted": [
      {
        "emoji": "✨",
        "phrase": "**{phrase}**",
        "pronunciation": "🔊 {pronunciation_tip}",
        "usage": "💡 {usage_note}"
      }
    ],
    "alternatives_title": "🔄 其他说法 | Alternatives",
    "alternatives_formatted": "• **{alt_1}**\n• **{alt_2}**",
    "chinglish_title": "⚠️ Chinglish 陷阱 | Chinglish Trap",
    "chinglish_formatted": "❌ Wrong: \"{wrong}\"\n✅ Correct: **{correct}**\n\n📝 {explanation}",
    "examples_title": "🗣️ 对话示例 | Example Dialogues",
    "examples_formatted": [
      {
        "situation_emoji": "☕",
        "situation": "{situation_name}",
        "dialogue": "💬 A: {line_1}\n💬 B: {line_2}",
        "key_phrase_highlight": "**{key_phrase}**"
      }
    ],
    "extended_title": "📚 延伸学习 | Extended Learning",
    "extended_formatted": "🔗 Related: **{related_1}** | **{related_2}**\n\n🌎 {cultural_note}",
    "references_title": "📖 权威参考 | References",
    "references_formatted": "📚 [{dict_source}]({dict_url}) - {dict_note}\n🎬 [{usage_source}]({usage_url}) - {usage_note}",
    "footer": "───────────────────\n📅 {date} | 📝 Take the quiz to earn XP!"
  }
}
```

**Variables:**
- `{topic_name}`: Chinese topic name (e.g., 职场口语)
- `{topic_name_en}`: English topic name (e.g., Workplace Oral)
- `{formality}`: Formality level (随意/中性/正式)
- `{scene_context}`: Brief scene description
- `{phrase}`: Key expression phrase
- `{pronunciation_tip}`: Pronunciation tips
- `{usage_note}`: Usage notes
- `{alt_N}`: Alternative expressions
- `{wrong}`: The Chinglish/wrong expression
- `{correct}`: The correct American expression
- `{explanation}`: Why the wrong version is wrong
- `{situation_name}`: Example situation
- `{dialogue}`: Dialogue with **bold** key phrases
- `{related_N}`: Related phrases
- `{dict_source}`: Dictionary source name (e.g., Merriam-Webster)
- `{dict_url}`: Dictionary URL
- `{dict_note}`: Brief note about dictionary entry
- `{usage_source}`: Usage context source name (e.g., YouGlish)
- `{usage_url}`: Usage context URL
- `{usage_note}`: Brief note about usage examples

### 10.4 Stats Display Template

> IMPORTANT: Output Markdown text directly, NOT JSON. Read from state.json and format as shown.

**Data Source:** `data/state.json`

**Fields to Read:**
- `user.xp` → current XP
- `user.streak` → streak days
- `user.level` → activity level (1-20)
- `user.gems` → gems count
- `progress.correct_rate` → accuracy percentage
- `progress.badges` → earned badges list

**Markdown Output Format:**

```markdown
📊 **Your Learning Progress**

• 等级: **{level}** ({level_name})
• XP: **{current_xp}** / {next_level_xp} (**{progress}%**)
• 连胜: **{streak}** 天 (倍数: **{multiplier}x**)
• 正确率: **{correct_rate}%**
• 徽章: **{badges_count}**/6
• 宝石: **{gems}**

───────────────────
Keep it up! 💪
```

**Level Names:**
- Level 1-5: Starter (启程者)
- Level 6-10: Traveler (行路人)
- Level 11-15: Explorer (探索者)
- Level 16-20: Pioneer (开拓者)

**Multiplier Calculation:** `1.0 + (streak * 0.05)`, max 2.0x

### 10.5 Config Display Template

> IMPORTANT: Output Markdown text directly, NOT JSON. Read from state.json and format as shown.

**Data Source:** `data/state.json`

**Fields to Read:**
- `preferences.cefr_level` → CEFR level (A1-C2)
- `preferences.topic_weights` → topic preferences with weights
- `preferences.tutor_style` → tutor style
- `preferences.oral_ratio` → speaking focus percentage
- `schedule.keypoint_time` → keypoint push time
- `schedule.quiz_time` → quiz push time

**Markdown Output Format:**

```markdown
⚙️ **Your Settings**

• CEFR 等级: **{cefr_level}**
• 主题偏好: **{topics_list}**
• 导师风格: **{tutor_style}**
• 口语占比: **{oral_ratio}%**
• 知识点推送: **{keypoint_time}**
• Quiz 推送: **{quiz_time}**

───────────────────
💡 Say **set level B2** to change your level
```

### 10.6 Errors Display Template (Paginated)

> IMPORTANT: Output Markdown text directly, NOT JSON. Read from state.json error_notebook and format as shown.

**Data Source:** `data/state.json` → `error_notebook` array

**Fields to Read:**
- `error_notebook` → array of error records
- Each error has: `date`, `question`, `user_answer`, `correct_answer`, `reviewed`

**Markdown Output Format:**

```markdown
📓 **Error Notebook**

📊 统计: **{total}** 条错题 (未复习: **{unreviewed}**)

❌ 最近 **5** 条:

**{date_1}**
Q: {question_1}
Your answer: {user_answer_1}
✅ Correct: **{correct_answer_1}**

**{date_2}**
Q: {question_2}
Your answer: {user_answer_2}
✅ Correct: **{correct_answer_2}**

[显示 5 条，第 1/{total_pages} 页]

───────────────────
📄 输入 **"错题本 更多"** 查看下5条
📄 输入 **"错题本 2026-02"** 查看特定月份
📄 输入 **"错题本 随机5"** 随机复习5条
📄 输入 **"错题本 统计"** 查看完整统计
📄 输入 **"错题本 复习"** 开始错题复习
```

**Pagination Commands:**
- `errors` / `错题本` → Show recent 5 errors
- `errors more` / `错题本 更多` → Next 5 errors
- `errors page N` → Go to page N
- `errors 2026-02` → Filter by month
- `errors random 5` → Random 5 for review
- `errors stats` → Show statistics only
- `errors review` → Start interactive review

### 10.7 Error Review Session Template

> IMPORTANT: Output Markdown text directly, NOT JSON. Error review gives NO XP.

**Question Display:**
```markdown
📓 **错题复习**

📊 进度: **{current}/{total}**

**Q:** {question}
A. {option_a}
B. {option_b}
C. {option_c}
D. {option_d}

───────────────────
💡 输入 **A/B/C/D** 作答
```

**Correct Answer Response:**
```markdown
✅ **正确！**

🎯 **{correct_answer}** 是地道的表达！

📊 本题已从错题本中移除 ✓

───────────────────
📝 继续下一题？输入 **继续**
```

**Wrong Answer Response:**
```markdown
❌ **错误！**

✅ 正确答案: **{correct_answer}**

📝 {explanation}

📊 本题错误次数：**{wrong_count}**

───────────────────
📝 继续下一题？输入 **继续**
```

**Review Complete Summary:**
```markdown
📓 **错题复习完成！**

• 本次正确率: **{correct}/{total}**
• 已清除: **{cleared}** 道错题
• 仍需复习: **{remaining}** 道错题
• Error Slayer 进度: **{progress}/30**

───────────────────
💪 继续加油！输入 **错题本 复习** 再次挑战
```

**Variables:**
- `{current}`: Current question number
- `{total}`: Total questions in session (default 5)
- `{wrong_count}`: Number of times this question was answered incorrectly
- `{cleared}`: Number of errors cleared this session
- `{remaining}`: Number of errors still needing review
- `{progress}`: Current progress toward Error Slayer badge

### 10.8 Quiz Result Display Template

> IMPORTANT: Output Markdown text directly, NOT JSON. Calculate XP from quiz answers.

**Markdown Output Format:**

```markdown
📊 **Quiz Results**

• 分数: **{correct}/{total}** (**{accuracy}%**)
• 状态: {status_emoji} {status_text}
• XP 获得: **+{total_xp} XP**
• 连胜: **{old_streak}** → **{new_streak}** 天
• 总 XP: **{total_xp_earned}**

💎 XP 明细:
  • Base: **{base_xp} XP**
  • Streak Bonus: **{multiplier}x** ({streak} day streak)
  {perfect_bonus}

───────────────────
📝 Come back tomorrow for a new quiz!
```

**Variables:**
- `{status_emoji}`: ✅ for passed, ❌ for failed
- `{status_text}`: "Passed! Great job! 🎉" or "Keep trying! 💪"
- `{perfect_bonus}`: "• Perfect Bonus: **+20 XP**" (only if 100% correct)

### 10.9 Output Format Rules

> CRITICAL: All responses must use platform-agnostic Markdown. OpenClaw handles platform-specific conversions.

**Universal Markdown Format:**

Output standard Markdown that works across all platforms (Feishu, Discord, Telegram, Slack):

```markdown
🏢 **Title Here**

**Label:** Value

───────────────────

📝 **Section Title**

Content with **bold** and [links](url).

───────────────────

📅 Footer info
```

**Rules:**

1. **Use standard Markdown** - Compatible with all platforms
2. **Bold syntax**: Use `**text**` for bold
3. **Never use** `~~strikethrough~~` - use ❌ emoji instead
4. **Line breaks**: Use blank lines between sections
5. **Bullets**: Use `•` for bullet points
6. **Emojis**: Include at the start of each section
7. **Punctuation**: End sentences properly (`.` or `?` or `!`)
8. **Links**: Use `[text](url)` format

**Platform Compatibility:**

| Syntax | Feishu | Discord | Telegram | Slack |
|--------|--------|---------|----------|-------|
| `**bold**` | ✅ | ✅ | ✅ | ✅ |
| `[link](url)` | ✅ | ✅ | ✅ | ✅ |
| Emoji | ✅ | ✅ | ✅ | ✅ |
