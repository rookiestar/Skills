# Quiz Generation Template

> Template for generating daily quizzes based on knowledge points.

---

## Quiz Generation Prompt

```markdown
Based on today's knowledge point, generate a 3-question quiz calibrated to user's CEFR level.

## USER CONTEXT
- CEFR Level: {cefr_level} (A1=Beginner to C2=Proficient)

## KNOWLEDGE POINT
{keypoint_json}

## CEFR DIFFICULTY CALIBRATION

| Level | Question Characteristics |
|-------|-------------------------|
| A1-A2 | Simple recognition, obvious distractors, direct context matching |
| B1-B2 | Nuanced usage, subtle distractors, requires understanding context |
| C1-C2 | Complex scenarios, idiomatic variations, cultural nuance testing |

**For B1-B2 (most users):**
- Multiple choice: Distractors should be grammatically correct but contextually wrong
- Chinglish fix: Use subtle errors (preposition, article, word choice) not obvious mistakes
- Create NEW scenarios that differ from the keypoint examples

## QUESTION TYPE REQUIREMENTS (3 questions total)
1. **multiple_choice** (required): Test expression recognition - 10 XP
2. **chinglish_fix** (required): Identify and correct Chinglish - 15 XP
3. **fill_blank OR dialogue_completion** (random): Pick one randomly - 12 XP

## QUESTION GUIDELINES

### Multiple Choice (10 XP)
- 4 options (A, B, C, D)
- Only 1 correct answer
- **Distractors MUST be plausible** - grammatically correct but semantically wrong
- Test understanding of meaning or usage in a NEW context (not copied from keypoint)
- For B2+: Include one distractor that's "almost correct" to test nuance

### Chinglish Fix (15 XP)
- Show a sentence with Chinglish expressions
- **Create a NEW sentence** - NOT the example from the keypoint
- For B2+: Use subtle errors (wrong preposition, article misuse, slight word order)
- Include explanation in the answer

### Fill in the Blank (12 XP)
- Use "___" for the blank
- Provide word bank with 3 options
- **Create a NEW context/sentence** - NOT copied from keypoint
- Test the expression in a different situation

### Dialogue Completion (12 XP)
- Show partial dialogue with NEW context
- Ask what should come next
- Test natural conversation flow

## ⛔ CRITICAL PROHIBITIONS ⛔

1. **NEVER copy questions directly from keypoint content**
   - Create NEW scenarios and contexts
   - Change the situation while testing the same expression

2. **NEVER reveal the answer in hints or question text**
   - Hint format: "💡 Think about what Americans say in this situation"
   - FORBIDDEN: "💡 The answer is 'touch base'" or showing the phrase directly

3. **NEVER make distractors obviously wrong**
   - All 4 options should sound plausible
   - For B2+: At least one distractor should be a common learner error

## STRICT RULES
1. Output ONLY valid JSON - no markdown, no extra text
2. All questions must relate to today's knowledge point
3. **Difficulty MUST match CEFR level** - harder for B2+ users
4. Include encouraging feedback in display fields
5. Total XP should be around 35-40
6. **End sentences with proper punctuation** - periods for statements, question marks for questions
7. **Use NEW contexts** - never copy-paste from keypoint examples
```

---

## Output Schema

> **CRITICAL:** Display fields must NOT reveal answers before user responds.

```json
{
  "quiz_date": "{today_date}",
  "keypoint_fingerprint": "{fingerprint}",
  "cefr_level": "{cefr_level}",
  "questions": [
    {
      "id": 1,
      "type": "multiple_choice",
      "question": "The question text - MUST be a NEW context, not copied from keypoint",
      "context": "NEW scenario description",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B",
      "explanation": "Why this is correct...",
      "xp_value": 10,
      "display": {
        "type_emoji": "🔤",
        "type_name": "选择题 | Multiple Choice",
        "question_formatted": "💬 {question}",
        "context_formatted": "📱 {context}",
        "options_formatted": ["⬜ A. ...", "⬜ B. ...", "⬜ C. ...", "⬜ D. ..."],
        "hint": "💡 Think about the context - which fits naturally?",
        "correct_feedback": "✅ Correct! **{key_phrase}** = {meaning}",
        "wrong_feedback": "❌ Not quite. The answer was **{correct_answer}**. {explanation}",
        "xp_display": "💎 +10 XP"
      }
    },
    {
      "id": 2,
      "type": "chinglish_fix",
      "question": "Fix this sentence - MUST be NEW sentence, not from keypoint",
      "chinglish_sentence": "A NEW sentence with Chinglish error...",
      "correct_answer": "The corrected version...",
      "explanation": "Why the original was wrong...",
      "xp_value": 15,
      "display": {
        "type_emoji": "🔧",
        "type_name": "Chinglish 修正 | Fix the Chinglish",
        "question_formatted": "🔧 What's wrong with this sentence?",
        "sentence_formatted": "📝 \"{chinglish_sentence}\"",
        "hint": "💡 How would an American say this naturally?",
        "correct_feedback": "✅ Fixed! **{correct_phrase}** sounds much more natural!",
        "wrong_feedback": "❌ Better: **{correct_sentence}**\n💡 {explanation}",
        "xp_display": "💎 +15 XP"
      }
    },
    {
      "id": 3,
      "type": "fill_blank",
      "question": "Complete the sentence - MUST be NEW context",
      "context": "NEW dialogue or situation with ___ blank",
      "word_bank": ["phrase1", "phrase2", "phrase3"],
      "correct_answer": "phrase1",
      "explanation": "...",
      "xp_value": 12,
      "display": {
        "type_emoji": "✏️",
        "type_name": "填空题 | Fill in the Blank",
        "question_formatted": "✏️ Fill in the blank:",
        "context_formatted": "💬 {context_with_blank}",
        "word_bank_formatted": "📦 Options: [ {opt1} | {opt2} | {opt3} ]",
        "hint": "💡 Consider the formality and context.",
        "correct_feedback": "✅ Perfect! **{answer}** fits perfectly here!",
        "wrong_feedback": "❌ The answer was **{correct_answer}**. {explanation}",
        "xp_display": "💎 +12 XP"
      }
    }
  ],
  "total_xp": 37,
  "passing_score": 70,
  "display": {
    "header": "📝 今日测验 | Daily Quiz",
    "date": "📅 {quiz_date}",
    "difficulty": "📊 Level: **{cefr_level}**",
    "topic": "🏷️ Topic: **{topic_name}**",
    "instructions": "🎯 3道小题，答对2道就过关！3 questions, get 2 right to pass!",
    "progress_bar": "⬜⬜⬜ 0/3 questions",
    "xp_summary": "💎 Total XP: {total_xp} | 🏆 Pass: 2/3 correct",
    "footer": "───────────────────\n💪 Good luck! 加油! 🚀"
  }
}
```

**Note:** Removed `key_phrase_summary` from display - it reveals the answer before quiz starts!

---

## XP Values Summary

| Question Type | XP Value | Description |
|---------------|----------|-------------|
| multiple_choice | 10 | Four-option recognition |
| chinglish_fix | 15 | Identify and correct |
| fill_blank | 12 | Complete with word bank |
| dialogue_completion | 12 | Choose conversation response |

**Total XP**: ~37 (10 + 15 + 12)
**Passing Score**: 70% (2/3 correct)
