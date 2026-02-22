# Emoji & Text Formatting Guide

> Guidelines for emoji decorations and markdown formatting in IM displays.
> Makes content more engaging, scannable, and visually consistent.

**Related Files:**
- [shared_enums.md](shared_enums.md) - Topic, category, formality, quiz type enums with emojis
- [output_rules.md](output_rules.md) - JSON output rules, markdown formatting, platform compatibility

---

## 1. Section Emojis

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

## 5. Feedback Emojis

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

## 10. Formatting Examples

> See [output_rules.md](output_rules.md) for complete formatting rules.

**Key phrase highlighting:**
```json
{
  "dialogue": "💬 A: Hey, can we **touch base**?\n💬 B: Sure!",
  "key_phrase_highlight": "**touch base**"
}
```

**Display object fields:**
| Field | Purpose | Example |
|-------|---------|---------|
| `phrase` | Bold key phrase | `**Let's touch base**` |
| `key_phrase_highlight` | Highlighted in context | `**touch base**` |
