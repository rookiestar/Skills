# Response Templates

> Templates for various response scenarios in the eng-lang-tutor skill.

---

## 1. Already Completed Responses

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

---

## 2. Not Available Responses

```json
{
  "keypoint_not_found": {
    "display": {
      "title": "📅 No Keypoint Found",
      "message": "No knowledge point exists for {date}.",
      "hint": "Try **keypoint today** for today's content.",
      "history": "Or say **keypoint history** to see recent keypoints."
    }
  }
}
```

---

## 2.5. Quiz Request Flow (CRITICAL)

> **NEVER tell user "will generate later" - ALWAYS generate immediately when user requests quiz.**

```
When user requests quiz:
1. Check if quiz already completed today (completion_status.quiz_completed_date == today)
   → YES: Show "Already completed" message
   → NO: Continue to step 2

2. Check if keypoint.json exists for today
   → NO: IMMEDIATELY generate keypoint via LLM (do NOT say "will notify later")
          Save keypoint with generated=true
   → YES: Continue to step 3

3. Check if quiz.json exists and quiz.generated == true
   → NO: IMMEDIATELY generate quiz via LLM based on keypoint
          Save quiz with generated=true
   → YES: Load existing quiz

4. Present quiz questions to user in ONE response
```

**FORBIDDEN responses:**
- ❌ "今天还没有生成知识点，稍后会为您生成并通知您"
- ❌ "Quiz will be available later"
- ❌ "Please wait for the scheduled push"

**REQUIRED behavior:**
- ✅ Generate keypoint immediately via LLM if missing
- ✅ Generate quiz immediately via LLM
- ✅ Present quiz in the same response

---

## 3. Keypoint History Response

**When user says:** `keypoint history`, `知识点 历史`, `昨天`, `yesterday`

**Logic:**
1. Scan `~/.openclaw/state/eng-lang-tutor/daily/` directory for all `YYYY-MM-DD/keypoint.json` files
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

---

## 4. Keypoint Display Template

> IMPORTANT: Use `**text**` for bold. Never use `~~strikethrough~~`. Output Markdown text directly, NOT JSON.

**Assembly Flow:**

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

---

## 5. Stats Display Template

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

---

## 6. Config Display Template

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

---

## 7. Errors Display Template (Paginated)

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

---

## 8. Quiz Result Display Template

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

---

## 9. Output Format Rules

> CRITICAL: All responses must use platform-agnostic Markdown.

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
