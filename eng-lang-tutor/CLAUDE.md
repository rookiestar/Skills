# SKILL: eng-lang-tutor

## 1. 项目目标

本项目主要为Agent添加「地道美式英语导师」的Skill，配合Agent所在环境的cron job实现定期的知识推送与测验。

### 1.1. 学习目标

- 以提升地道的美式英语常用口语表达为主，兼顾听力与书面表达（正式场合）。
- 避免传统的Chinglish的硬翻式尴尬表达。
- 融入轻量游戏化教学，覆盖影视、新闻、游戏、体育、职场、社交、生活等用户感兴趣的场景来提升用户的粘性。

### 1.2. 语言范围

- 以美式英语为主，包含俚语、口头语、缩写（gonna, gotta, kinda 等），能帮助用户区分「正式 vs 口语」。

### 1.3. 技能维度

- 涉及词汇/短语、固定搭配、场景句型等口语与书面语中的表达方式。

## 2. 项目范围

### 2.1. MVP版本功能清单

#### 2.1.1 导师模式

Agent结合难度与偏好的设置，以及用户的历史学习进度动态生成并调整个性化的教学大纲与教学内容：

| 功能 | 描述 | 频次 | 对应脚本 |
|-----|------|-----|---------|
| **知识点** | 地道美式英语日常沟通素材，包含场景、可替换说法、Chinglish陷阱+修正 | 每天 | state_manager.py |
| **Quiz** | 3道轻量测验：1多选+1Chinglish修正+1随机（填空/对话）| 每天 | scorer.py |
| **错题本** | 记录错误答案，支持手动添加，便于针对性复习 | 实时 | state_manager.py |

**Quiz 结构：**

| 题型 | 描述 | XP值 | 每日Quiz |
|-----|------|-----|---------|
| multiple_choice | 四选一，测试表达识别 | 10 | 1 (必选) |
| chinglish_fix | 识别并修正Chinglish表达 | 15 | 1 (必选) |
| fill_blank | 填空，完成对话 | 12 | 0-1 (随机) |
| dialogue_completion | 选择合适的对话回应 | 15 | 0-1 (随机) |

- **每日Quiz**: 3题，约37 XP，答对2题即过关

#### 2.1.2 状态管理

保障整个教学过程可备份、可追溯、可回滚：

