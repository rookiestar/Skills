# eng-lang-tutor

**地道美式英语导师** - 一个用于学习地道美式英语表达的 OpenClaw Skill。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能特性

- 📚 **每日知识点** - 地道美式表达，包含场景语境、可替换说法和中式英语陷阱
- 🔊 **语音版知识点** - 支持 TTS 语音合成，可收听发音学习
- 📝 **测验系统** - 4种题型：选择题、填空题、对话补全、中式英语修正
- 🎮 **多邻国风格游戏化** - XP经验值、等级、连胜、徽章、宝石
- ⏰ **可自定义推送时间** - 通过 cron 设置您偏好的推送时间
- 🌐 **双语支持** - 命令同时支持中英文

## 快速开始

### 前置条件

- 服务器上已安装 OpenClaw Gateway
- Python 3.8+
- ffmpeg（用于音频合成，可选）
- Discord Bot（或其他 IM 通道）

### 安装步骤

**方式一：npm 安装（推荐）**

```bash
npm install -g @rookiestar/eng-lang-tutor
```

安装会自动执行，skill 将被安装到 `~/.openclaw/skills/eng-lang-tutor/`。

**方式二：从源码安装**

```bash
cd ~/.openclaw/skills/
git clone https://github.com/rookiestar/eng-lang-tutor.git
pip install -r eng-lang-tutor/requirements.txt
```

**验证安装：**

```bash
openclaw skills list
openclaw skills info eng-lang-tutor
```

**重启 Gateway：**

```bash
openclaw gateway restart
```

**配置渠道：**

**Discord 配置：**
```bash
openclaw config set discord.token YOUR_BOT_TOKEN
openclaw config set discord.guildId YOUR_SERVER_ID
```

4. **完成配对：**

首次向 Bot 发送消息时，您会收到一个配对码。批准它：

```bash
openclaw pairing approve discord YOUR_PAIRING_CODE
```

### 首次使用

首次与 Bot 交互时，它会引导您完成 6 步引导流程：

1. 选择您的 CEFR 等级（A1-C2）
2. 选择您的兴趣主题
3. 选择导师风格（幽默/严谨/随意/专业）
4. 设置口语/书面语比例
5. 配置推送时间（知识点和测验时间）
6. 确认您的设置并创建定时任务

## 命令列表

| 命令 | 别名 | 描述 |
|---------|---------|-------------|
| `start` | `开始`, `初始化` | 启动引导配置 |
| `keypoint` | `知识点`, `today` | 查看今日知识点 |
| `keypoint history` | `知识点 历史` | 查看历史知识点 |
| `quiz` | `测验`, `test` | 参加每日测验 |
| `stats` | `进度`, `level` | 查看学习进度 |
| `config` | `设置` | 查看设置 |
| `errors` | `错题本` | 查看错题本 |
| `help` | `帮助` | 显示命令列表 |

## 推送时间配置

### Crontab 设置

Skill 的定时推送依赖 crontab。在 onboarding 流程的 Step 6 会自动创建 cron 任务。

如需手动配置或修改：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（示例：北京时间 06:45 推送知识点，22:45 推送测验）
CRON_TZ=Asia/Shanghai

# 知识点推送
45 6 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's keypoint." --mode now

