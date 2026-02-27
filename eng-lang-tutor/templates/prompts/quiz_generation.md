# Quiz Generation Template

> Template for generating daily quizzes based on knowledge points.

**Related Files:**
- [shared_enums.md](shared_enums.md) - Quiz types, XP values, CEFR levels
- [output_rules.md](output_rules.md) - JSON output rules, markdown formatting

---

## Quiz Generation Prompt

```markdown
Based on today's knowledge point, generate a 3-question quiz calibrated to user's CEFR level.

## USER CONTEXT
- CEFR Level: {cefr_level} (A1=Beginner to C2=Proficient)

## KNOWLEDGE POINT
{keypoint_json}

## CEFR DIFFICULTY CALIBRATION - 6 LEVELS

### A1 - Beginner 入门级

**Multiple Choice:**
- 4 选项，1 个明显错误（语法/拼写）
- 其他 3 个语法正确但语义不符
- 场景简单日常：购物、问路、问候

**Chinglish Fix:**
- 错误类型：基本语法、词序、明显直译
- 示例错误："I very like it" → "I really like it"
- 示例错误："She go to school yesterday" → "She went"

**Fill Blank:**
- 3 选 1 词库
- 直接匹配，无需理解语境

---

### A2 - Elementary 初级

**Multiple Choice:**
- 4 选项全部语法正确
- 干扰项语义差异明显
- 场景：日常生活、简单工作

**Chinglish Fix:**
- 错误类型：常见直译、介词错误
- 示例错误："I agree your opinion" → "I agree with your opinion"
- 示例错误："Discuss about this" → "Discuss this"

**Fill Blank:**
- 3 选 1 词库
- 需要简单语境理解

---

### B1 - Intermediate 中级

**Multiple Choice:**
- 4 选项全部语法正确
- 干扰项在**其他语境**下可用
- 包含 1 个常见学习者错误作为陷阱
- 场景：工作沟通、旅行、社交

**Example - B1 MC:**
Context: "You want to end a phone call politely."
Options:
A. "I'll let you go now" ← Correct
B. "I'll hang up now" ← 太直接
C. "Let's stop talking" ← 不礼貌
D. "I'm going now" ← 语境不符

**Chinglish Fix:**
- 错误类型：介词搭配、冠词、固定搭配
- 示例错误："Make a decision for" → "Make a decision about"

**Fill Blank:**
- 3-4 选 1 词库
- 需要理解表达用法

---

### B2 - Upper-Intermediate 中高级 ⚠️ 常见级别

**Multiple Choice:**
- 4 选项全部语法正确且听起来自然
- 干扰项必须是 **plausible in OTHER contexts**
- 至少 1 个"高级陷阱"：常见学习者错误
- 场景：商务会议、专业沟通

**Example - B2 MC:**
Context: "In a team meeting, you want to return to a topic later."
Options:
A. "Let's circle back on this" ← Correct
B. "Let's follow up on this" ← Plausible (different meaning - action vs discussion)
C. "We should revisit this later" ← Plausible (more formal, less idiomatic)
D. "Let's discuss this again" ← Trap (grammatically correct but not idiomatic)

**Chinglish Fix:**
- 错误类型：细微介词错误、语体不当、搭配错误
- 示例错误："We need to discuss about the project"
- 示例错误："I am interesting in this topic" (interested)

**Fill Blank:**
- 4 选 1 词库
- 需要理解细微语义差别

---

### C1 - Advanced 高级

**Multiple Choice:**
- 所有选项对非母语者都听起来自然
- 需要文化知识或习语理解
- 可包含 1-2 个英式/美式差异陷阱
- 场景：复杂商务、学术讨论

**Example - C1 MC:**
Context: "You want to politely decline a request without saying no directly."
Options:
A. "That might be challenging to fit in" ← Correct (indirect)
B. "I'm afraid I can't" ← Too direct
C. "Let me think about it" ← Implies maybe, not decline
D. "I'll have to pass on this" ← Correct but more casual

**Chinglish Fix:**
- 错误类型：文化得体性、语域错误、隐含意义
- 示例错误："Please kindly check" (过度礼貌)
- 示例错误：在非正式场合使用过于正式的表达

**Fill Blank / Dialogue Completion:**
- 4 选 1，需要文化理解
- 多个答案可能都"可以"，但只有一个"最地道"

---

### C2 - Proficiency 精通级

**Multiple Choice:**
- 所有选项都符合语法且自然
- 区别在于**细微语气差异**或**文化隐含意义**
- 场景：专业演讲、文化敏感话题

**Example - C2 MC:**
Context: "Giving feedback to a senior colleague on their presentation."
Options:
A. "I had a thought on slide 3" ← Correct (hedges, collaborative)
B. "You should change slide 3" ← Too direct
C. "Slide 3 could be better" ← Vague
D. "I think slide 3 is wrong" ← Too confrontational

**Chinglish Fix:**
- 错误类型：深层文化差异、语用失误
- 示例错误：不理解美式间接沟通文化
- 示例错误：在需要 hedge 的情况下过于直接

**Dialogue Completion:**
- 开放式，需要综合理解
- 可能没有"唯一正确答案"，而是"最符合语境"

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

## 💡 HINT DESIGN PRINCIPLES

### Core Rule: Hints guide thinking direction, NEVER reveal answers

**SAFE Hint Patterns** (通用模板，可复用):
- "💡 Think about the formality level of this situation"
- "💡 Consider who you're talking to - friend or boss?"
- "💡 What would sound natural in American English?"
- "💡 Is this formal or casual context?"
- "💡 Think about the relationship between the speakers"
- "💡 Consider the tone - professional or friendly?"
- "💡 What's appropriate for a workplace setting?"

**FORBIDDEN Hint Patterns**:
- ❌ "💡 Use a spatial metaphor" (太具体，直接指向特定答案)
- ❌ "💡 The phrase starts with 't'" (字母提示)
- ❌ "💡 Include someone = ?" (等同告诉答案)
- ❌ "💡 'A' or 'B' - which one?" (二选一)
- ❌ "💡 Think about [specific word/concept from answer]" (指向答案)
- ❌ 直接用中文翻译作为提示

**Validation Test**:
如果 hint 只适用于 ONE possible answer，则太具体。
Good hint 应该对 2-3 个选项都"听起来合理"。

**Bad Hint Example:**
- Question: "Let's ___ on this later." (Answer: circle back)
- Bad hint: "💡 Think about a shape" ← 太具体，直接指向 circle
- Good hint: "💡 What's the idiomatic way to say 'return to a topic'?"

3. **NEVER make distractors obviously wrong**
   - All 4 options should sound plausible
   - For B2+: At least one distractor should be a common learner error

## STRICT RULES
> **See [output_rules.md](output_rules.md) for complete JSON/Markdown formatting rules.**

1. All questions must relate to today's knowledge point
2. **Difficulty MUST match CEFR level** - harder for B2+ users
3. Include encouraging feedback in display fields
4. Total XP should be around 35-40
5. **Use NEW contexts** - never copy-paste from keypoint examples

## CONTEXT VARIATION RULES

### Multiple Choice - 场景类型（轮换使用）
1. **Email**: "You're writing to a client..."
2. **Meeting**: "In a team meeting..."
3. **Casual chat**: "Talking to a coworker at lunch..."
4. **Phone/Video call**: "On a call with your manager..."
5. **Presentation**: "During your presentation..."
6. **Networking**: "At a professional event..."

### Chinglish Fix - 错误类型分布（按级别）
| Level | 主导错误类型 | 占比 |
|-------|-------------|------|
| A1-A2 | 基本语法、词序、直译 | 80% |
| B1-B2 | 介词、冠词、搭配 | 60% |
| C1-C2 | 语域、文化、语用 | 50% |

### Fill Blank - 语境深度
- A1-A2: 单句，明确场景
- B1-B2: 对话语境，需理解关系
- C1-C2: 复杂语境，可能有多重解读
```

---

## Output Schema

> **CRITICAL:** Display fields must NOT reveal answers before user responds.

```json
{
  "_meta": {
    "prompt_version": "quiz_gen_v1.3"
  },
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

> See [shared_enums.md](shared_enums.md#quiz-question-types-题型) for full quiz type definitions.

**Daily Quiz:** 3 questions, ~37 XP, pass with 2/3 correct
