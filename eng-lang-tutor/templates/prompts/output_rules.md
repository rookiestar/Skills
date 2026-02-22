# 输出规则

> 本文件定义所有 LLM 输出的通用规则。生成内容时必须遵守这些规则。

---

## JSON 输出要求

### 基本规则
- ⛔ **只输出合法 JSON** - 无 markdown 代码块，无 ```json 标记
- ⛔ **无多余文本** - 不要在 JSON 前后添加说明文字
- ⛔ **无注释** - JSON 中不允许 `//` 或 `/* */` 注释
- ✅ **必须通过 Schema 验证** - 符合 `templates/` 目录下的 JSON Schema

### JSON 转义规则 (用于 bash 命令)
```bash
# 单引号包裹
python3 scripts/state_manager.py save_daily --content-type keypoint --content '{"key": "value"}'

# 转义内部单引号: ' → '\''
python3 scripts/state_manager.py save_daily --content-type keypoint --content '{"title": "It'\''s a test"}'
```

---

## Markdown 格式规则

### 平台兼容性

| 格式 | 语法 | 飞书 | Discord | Telegram | Slack |
|------|------|------|---------|----------|-------|
| 粗体 | `**text**` | ✅ | ✅ | ✅ | ✅ |
| 斜体 | `*text*` | ✅ | ✅ | ✅ | ✅ |
| 链接 | `[text](url)` | ✅ | ✅ | ✅ | ✅ |
| 代码 | `` `code` `` | ✅ | ✅ | ✅ | ✅ |
| 删除线 | `~~text~~` | ❌ | ✅ | ✅ | ✅ |

### 飞书兼容性特别说明
- **删除线**: 飞书不支持 `~~text~~` 语法
- **替代方案**: 直接使用「错误：xxx」而非删除线

---

## 标点符号规则

| 规则 | 正确示例 | 错误示例 |
|------|----------|----------|
| 陈述句以句号结尾 | `This is correct.` | `This is correct` |
| 问句以问号结尾 | `How are you?` | `How are you` |
| 避免连续标点 | `Great!` | `Great!!!` |
| 中英文标点不混用 | `Hello, 你好。` | `Hello，你好.` |

---

## 双语标签格式

### 标准格式
```
中文 | English
```

### 示例
```
选择题 | Multiple Choice
填空题 | Fill in the Blank
Chinglish 修正 | Fix the Chinglish
```

---

## Display 对象通用字段

所有 `display` 对象应包含以下通用格式字段：

| 字段 | 描述 | 示例 |
|------|------|------|
| `type_emoji` | 类型图标 | `🔤` |
| `type_name` | 类型名称（双语） | `选择题 \| Multiple Choice` |
| `hint` | 提示（不泄露答案） | `💡 考虑上下文...` |
| `correct_feedback` | 正确反馈 | `✅ 正确！` |
| `wrong_feedback` | 错误反馈 | `❌ 再想想...` |
| `xp_display` | XP 显示 | `💎 +10 XP` |

---

## Emoji 使用规则

### 通用原则
- ✅ 使用表情符号增加视觉效果
- ✅ 每个主要部分使用 emoji 作为视觉分隔
- ⛔ 不要过度使用，保持简洁
- ⛔ 不要在 JSON 字段名中使用 emoji

### 常用 Emoji 参考
- 📝 文档/测验
- 💬 对话/聊天
- 💎 XP/奖励
- ✅ 正确/完成
- ❌ 错误
- 💡 提示
- 🎯 目标/要点
- 📅 日期
- 🏆 成就/徽章
- ⛔ 禁止/警告

详细 Emoji 映射请参考 [display_guide.md](display_guide.md)。
