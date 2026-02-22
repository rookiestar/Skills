# Quiz Generation Template

> Template for generating daily quizzes based on knowledge points.

---

## Quiz Generation Prompt

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
```

---

## Output Schema

```json
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

## XP Values Summary

| Question Type | XP Value | Description |
|---------------|----------|-------------|
| multiple_choice | 10 | Four-option recognition |
| chinglish_fix | 15 | Identify and correct |
| fill_blank | 12 | Complete with word bank |
| dialogue_completion | 12 | Choose conversation response |

**Total XP**: ~37 (10 + 15 + 12)
**Passing Score**: 70% (2/3 correct)