# 测验推送
45 22 * * * openclaw system event --text "Use eng-lang-tutor skill. Push today's quiz invitation." --mode now
```

### 修改推送时间

如需修改推送时间：

1. **在 IM 中向 Bot 发送命令**更新偏好设置：

```
set schedule keypoint 7:00    # 设置知识点推送时间为早上 7:00
set schedule quiz 21:00       # 设置测验推送时间为晚上 21:00
```

2. **同步更新 crontab**（修改对应的时间）：

```bash
crontab -e
# 将 45 6 改为 0 7，将 45 22 改为 0 21
```

**注意：** 测验时间必须晚于知识点时间。时间格式为 24 小时制（HH:MM）。

## 游戏化系统

### XP 与等级

本系统包含两个独立的等级体系：
- **能力等级 (CEFR)**：A1-C2，决定内容难度（语言能力水平）
- **活跃等级 (Level)**：1-20，衡量使用深度（使用进程）

| 等级范围 | 所需 XP | 阶段 |
|-------------|-------------|-------|
| 1-5 | 0-350 | 启程者 (Starter) |
| 6-10 | 550-2000 | 行路人 (Traveler) |
| 11-15 | 2600-6000 | 探索者 (Explorer) |
| 16-20 | 7200-15000 | 开拓者 (Pioneer) |

### 徽章

| 徽章 | 获取条件 | 宝石奖励 |
|-------|-------------|------|
| First Steps | 完成首次测验 | 10 |
| Week Warrior | 7天连胜 | 25 |
| Month Master | 30天连胜 | 100 |
| Perfect 10 | 10次满分测验 | 50 |
| Vocab Hunter | 学习100个表达 | 75 |
| Error Slayer | 清除30个错题 | 30 |

## 项目结构

```
eng-lang-tutor/
├── SKILL.md                    # Skill 文档
├── scripts/
│   ├── state_manager.py        # 状态持久化与事件日志
│   ├── scorer.py               # 答案评估与 XP 计算
│   ├── gamification.py         # 连胜/等级/徽章逻辑
│   ├── dedup.py                # 14天去重逻辑
│   ├── command_parser.py       # 用户命令解析
│   ├── cron_push.py            # 定时内容推送
│   ├── constants.py            # 共享常量（等级阈值）
│   ├── utils.py                # 工具函数（安全除法、深度合并）
│   ├── cli.py                  # CLI 入口点
│   └── tts/                    # TTS 语音合成模块
├── templates/
│   ├── state_schema.json       # 状态 JSON Schema
│   ├── keypoint_schema.json    # 知识点 JSON Schema
│   ├── quiz_schema.json        # 测验 JSON Schema
│   ├── prompt_templates.md     # LLM Prompt 模板索引
│   └── prompts/                # 拆分的 Prompt 模板
│       ├── keypoint_generation.md
│       ├── quiz_generation.md
│       ├── display_guide.md
│       ├── initialization.md
│       └── responses.md
├── references/
│   └── resources.md            # 主题化学习资源
├── examples/
│   ├── sample_keypoint.json    # 知识点示例
│   └── sample_quiz.json        # 测验示例
└── docs/
    └── OPENCLAW_DEPLOYMENT.md  # 部署文档
```

**数据存储位置：** `~/.openclaw/state/eng-lang-tutor/`

可通过环境变量 `OPENCLAW_STATE_DIR` 自定义数据目录。

## 文档

- [SKILL.md](SKILL.md) - 完整 Skill 文档
- [OpenClaw 部署指南](docs/OPENCLAW_DEPLOYMENT.md) - 服务器部署

## 开发

### 本地调试

```bash
python3 scripts/command_parser.py --demo
python3 scripts/cron_push.py --task status
```

## 服务器迁移

**迁移学习数据：**

```bash
# 在源服务器上打包数据
tar -czvf eng-lang-tutor-data.tar.gz -C ~/.openclaw/state eng-lang-tutor

# 传输到新服务器
scp eng-lang-tutor-data.tar.gz user@new-server:~/

# 在目标服务器上解压
mkdir -p ~/.openclaw/state
tar -xzvf ~/eng-lang-tutor-data.tar.gz -C ~/.openclaw/state
```

**重新安装 skill：**

```bash
npm install -g @rookiestar/eng-lang-tutor
```

详细迁移指南请参见 [docs/OPENCLAW_DEPLOYMENT.md](docs/OPENCLAW_DEPLOYMENT.md)。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)。

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 致谢

- [awesome-language-learning](https://github.com/Vuizur/awesome-language-learning) - 资源灵感来源
- [Duolingo](https://www.duolingo.com) - 游戏化模型参考
