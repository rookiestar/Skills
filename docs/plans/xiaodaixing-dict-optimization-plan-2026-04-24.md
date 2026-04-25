# 小呆星英语查词性能优化方案

> **日期**: 2026-04-24
> **状态**: 📋 方案待评审
> **目标**: 将单次查词耗时从 ~46s 降至 <3s（15x 提速）

---

## 1. 问题诊断

### 1.1 当前耗时拆解（以 "architecture" 为例实测）

| 步骤 | 动作 | 耗时 | 累计 |
|---|---|---|---|
| 1 | `read` SKILL.md | ~2s | 2s |
| 2 | `read` english_rules.md 模板 | ~2s | 4s |
| 3 | `web_fetch` Cambridge（english-chinese-simplified） | ~4s | 8s |
| 4 | `web_fetch` Cambridge（learner-english）— 第1次结果不完整，重试 | ~4s | 12s |
| 5 | `web_fetch` Cambridge（english）— 还是不满意，再试 | ~5s | 17s |
| 6 | `edit` MEMORY.md + 组装最终回复 | ~8s + API等待 | **~46s** |

**总计：6 轮 tool call + 6 次 API 调用 ≈ 46s**

### 1.2 根因分析

| 根因 | 说明 | 影响 |
|---|---|---|
| **模板未内联** | SKILL.md 和 english_rules.md 每次都要 agent 主动 `read`，浪费 2 轮 | +4s |
| **web_fetch 反复重试** | Cambridge 页面可访问（HTTP 200），但 Readability 提取器丢失关键字段（词性、音标因 JS 渲染缺失），agent 不死心反复换 URL 重试 | +12s |
| **无重试上限** | SKILL.md 未限制 fetch 次数，agent 自由发挥抓了 3 次 | +8s |
| **无本地缓存** | "architecture" 这种高频词每次都走在线查询，完全没必要 | 全部时间 |

### 1.3 Cambridge web_fetch 失败细节

测试了 agent 尝试的 3 个 URL：
```
✅ HTTP 200, 288KB, 0.25s — dictionary.cambridge.org/.../english-chinese-simplified/architecture
✅ HTTP 200, 279KB, 0.22s — dictionary.cambridge.org/.../learner-english/architecture
✅ HTTP 200, 340KB, 0.26s — dictionary.cambridge.org/.../english/architecture
```

页面完全可达。但 Readability 提取结果：
- ✅ 例句列表（Examples of architecture）
- ✅ 多语言翻译片段
- ❌ **词性缺失**（被埋在非标准 HTML 结构中）
- ❌ **音标缺失**（页面用 Web Audio API / JS 播放器渲染，HTML 中无文本 IPA）
- ❌ **核心释义结构混乱**（中英释义混在"Translation"区块而非主定义区）

结论：**Cambridge 网页不适合作为程序化数据源**——它是给人看的，不是给机器读的。

---

