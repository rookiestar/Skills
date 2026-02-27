# Knowledge Point Generation Template

> Main template for generating daily English learning content.

**Related Files:**
- [shared_enums.md](shared_enums.md) - Topics, CEFR levels, tutor styles, quiz types
- [output_rules.md](output_rules.md) - JSON output rules, markdown formatting

---

## 1. Generation Prompt

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
> **See [output_rules.md](output_rules.md) for complete JSON/Markdown formatting rules.**

1. Focus on "How Americans say it" - NOT Chinese translations
2. Must include: scene context, alternatives, Chinglish trap + correction
3. Use authentic expressions from the resource references above
4. Include pronunciation tips for casual speech (gonna, gotta, wanna, etc.)
5. AVOID these recent topics (14-day dedup): {excluded_topics}
6. **Include reference links** - provide authoritative sources for verification
7. **Include formatted display object** - MUST include `display` object with all formatted fields using `**text**` for bold
8. **Never use strikethrough** - Use ❌ emoji for wrong answers instead of `~~text~~`
9. **NEVER add [AUDIO:...] tags** - Audio is handled separately by the system
```

---

## 2. Reference Sources

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

---

## 3. Content Guidelines

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

---

## 4. Output Schema

```json
{
  "_meta": {
    "prompt_version": "keypoint_gen_v2.1"
  },
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

## 5. Topic Resource Injection

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

## 6. CEFR Level Guidelines

> See [shared_enums.md](shared_enums.md#cefr-levels-能力等级) for level definitions.

Adjust content complexity based on CEFR level.

---

## 7. Tutor Style Variations

> See [shared_enums.md](shared_enums.md#tutor-styles-导师风格) for style definitions.