| 组件 | 文件 | 用途 |
|-----|------|-----|
| 核心状态 | state.json | streak/xp/偏好/近期主题/错题本 |
| 事件日志 | logs/events_YYYY-MM.jsonl | 追加式事件流水账 |
| 每日内容 | daily/YYYY-MM-DD/*.json | 知识点/Quiz/用户答案 |

#### 2.1.3 成就体系（Duolingo风格）

**双等级体系说明：**
- **能力等级 (CEFR)**：A1-C2，决定内容难度，与 App 无关的绝对语言能力
- **活跃等级 (Level)**：1-20，衡量 App 使用深度，通过 XP 累积升级

| 活跃等级 | 阶段 | XP 需求 |
|---------|------|---------|
| 1-5 | 启程者 (Starter) | 0-350 |
| 6-10 | 行路人 (Traveler) | 550-2000 |
| 11-15 | 探索者 (Explorer) | 2600-6000 |
| 16-20 | 开拓者 (Pioneer) | 7200-15000 |

| 组件 | 描述 |
|-----|------|
| **XP & 等级** | 1-20级，XP累积升级（启程者 → 行路人 → 探索者 → 开拓者） |
| **连胜系统** | 连续学习天数，支持连胜冻结（50宝石） |
| **徽章系统** | First Steps、Week Warrior、Month Master、Perfect 10、Vocab Hunter、Error Slayer |
| **宝石系统** | 用于购买连胜冻结、提示等 |

**徽章详情：**

| 徽章 | 触发条件 | 宝石奖励 |
|-----|---------|---------|
| First Steps | 完成首次Quiz | 10 |
| Week Warrior | 7天连胜 | 25 |
| Month Master | 30天连胜 | 100 |
| Perfect 10 | 10次完美Quiz | 50 |
| Vocab Hunter | 学习100个表达 | 75 |
| Error Slayer | 清除30个错题 | 30 |

#### 2.1.4 系统配置

| 配置项 | 描述 | 默认值 |
|-------|------|-------|
| CEFR等级 | A1-C2语言级别 | B1 |
| 口语/书面比例 | 口语表达占比 | 70% |
| 主题配比 | movies/news/gaming/sports/workplace/social/daily_life | 各主题权重 |
| 导师风格 | humorous/rigorous/casual/professional | humorous |
| 去重天数 | 避免重复内容的时间窗口 | 14天 |

**配置常量：** 集中定义于 `scripts/core/constants.py`（宝石消耗、XP值、超时阈值等）

### 2.2. MVP版本不做 / 延后

- **周周练**：5道综合性场景练习，覆盖本周知识点，约62 XP，答对3题即过关。计划周日推送。
- **语音模式**：支持tts便于用户跟读，支持asr便于导师对口语表达进行打分。

### 2.3. 项目约束

**核心原则：别问"怎么翻译"，先问"这个场景美国人会怎么说"，会让你立刻更像美国人。**

#### 2.3.1 输出格式约束

- **必须输出合法 JSON**（不要 markdown，不要代码块，不要多余文本）
- 所有输出必须符合 `templates/` 目录下的 JSON Schema

#### 2.3.2 内容质量约束

- 语言风格：**地道美式**、轻松、可用、短句为主
- 每条知识点必须包含：**场景、可替换说法、Chinglish 陷阱 + 修正**
- 包含发音提示（gonna, gotta, wanna 等自然发音）
- 提供文化背景和使用场景说明

#### 2.3.3 去重策略（14天窗口）

使用 `scripts/utils/dedup.py` 实现三层去重：

| 层级 | 方法 | 描述 |
|-----|------|-----|
| 1 | topic_fingerprint | 主题指纹匹配 |
| 2 | 表达重叠 | 相同短语超过50%视为重复 |
| 3 | 词根匹配 | 核心词汇结构相似 |

#### 2.3.4 反直译原则

- 优先给"美国人会怎么说"，而不是"中文怎么翻英文"
- 参考 `references/resources.md` 中的主题资源库
- 使用 `references/prompt_templates.md` 中的LLM提示模板

## 3. 技术栈与SKILL结构

### 3.1. 技术栈与输出格式

- 技术栈：Python 3.x
- 触发方式：cron 触发 Agent 调用 Skill

### 3.2. 目录结构

```
eng-lang-tutor/
├── SKILL.md                    # 核心技能文档
├── CLAUDE.md                   # 项目说明（本文件）
├── scripts/
│   ├── __init__.py             # 包入口，重导出核心类
│   ├── core/
│   │   ├── state_manager.py    # 状态持久化与事件日志
│   │   ├── error_notebook.py   # 错题本管理
│   │   ├── scorer.py           # 答案评估与XP计算
│   │   ├── gamification.py     # 连胜/等级/徽章
│   │   └── constants.py        # 共享常量和工具函数
│   ├── cli/
│   │   ├── cli.py              # CLI入口点
│   │   └── command_parser.py   # 命令解析
│   ├── audio/
│   │   ├── tts/                # TTS引擎（Coqui/Azure/Edge）
│   │   ├── composer.py         # 音频合成
│   │   ├── converter.py        # 格式转换
│   │   ├── feishu_voice.py     # 飞书语音发送
│   │   └── utils.py            # 音频工具函数
│   ├── scheduling/
│   │   └── cron_push.py        # 定时推送
│   └── utils/
│       ├── dedup.py            # 14天去重逻辑
│       └── helpers.py          # 通用工具函数
├── templates/
│   ├── state_schema.json       # 状态 JSON Schema
│   ├── keypoint_schema.json    # 知识点 JSON Schema
│   └── quiz_schema.json        # Quiz JSON Schema
├── references/
│   ├── resources.md            # 主题化英语学习资源库
│   └── prompt_templates.md     # LLM Prompt 模板
├── examples/                   # 示例文件（按 CEFR 级别命名）
│   ├── sample_keypoint_*.json  # 知识点示例 (a1-c2)
│   └── sample_quiz_*.json      # Quiz示例 (a1-c2)
└── (数据存储在外部目录)
    ~/.openclaw/state/eng-lang-tutor/   # 实际数据存储位置
    ├── state.json              # 运行时状态
    ├── logs/
    │   └── events_YYYY-MM.jsonl
    └── daily/
        └── YYYY-MM-DD/
            ├── keypoint.json
            ├── quiz.json
            └── user_answers.json

    注: 可通过 OPENCLAW_STATE_DIR 环境变量自定义存储位置
```

## 4. 功能切片实现

### 4.1 功能切片与脚本对应

| 切片 | 对应脚本 | 输入 | 输出 |
|-----|---------|------|-----|
| 状态加载/保存 | core/state_manager.py | - | state.json |
| 事件日志 | core/state_manager.py | event_type, data | events_YYYY-MM.jsonl |
| 每日内容保存 | core/state_manager.py | content_type, content | daily/YYYY-MM-DD/*.json |
| 答案评估 | core/scorer.py | quiz.json + user_answers | results + updated state |
| XP计算 | core/scorer.py | correct_count, streak | XP with multiplier |
| 连胜更新 | core/gamification.py | study_date | new_streak |
| 等级更新 | core/gamification.py | XP | level |
| 徽章检查 | core/gamification.py | progress | new_badges |
| 去重检查 | utils/dedup.py | new_content, recent_content | is_duplicate |
| 异步音频生成 | core/state_manager.py | keypoint.json | audio/*.mp3 |

### 4.2 核心工作流

#### 4.2.1 每日知识点生成

```
1. state_manager.load_state()
2. dedup.get_excluded_topics(state)
3. LLM生成知识点（使用prompt_templates.md）
4. dedup.check_duplicate(new_content, recent_content)
5. 验证JSON Schema
6. state_manager.save_daily_content('keypoint', content)
7. state_manager.append_event('keypoint_generated', {...})
```

#### 4.2.2 Quiz评估流程

```
1. state_manager.load_daily_content('quiz')
2. 读取 user_answers.json
3. scorer.evaluate_quiz(quiz, answers, state)
4. gamification.update_streak(state, today)
5. gamification.update_level(state)
6. gamification.check_badges(state)
7. state_manager.save_state(state)
8. state_manager.append_event('quiz_completed', results)
```

## 5. 开发准则

### 5.1 Skill文档规范

- SKILL.md文档要详细但不能过长，聚焦核心步骤，细节可以放在代码示例里。建议**800-1500 tokens**。
- Skills 必须包含可执行的步骤、代码示例、验证检查点。
- 设计 Skills 时考虑复用性（模块化）。一个 Skill 解决一类问题，不是一次性的硬编码。

### 5.2 确定性验证器

每个任务都有**确定性验证器**（deterministic verifier）：这不是用 LLM 评判，而是程序化断言。

| 验证项 | 验证方法 | 对应工具 |
|-------|---------|---------|
| JSON格式 | json.loads() | Python标准库 |
| JSON Schema | schema validation | templates/*.json |
| XP计算 | 公式验证 | scorer.py |
| 连胜更新 | 日期比较 | gamification.py |
| 去重检查 | 指纹/表达匹配 | dedup.py |

### 5.3 聚焦核心路径

不要过度工程化：比如应该聚焦 80% 场景的核心路径，而非覆盖尽可能多的edge cases。

### 5.4 可复用资源

| 资源 | 位置 | 用途 |
|-----|------|-----|
| skill-creator | github.com/anthropics/skills | 自动生成skill骨架 |
| awesome-language-learning | github.com/Vuizur/awesome-language-learning | 语言学习工具集合 |
| 主题资源库 | references/resources.md | 美剧/新闻/游戏/体育/职场/生活 |
| LLM提示模板 | references/prompt_templates.md | 知识点/Quiz生成模板 |

### 5.5 行动准则

- 未经允许不得擅自执行git commit、push和publish等相关动作
- 针对耗费较长时间做debug或者反复掉坑的情况，需要及时总结复盘，并将经验精炼到本文档中

## 6. 三层版本管理与发布流程

### 6.1 架构概述

本项目采用三层文件管理策略，分别控制本地开发、远程仓库和 npm 包的文件可见性：

```
┌─────────────────────────────────────────────────────────┐
│  本地仓库 (main 分支) - 最全                              │
│  - 所有开发文件：tests/, package.json, bin/, CLAUDE.md等  │
│  - 通过 .gitignore 管理追踪                               │
│  - 文件数：~75                                            │
└─────────────────────────────────────────────────────────┘
                          │
                          │ (选择性同步)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  远程仓库 (public 分支) - 公开                            │
│  - 用户可见的源代码                                        │
│  - 排除：tests/, bin/, package.json, CLAUDE.md 等        │
│  - 文件数：~57                                            │
└─────────────────────────────────────────────────────────┘
                          │
                          │ (npm publish)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  npm 包 (@rookiestar/eng-lang-tutor) - 最精简            │
│  - 用户运行所需的最小文件集                                │
│  - 通过 package.json "files" 字段控制                     │
│  - 文件数：~50                                            │
└─────────────────────────────────────────────────────────┘
```

### 6.2 配置文件

| 文件 | 作用 | 管理层级 |
|------|------|----------|
| `.gitignore` | 控制本地 git 追踪 | 本地仓库 |
| `.gitattributes` | 控制 `git archive` 导出 | 远程导出 |
| `package.json` `files` 字段 | 控制 npm 包内容 | npm 包 |

### 6.3 分支管理

| 分支 | 用途 | 文件范围 | 远程状态 |
|------|------|----------|----------|
| `main` | 本地开发 | 全部文件 | 推送但不作为默认 |
| `public` | 远程公开 | 公开文件 | **默认分支** |

### 6.4 各层包含的文件

**本地仓库 (main) 独有：**
- `tests/` - 单元测试
- `bin/` - npm CLI 入口
- `package.json` - npm 包配置
- `CLAUDE.md` - 本开发文档
- `CHANGELOG.md` - 变更日志
- `.gitignore` / `.gitattributes` - Git 配置

**远程仓库 (public) 包含：**
- `scripts/` - 核心代码
- `templates/` - LLM 模板
- `examples/` - 示例文件
- `references/` - 参考资源
- `docs/` - 部署文档
- `SKILL.md`, `README.md`, `requirements.txt`

**npm 包包含：**
- `scripts/`, `templates/`, `examples/`, `references/`
- `SKILL.md`, `README.md`, `requirements.txt`

### 6.5 发布流程

#### 6.5.1 日常开发（main 分支）

```bash
# 在 main 分支开发
git checkout main

# 开发完成后提交
git add .
git commit -m "feat: new feature"
git push origin main
```

#### 6.5.2 同步到 public 分支

```bash
# 切换到 public 分支
git checkout public

# 从 main 同步公开文件
git checkout main -- eng-lang-tutor/scripts/ eng-lang-tutor/templates/ eng-lang-tutor/examples/ eng-lang-tutor/references/ eng-lang-tutor/docs/ eng-lang-tutor/SKILL.md eng-lang-tutor/README.md eng-lang-tutor/requirements.txt

# 提交并推送
git commit -m "sync: update from main"
git push origin public

# 切回 main 继续开发
git checkout main
```

#### 6.5.3 发布 npm 包

```bash
# 确保在 eng-lang-tutor 目录
cd eng-lang-tutor

# 更新版本号
# 编辑 package.json 中的 version 字段

# 更新 CHANGELOG.md

# 提交版本变更
git add package.json CHANGELOG.md
git commit -m "chore: bump version to x.x.x"
git push origin main

# 发布到 npm（需要 OTP）
npm publish --otp=<your-otp-code>
```

### 6.6 辅助脚本

使用 `scripts/release.py` 查看文件分布：

```bash
# 查看三层文件分布
python3 scripts/release.py --check

# 输出示例：
# Local=75 | Remote=57 | npm=50
```

### 6.7 最佳实践

1. **开发时**：始终在 `main` 分支工作，包含完整测试
2. **发布前**：运行 `pytest` 确保测试通过
3. **同步时**：只同步必要的公开文件到 `public` 分支
4. **npm 发布**：使用 `files` 白名单而非黑名单，避免意外包含敏感文件
5. **版本号**：遵循语义化版本 (semver)：MAJOR.MINOR.PATCH
6. **CHANGELOG**：每次发布前更新变更日志
