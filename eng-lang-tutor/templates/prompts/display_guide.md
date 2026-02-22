# Emoji & Text Formatting Guide

> Guidelines for emoji decorations and markdown formatting in IM displays.
> Makes content more engaging, scannable, and visually consistent.

**Related Files:**
- [shared_enums.md](shared_enums.md) - Topic, category, formality, quiz type enums with emojis
- [output_rules.md](output_rules.md) - JSON output rules, markdown formatting, platform compatibility

---

## 1. Topic & Category Emojis

> See [shared_enums.md](shared_enums.md) for complete topic/category/formality definitions.

Quick reference for display:
- **Topics**: 🎬 movies, 📰 news, 🎮 gaming, ⚽ sports, 🏢 workplace, 💬 social, 🏠 daily_life
- **Categories**: 💬 oral, ✍️ written
- **Formality**: 😎 casual, 😐 neutral, 🤵 formal

---

## 2. Section Emojis

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

---

## 5. Quiz Type Emojis

> See [shared_enums.md](shared_enums.md#quiz-question-types-题型) for quiz type definitions.

| Question Type | Emoji | Label |
|---------------|-------|-------|
| multiple_choice | 🔤 | 选择题 \| Multiple Choice |
| fill_blank | ✏️ | 填空题 \| Fill in the Blank |
| dialogue_completion | 💬 | 对话补全 \| Dialogue Completion |
| chinglish_fix | 🔧 | Chinglish 修正 \| Fix the Chinglish |

---

## 6. Feedback Emojis

| Feedback | Emoji | Example |
|----------|-------|---------|
| Correct | ✅ | `✅ Correct! 'Touch base' = quick check-in` |
| Wrong | ❌ | `❌ Not quite. Try again!` |
| XP | 💎 | `💎 +10 XP` |
| Progress | ⬜⬜⬜⬜ | `⬜⬜⬜⬜ 0/4 questions` |
| Encourage | 💪🚀 | `💪 Good luck! 加油! 🚀` |

---

## 7. Situation Emojis for Examples

| Situation | Emoji |
|-----------|-------|
| Morning/coffee | ☕ |
| Email/message | 📧 |
| Meeting | 🤝 |
| Phone call | 📱 |
| Office chat | 💬 |
| Lunch break | 🍱 |
| Slack/Teams | 💬 |

---

## 8. Display Object Structure

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

---

## 9. Emoji Usage Rules

> See [output_rules.md](output_rules.md) for complete formatting rules.

1. **Keep it readable**: Don't overuse emojis; 1-2 per line maximum
2. **Be consistent**: Use the same emoji for the same concept
3. **Bilingual labels**: Include both Chinese and English when appropriate
4. **Visual hierarchy**: Use emojis to create visual sections
5. **Positive tone**: Use encouraging emojis for feedback

---

## 10. Bold & Wrong Answer Format

> See [output_rules.md](output_rules.md#markdown-格式规则) for complete formatting rules.

**Bold key phrases**: Use `**phrase**` for main expressions

**Wrong answers (Feishu-compatible):**
- ⛔ Do NOT use `~~strikethrough~~` - doesn't work in Feishu
- ✅ Use ❌ emoji + quotes: `❌ "discuss together"`

---

## 11. Formatting Combinations

Combine formatting with emojis for maximum impact:

```
❌ Wrong: "Let's discuss together."
✅ Correct: **Let's touch base!**

💬 A: "Can we **touch base** on those mockups?"
```

---

## 12. Key Phrase Highlighting in Dialogues

In examples, always highlight the key phrase:

```json
{
  "dialogue": "💬 A: Hey, can we **touch base** on those mockups?\n💬 B: Sure, I'll swing by after lunch.",
  "key_phrase_highlight": "**touch base**"
}
```

---

## 13. Display Object Fields for Formatting

| Field | Purpose | Example |
|-------|---------|---------|
| `phrase` | Bold key phrase | `**Let's touch base**` |
| `phrase_plain` | Unformatted version | `Let's touch base` |
| `key_phrase` | Question key phrase | `**touch base**` |
| `key_phrase_highlight` | Highlighted in context | `**touch base**` |
| `correct_pattern` | Pattern explanation | `**Agree + suggest time**` |

---

## 14. Quick Reference

1. **Bold all key phrases** in display sections
2. **Use ❌ emoji for wrong answers** (NOT strikethrough)
3. **Keep original text** in data fields
4. **Add formatting only** in display fields
5. **Be consistent** - same phrase, same format
