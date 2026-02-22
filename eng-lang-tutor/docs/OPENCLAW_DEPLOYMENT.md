# OpenClaw 部署指南

本文档说明如何将 `eng-lang-tutor` skill 部署到 OpenClaw 服务器，并通过 Discord 等渠道使用。

## 1. 前置条件

- 一台已安装 OpenClaw 的服务器
- OpenClaw Gateway 正在运行
- 已配置好 Discord Bot（可选其他渠道）

## 2. 部署步骤

### 2.1 上传 Skill 到服务器

**方式 A：使用 SCP 上传**

```bash
# 在本地机器上执行
scp -r /path/to/eng-lang-tutor user@your-server:~/.openclaw/skills/
```

**方式 B：使用 Git Clone**

```bash
# 在服务器上执行
cd ~/.openclaw/skills/
git clone https://github.com/rookiestar/eng-lang-tutor.git
```

### 2.2 确认目录结构

确保目录结构如下：

```
~/.openclaw/skills/eng-lang-tutor/
├── SKILL.md              # 核心技能文件（必需）
├── scripts/              # Python 脚本
│   ├── state_manager.py
│   ├── scorer.py
│   ├── gamification.py
│   └── dedup.py
├── templates/            # JSON Schema
├── references/           # 参考资源
├── examples/             # 示例文件
└── (数据存储在外部目录)
    ~/.openclaw/state/eng-lang-tutor/  # 运行时数据（自动创建）
```

### 2.3 验证 Skill 加载

```bash
# 查看已加载的 skills
openclaw skills list

# 查看特定 skill 详情
openclaw skills info eng-lang-tutor
```

## 3. 配置 Discord 渠道

### 3.1 创建 Discord Bot

1. 访问 [Discord Developer Portal](https://discord.com/developers/applications)
2. 创建新应用，命名为你的 Bot
3. 进入 Bot 页面，创建 Bot 并获取 Token
4. 启用 Message Content Intent

### 3.2 配置 OpenClaw

```bash
# 设置 Discord Token
openclaw config set discord.token YOUR_BOT_TOKEN

# 设置服务器 ID（可选）
openclaw config set discord.guildId YOUR_SERVER_ID
```

### 3.3 邀请 Bot 到服务器

1. 在 Discord Developer Portal 中，进入 OAuth2 > URL Generator
2. 选择 `bot` 和 `applications.commands` scope
3. 选择所需权限（Send Messages, Read Messages 等）
4. 复制生成的邀请链接并在浏览器中打开
5. 选择要添加 Bot 的服务器

### 3.4 完成配对

首次与 Bot 对话时，会收到配对码：

```bash
# 在服务器上执行配对
openclaw pairing approve discord YOUR_PAIRING_CODE
```

## 4. 使用 Skill

### 4.1 通过 Discord 使用

在 Discord 中与 Bot 对话，触发英语学习功能：

```
# 触发今日知识点
今天有什么英语知识点？

# 触发 Quiz
给我出个 Quiz

# 查看学习进度
我的学习进度怎么样？
```

### 4.2 设置定时推送（cron）

```bash
# 编辑 crontab
crontab -e

# 添加每日定时推送（例如每天早上 9 点）
0 9 * * * openclaw agent --channel discord --message "每日英语学习时间到！今天的知识点是：" --agent eng-lang-tutor
```

## 5. 进阶配置

### 5.1 配置用户偏好

在 Discord 中与 Bot 对话设置：

```
设置我的 CEFR 等级为 B2
我的导师风格设为严谨
调整主题配比，增加职场内容的比例
```

### 5.2 配置环境变量

在服务器上设置 API 密钥（如果使用外部 LLM）：

```bash
# 编辑 OpenClaw 配置
openclaw config set model.provider anthropic
openclaw config set model.api_key YOUR_API_KEY
```

### 5.3 数据持久化

数据存储在 `~/.openclaw/state/eng-lang-tutor/` 目录，确保有正确的写入权限：

```bash
chmod -R 755 ~/.openclaw/state/eng-lang-tutor/
```

可通过环境变量 `OPENCLAW_STATE_DIR` 自定义数据目录。

## 6. 故障排查

### 6.1 Skill 未加载

```bash
# 检查 skill 目录
ls -la ~/.openclaw/skills/eng-lang-tutor/

# 检查 SKILL.md 是否存在
cat ~/.openclaw/skills/eng-lang-tutor/SKILL.md

# 重启 Gateway
openclaw gateway restart
```

### 6.2 Discord 无响应

```bash
# 检查 Gateway 日志
openclaw logs

# 验证 Discord Token
openclaw config get discord.token

# 检查 Bot 状态
openclaw doctor
```

### 6.3 Python 脚本错误

```bash
# 检查 Python 环境
python3 --version

# 安装依赖（如有需要）
pip3 install -r ~/.openclaw/skills/eng-lang-tutor/requirements.txt

# 手动测试脚本
cd ~/.openclaw/skills/eng-lang-tutor/scripts/
python3 state_manager.py --show
```

## 7. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      Discord                            │
│                    (用户交互)                            │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 OpenClaw Gateway                        │
│              (消息路由 + 会话管理)                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               eng-lang-tutor Skill                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ SKILL.md    │  │ scripts/    │  │ ~/.openclaw │    │
│  │ (技能描述)   │  │ (Python代码) │  │ (状态存储)   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    LLM Provider                         │
│              (Claude/GPT/Qwen 等)                       │
└─────────────────────────────────────────────────────────┘
```

## 8. 参考链接

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Discord 开发者门户](https://discord.com/developers/applications)
- [OpenClaw Skills 开发指南](https://docs.openclaw.ai/skills)
