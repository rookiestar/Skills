# Response Templates

> Templates for various response scenarios in the eng-lang-tutor skill.

**Related Files:**
- [shared_enums.md](shared_enums.md) - Level names, badges, quiz types
- [output_rules.md](output_rules.md) - JSON output rules, markdown formatting
- [display_guide.md](display_guide.md) - Emoji and formatting guidelines

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

> See [shared_enums.md](shared_enums.md#activity-levels-活跃等级) for level names.

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

### Error Review Session Flow

When user starts `errors review`:

**1. Load Errors**
- Fetch unreviewed errors from `error_notebook` (max 5 at a time)
- Skip already reviewed errors (`reviewed: true`)

**2. Present Question**
```markdown
🔄 **Error Review** ({current}/{total})

❌ 原题: {question}
📝 你的答案: {user_answer}
✅ 正确答案: **{correct_answer}**

💡 {explanation}

───────────────────
回答回忆: 你选择了 **{user_answer}**
现在你还记得为什么吗？输入 **记得** 或 **忘了**
```

**3. User Response**
- If "记得" / "remember": Mark as reviewed, +5 XP
- If "忘了" / "forgot": Keep in notebook, show explanation again

**4. State Update**
- Update `error_notebook[].reviewed` to `true` for remembered items
- Increment `reviewed_count` for badge tracking
- Log event: `error_reviewed`

**5. Completion**
```markdown
🎉 **Review Complete!**

📊 本次复习: **{reviewed}** 题
💎 获得: **+{xp} XP**

{if all reviewed:}
✨ 恭喜！错题本已清空！获得徽章: **Error Slayer** (清除30个错题)
{else:}
📓 还剩 **{remaining}** 条错题待复习

───────────────────
💪 继续加油！输入 **errors review** 再来一轮
```

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

> See [output_rules.md](output_rules.md) for complete formatting rules.

**Quick Reference:**
- **Bold syntax**: Use `**text**` for bold
- **Never use** `~~strikethrough~~` - use ❌ emoji instead
- **Emojis**: Include at the start of each section
- **Punctuation**: End sentences properly (`.` or `?` or `!`)