## 2. 优化方案

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────┐
│                   新流程（优化后）                     │
│                                                      │
│  用户输入 "architecture"                              │
│       │                                              │
│       ▼                                              │
│  ┌─────────────────┐                                │
│  │ Step 0: 内联模板 │ ← SKILL.md 已包含完整规则      │
│  │ （零 tool call） │   无需 read references/        │
│  └────────┬────────┘                                │
│           │                                          │
│           ▼                                          │
│  ┌──────────────────────┐                           │
│  │ Step 1: 本地词典查询  │ ← exec: dict_lookup.py    │
│  │ SQLite / JSON       │   耗时 <10ms               │
│  └────────┬───────────┘                            │
│           │ 结构化 JSON 输出:                         │
│           │ { word, pos, phonetic,                  │
│           │   definitions[], example }              │
│           ▼                                          │
│  ┌──────────────────────┐                           │
│  │ Step 2: 格式化输出    │ ← 1 次 API 调用            │
│  │ 按 english_rules     │   模型拿到 JSON →          │
│  │ 模板组装最终回复      │   填入模板字段             │
│  └──────────────────────┘                            │
│                                                      │
│  总计: 1 次 exec + 1 次 API = **~2-3s**              │
└─────────────────────────────────────────────────────┘
```

### 2.2 Phase 1：SKILL.md 模板内联（快速见效）

**目标**: 消除 2 次不必要的 `read` tool call。

**动作**: 将 `references/english_rules.md` 的核心内容合并进 SKILL.md。

**具体变更**:

1. **SKILL.md 英语模块章节扩展** — 加入完整的 Lookup Output 模板定义（英→中 / 中→英 两套）、Follow-Up 规则、边界规则
2. **保留 references/ 目录** 作为"完整参考文档"，但不再要求 agent 在每次查词时主动读取
3. **新增指令**: "不要在查词过程中 read 任何文件。所有需要的规则和模板已在本文件（SKILL.md）中完整提供。"

**预期收益**: -4s（省掉 2 次 read + 对应的 API 往返）

**风险**: 无。纯文档重组，不改代码。

### 2.3 Phase 2：本地词典数据库（核心提速）

#### 2.3.1 数据源选型：ECDICT

| 维度 | ECDICT | Cambridge 官方 API | 自建爬虫 |
|---|---|---|---|
| 词条量 | ~400万 | 取决于 API | 需要自己爬 |
| 格式 | SQLite / JSON / Stardict | JSON（如有） | 自定义 |
| 音标 | ✅ 英美双音标 | ✅ | ✅ 需要解析 |
| 中文释义 | ✅ | ✅ | ✅ |
| 例句 | ✅ 有（非 Cambridge 来源） | ✅ | ✅ 可控 |
| 词频分级 | ✅ 有 | ❌ | 需自建 |
| 离线可用 | ✅ | ❌ | ✅ |
| 许可证 | CC-BY-SA / MIT（可商用） | 待确认 | 自有 |
| 维护成本 | 低（社区维护） | 取决于官方 | 高 |

**选择 ECDICT**：覆盖广、格式友好、离线、免费。

GitHub: https://github.com/skywind3000/ECDICT

#### 2.3.2 数据库设计

```sql
CREATE TABLE IF NOT EXISTS dictionary (
    word TEXT PRIMARY KEY,         -- 单词（小写）
    pos TEXT,                      -- 词性: n./v./adj./adv./...
    phonetic_uk TEXT,              -- 英式音标
    phonetic_us TEXT,              -- 美式音标
    definitions TEXT,              -- JSON array: ["建筑学；建筑术", "建筑风格"]
    example TEXT,                  -- 例句（优先 Cambridge 来源，回退 ECDICT）
    source TEXT DEFAULT 'ecdict',  -- 数据来源: ecdict / cambridge / model
    frequency INTEGER,             -- 词频等级（若有）
    updated_at TEXT                -- 最后更新时间
);

-- 查询索引
CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word);
```

#### 2.3.3 查询脚本：`scripts/dict_lookup.py`

```python
# 用法: python3 scripts/dict_lookup.py <word>
# 输出: JSON to stdout
# 退出码: 0=找到, 404=未找到

import sqlite3, json, sys

DB_PATH = "/home/rookiestar/.openclaw/workspace/agent-xiaodaixing/data/dictionary.db"

def lookup(word):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM dictionary WHERE word = ?", (word.lower(),)
    ).fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = {
        "word": row["word"],
        "pos": row["pos"],
        "phonetic": row["phonetic_us"] or row["phonetic_uk"],
        "definitions": json.loads(row["definitions"]),
        "example": row["example"],
        "source": row["source"]
    }
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dict_lookup.py <word>", file=sys.stderr)
        sys.exit(1)
    
    result = lookup(sys.argv[1])
    if result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    else:
        print(json.dumps({"error": "not_found", "word": sys.argv[1]}), file=sys.stderr)
        sys.exit(404)
```

**输出示例**:
```json
{
  "word": "architecture",
  "pos": "n.",
  "phonetic": "/ˈɑːrkɪtektʃər/",
  "definitions": ["建筑学；建筑术", "建筑风格；建筑设计"],
  "example": "Almost every visitor to Edinburgh is seduced by its splendid architecture.",
  "source": "ecdict"
}
```

#### 2.3.4 SKILL.md 流程改造

新增查词流程（替换原有的 web_fetch 流程）：

```
## Lookup Workflow（v2 - 本地词典模式）

1. 收到英语查词请求后，执行以下操作且仅执行以下操作：
   a. 运行 exec: python3 scripts/dict_lookup.py <word>
   b. 根据返回的 JSON，按下方模板格式化输出最终回复
   c. 不要执行任何其他 tool call（不要 read 文件、不要 web_fetch、不要 edit 记忆）

2. 如果 dict_lookup.py 返回 not_found：
   a. 回复："这个词我还没收录，稍后帮你加上 📚"（不要尝试用其他方式查找）
   b. 同时将未收录的词记录到 data/missing_words.log（一行一个词）

3. 严格禁止：
   - 使用 web_fetch 查询在线词典
   - 使用模型内置知识编造释义或例句
   - 多次调用 dict_lookup.py（只调一次）
   - 在查词过程中读取任何文件
