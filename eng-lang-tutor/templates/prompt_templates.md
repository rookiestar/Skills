# LLM Prompt Templates Index

> Templates for generating English learning content.
> Use these templates with state.json data to generate personalized content.

---

## Template Files

This documentation has been split into focused modules for easier navigation:

### Shared Files (Reference First)
| File | Purpose |
|------|---------|
| [prompts/shared_enums.md](prompts/shared_enums.md) | **Shared enums** - Topics, CEFR levels, tutor styles, quiz types, badges |
| [prompts/output_rules.md](prompts/output_rules.md) | **Output rules** - JSON format, markdown syntax, platform compatibility |

### Generation Templates
| File | Purpose |
|------|---------|
| [prompts/keypoint_generation.md](prompts/keypoint_generation.md) | Knowledge point generation template, topic resources |
| [prompts/quiz_generation.md](prompts/quiz_generation.md) | Quiz generation template with question types |
| [prompts/initialization.md](prompts/initialization.md) | 6-step onboarding flow templates |

### Display Templates
| File | Purpose |
|------|---------|
| [prompts/display_guide.md](prompts/display_guide.md) | Emoji usage and text formatting guidelines |
| [prompts/responses.md](prompts/responses.md) | Response templates for stats, config, errors, quiz results |

---

## Quick Reference

### Generation Flow

1. **Keypoint Generation** → Use [keypoint_generation.md](prompts/keypoint_generation.md)
   - Inject user context (CEFR, topic, style)
   - Inject topic resources
   - Apply dedup rules

2. **Quiz Generation** → Use [quiz_generation.md](prompts/quiz_generation.md)
   - Based on today's keypoint
   - 3 questions: multiple_choice + chinglish_fix + fill_blank/dialogue

3. **Display Formatting** → Use [display_guide.md](prompts/display_guide.md)
   - Apply emojis consistently
   - Bold key phrases
   - Never use strikethrough

### Key Rules

> See [prompts/output_rules.md](prompts/output_rules.md) for complete formatting rules.

1. **Output ONLY valid JSON** - no markdown blocks, no extra text
2. **Focus on "How Americans say it"** - NOT Chinese translations
3. **Include display object** - formatted strings for IM display
4. **Use `**text**` for bold** - never use `~~strikethrough~~`

### Reference Sources

| Type | Source | URL Pattern |
|------|--------|-------------|
| Dictionary | Merriam-Webster | `https://www.merriam-webster.com/dictionary/{phrase}` |
| Usage | YouGlish | `https://youglish.com/pronounce/{phrase}/english/us` |

---

## Related Files

- [../references/resources.md](../references/resources.md) - Topic-specific learning resources
- [../examples/sample_keypoint.json](../examples/sample_keypoint.json) - Example keypoint output
- [../examples/sample_quiz.json](../examples/sample_quiz.json) - Example quiz output