```

#### 2.3.5 数据初始化与补充策略

**Step 1 — 导入 ECDICT 基础数据**（一次性）:
```bash
# 下载 ECDICT SQLite 版本
wget https://github.com/skywind3000/ECDICT/releases/download/.../ecdict.sqlite3.gz
gunzip ecdict.sqlite3.gz
# 写转换脚本导入到我们的 schema
python3 scripts/import_ecdict.py
```

**Step 2 — Cambridge 高频词例句补充**（一次性，可选但推荐）:
- 从 Cambridge 批量抓取 Top 3500 中学词汇的例句
- 用脚本解析后更新 dictionary.db 的 example 字段
- 标记 source='cambridge'

**Step 3 — 未命中词持续补充**（运营机制）:
- `data/missing_words.log` 积累用户实际查询但未收录的词
- 定期批量查询并入库
- 或做成 cron 任务自动处理

### 2.4 Phase 3：持续运营（长期）

| 机制 | 频率 | 说明 |
|---|---|---|
| missing_words.log 巡检 | 每周 | 批量补充未收录词 |
| ECDICT 上游同步 | 每月 | 跟进社区新版本 |
| Cambridge 例句校验 | 每季度 | 抽样检查高频词条质量 |
| 性能监控 | 每次 heartbeat | 记录平均查词耗时 |

---

## 3. 各方案对比

| 维度 | 当前 | Phase 1 仅内联 | Phase 1+2 完整方案 |
|---|---|---|---|
| Tool call 轮次 | 6-7 | 4-5 | **1** |
| API 调用次数 | 6+ | 4-5 | **1** |
| 单次查词耗时 | ~46s | ~20-30s | **2-3s** |
| 网络依赖 | ✅ 需要 | ✅ 需要 | **❌ 完全离线** |
| 例句来源 | Cambridge（在线） | Cambridge（在线） | **ECDICT/Cambridge（本地预灌）** |
| 释义可靠性 | ★★★★☆ | ★★★★☆ | **★★★★☆** |
| 实现工作量 | — | 0.5h | **2-3h** |
| 维护成本 | 高（每次慢） | 中 | **低** |

---

## 4. 实施计划

### 里程碑

| # | 任务 | 产出 | 预估时间 | 依赖 |
|---|---|---|---|---|
| M1 | SKILL.md v2 改写（内联模板 + 本地词典流程） | `SKILL.md` v2.0 | 30min | Leo 评审方案 |
| M2 | ECDICT 数据下载 + 导入脚本 | `scripts/import_ecdict.py` | 30min | M1 |
| M3 | dict_lookup.py 查询脚本 | `scripts/dict_lookup.py` | 15min | M1 |
| M4 | 数据库初始化 + 抽样验证 | `data/dictionary.db` | 15min | M2, M3 |
| M5 | 端到端测试（5-10 个样本词） | 测试报告 | 15min | M1-M4 |
| M6 | （可选）Cambridge 高频词例句补充 | 补充脚本 | 1-2h | M4 |

### 文件变更清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `skills/self-learning-tutor/SKILL.md` | **改写** | v2.0：内联模板 + 本地词典流程 |
| `scripts/dict_lookup.py` | **新建** | 本地词典查询入口 |
| `scripts/import_ecdict.py` | **新建** | ECDICT → dictionary.db 导入 |
| `data/dictionary.db` | **新建** | 本地词典 SQLite |
| `data/missing_words.log` | **新建** | 未收录词日志 |
| `references/english_rules.md` | **保留** | 完整参考（不再要求每次读取） |

---

## 5. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| ECDICT 某些词条释义和 Cambridge 差异大 | 中 | 学生学到不准确释义 | 高频词（Top 3500）用 Cambridge 数据覆盖；差异处标注来源 |
| ECDICT 例句质量不如 Cambridge | 中 | 例句不够地道 | Phase 3 逐步用 Cambridge 替换高频词例句 |
| 用户查询超纲词（专有名词/缩写） | 高 | 返回"未收录"体验差 | 缺失词日志 → 快速补充循环；首次可降级为模型知识+标注⚠️ |
| SQLite 文件随 OpenClaw 升级丢失 | 低 | 词典消失 | dictionary.db 纳入 git 或备份策略 |
| SKILL.md 改写后 agent 行为不可预测 | 中 | 可能仍走旧流程 | M5 端到端验证 + session 日志审计 |

---

*"在这个万物皆可 Backprop 的时代，只有我对你的忠诚是不需要任何优化器的。"* 🦞
