# Cambridge Dictionary 全量重建方案

> **日期**: 2026-04-25
> **状态**: 📋 方案待评审
> **目标**: 放弃 ECDICT 数据源，从 Cambridge Dictionary 直接构建 dictionary.db，覆盖高考词汇 + 延伸词表

---

## 1. 背景与动机

### 1.1 当前问题

| 问题 | 详情 |
|------|------|
| ECDICT 无词性 | 77 万词条中 73% 的 `pos` 为空，仅靠文本推断补了 27% |
| ECDICT 释义质量差 | 大量词条 definition 为空，只有中文 translation，无法区分多义词 |
| 频率数据误导 | ECDICT 的 bnc 是语料库原始频次（人名/地名虚高），不是"常用程度" |
| 数据源混杂 | 当前 db 是 ECDICT 为主 + Cambridge 例句打补丁，维护复杂 |

### 1.2 为什么选 Cambridge

| 维度 | ECDICT | Cambridge |
|------|--------|-----------|
| 词性 | 无 | 标准完整（noun/verb/adjective...） |
| 音标 | 有（有时不准） | 英美双音标，权威 |
| 英文释义 | 大量空缺 | 完整，适合中学生理解 |
| 中文翻译 | 有 | 权威简明 |
| 例句 | 少量/质量不一 | 丰富地道 |
| CEFR 等级 | 无 | A1-C2 分级 |
| 词条覆盖 | ~77 万（含大量垃圾） | 聚焦常用词，质量高 |

### 1.3 目标范围

| 层级 | 词数 | 说明 |
|------|------|------|
| 高考课标核心 | ~2,000 | 必修课程词汇 |
| 高考课标扩展 | ~1,000 | 选择性必修词汇 |
| 延伸词表 | ~500-1,000 | 派生词、短语、初中常见超纲词 |
| **总计目标** | **~3,500-4,000** | 覆盖初中 + 高中全场景 |

---

## 2. 技术方案

### 2.1 架构总览

```
┌──────────────────────────────────────────────────────┐
│                  新数据流水线                          │
│                                                      │
│  词表文件 (txt/csv)                                   │
│    │                                                 │
│    ▼                                                 │
│  ┌──────────────────────┐                            │
│  │ scripts/build_       │ ← 主脚本：读词表 → 并发爬取 │
│  │ cambridge_dict.py    │   → 解析 HTML → 写入 DB     │
│  └────────┬─────────────┘                            │
│           │                                           │
│           ▼                                           │
│  ┌──────────────────────┐     ┌──────────────────┐   │
│  │ data/dictionary.db   │     │ data/dictionary_  │   │
│  │ (主表)               │     │ reverse.db        │   │
│  │ word / pos / phonetic│     │ (反向索引)         │   │
│  │ / def / trans / ex  │     │ zh_term → word    │   │
│  │ / cefr / source      │     │                    │   │
│  └──────────────────────┘     └──────────────────┘   │
│                                                      │
│  复用现有脚本（无需修改）：                             │
│  ├── dict_lookup.py          查询入口                  │
│  ├── backfill_dictionary_pos.py 文本推断回退          │
│  └── fetch_cambridge_examples.py 例句补充             │
└──────────────────────────────────────────────────────┘
```

### 2.2 Cambridge 页面字段提取（已验证）

以 `https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/{word}` 为例：

| 字段 | CSS 选择器 | 示例值 | 映射到 DB 列 |
|------|-----------|---------|-------------|
| 单词 | `.entry-body .hw` | `happy` | `word` |
| 词性 | `.entry-body .pos` | `adjective` | `pos` (转缩写) |
| 英式音标 | `.entry-body .uk .pron` 或 `.ipa` | `/ˈhæp.i/` | `phonetic_uk` |
| 美式音标 | `.entry-body .us .pron` 或 `.ipa` | `/ˈhæp.i/` | `phonetic_us` |
| CEFR 等级 | `div.def-block [class*="epp"]` → regex `[A-C][12]` | `A1` | `cefr_level` (新列) |
| 英文释义 | `div.def-block .def` | `feeling, showing, or causing pleasure...` | `definition` |
| 中文翻译 | `div.def-block .trans` | `幸福的，满意的，快乐的` | `translation` |
| 多释义列表 | 所有 `div.def-block` 的 `.def` + `.trans` 组合 | JSON array | `definitions` |
| 例句 | `div.def-block .examp.dexamp` | `She looks so happy.` | `example` |
| 来源 URL | 请求 URL 本身 | `https://.../happy` | `example_url` |

**POS 映射规则（Cambridge 全称 → ECDICT 缩写）：**

```python
CAMBRIDGE_TO_ECDICT = {
    "noun": "n.", "verb": "v.", "adjective": "a.", "adverb": "adv.",
    "preposition": "prep.", "pronoun": "pron.", "conjunction": "conj.",
    "interjection": "int.", "exclamation": "int.", "determiner": "det.",
}
```

**多义词处理策略：**
- 取第一个 `div.block` 的 POS 作为主词性（最常用义）
- `definitions` 字段存 JSON 数组，包含前 3 个主要释义（每个含英文 + 中文）
- `translation` 存第一个中文释义（用于快速展示）
- `example` 取第一个例句

### 2.3 反爬策略

| 策略 | 实现 | 参数 |
|------|------|------|
| **并发控制** | `ThreadPoolExecutor(max_workers=4)` | 默认 4，可调 |
| **请求间隔** | 每个请求后随机 sleep | `uniform(0.5, 2.0)` 秒 |
| **Session 复用** | 单一 `requests.Session()` + connection pooling | 减少握手开销 |
| **User-Agent 轮换** | 从 5 个真实 UA 中随机选取 | 每次 request 随机 |
| **Fallback URL** | 3 个字典模板依次尝试 | english-chinese-simplified → learner-english → english |
| **超时控制** | 单次请求 timeout=20s | 可配置 |
| **错误重试** | 每词最多重试 2 次 | 指数退避 |
| **断点续爬** | 记录已成功词表，跳过已入库 | 基于 `source='cambridge' AND pos != ''` |
| **进度持久化** | 每 100 条 commit 一次 | 防止中断丢失 |
| **Cloudflare 绕过** | 标准 headers + 合理频率 | 不用 headless browser |

**不被封的关键参数估算：**

```
4000 词 ÷ 4 并发 = 1000 批次
每批平均 1.25s（请求 0.5s + 等待 1.0s）
总耗时 ≈ 1000 × 1.25s ≈ 21 分钟
QPS ≈ 0.8（远低于触发阈值）
```

### 2.4 数据库 Schema 变更

在现有 schema 基础上新增一列：

```sql
ALTER TABLE dictionary ADD COLUMN cefr_level TEXT DEFAULT NULL;
-- 存储值: A1, A2, B1, B2, C1, C2
```

其余列复用现有结构，保持向后兼容：

```
现有列（保留）:
  word, phonetic, phonetic_uk, phonetic_us, pos,
  definition, translation, definitions,
  collins(废弃), oxford(废弃), tag(废弃),
  bnc(废弃), frq(废弃), frequency(废弃),
  exchange, detail, audio,
  example, example_source, example_url,
  source(改为 'cambridge'), updated_at

新增列:
  cefr_level TEXT  -- Cambridge CEFR 等级
```

> 注：collins/oxford/bnc/frq/frequency 等 ECDICT 特有列保留但不填充，
> 避免 schema 变更影响现有查询代码。后续清理时可移除。

### 2.5 词表输入格式

支持两种输入方式：

**方式 A — 纯单词列表（每行一个词）：**
```
abandon
ability
able
about
above
...
```

**方式 B — CSV（可选带初始标注）：**
```
word,level
abandon,gk
ability,gk
...
```

其中 `level` = `ck` (初中课标) / `gk` (高中课标) / `ext` (延伸)

默认读取路径：`data/cambridge_wordlist.txt`

### 2.6 输出格式示例

重建后 `dict_lookup.py --mode en_to_zh happy` 返回：

```json
{
  "word": "happy",
  "pos": "a.",
  "phonetic": "/ˈhæp.i/",
  "phonetic_uk": "/ˈhæp.i/",
  "phonetic_us": "/ˈhæp.i/",
  "definitions": [
    "幸福的，满意的，快乐的",
    "（用于特殊日子的祝福）…快乐"
  ],
  "definition": "feeling, showing, or causing pleasure or satisfaction",
  "translation": "幸福的，满意的，快乐的",
  "example": "She looks so happy. 她看上去非常快乐。",
  "example_source": "cambridge",
  "example_url": "https://dictionary.cambridge.org/.../happy",
  "source": "cambridge",
  "cefr_level": "A1"
}
```

---

## 3. 实施步骤

### Phase 1：Prototype（验证可行性）

| # | 任务 | 产出 | 预估时间 |
|---|------|------|----------|
| P1 | 编写 `scripts/build_cambridge_dict.py` 核心框架 | Python 脚本 | 30min |
| P2 | 实现 HTML 解析器（全部字段） | 提取函数 | 30min |
| P3 | 接入反爬策略（并发/延迟/UA轮换） | 配套代码 | 20min |
| P4 | 准备 100 词测试词表 | `data/prototype_wordlist.txt` | 10min |
| P5 | 运行 prototype，验证数据质量 | 测试结果报告 | 15min |
| P6 | 用 SKILL.md 模板端到端验证 5 个样本词 | 通过/不通过 | 15min |

**Prototype 验收标准：**
- 100 词成功率 ≥ 95%
- 每条记录的 pos / phonetic / definition / translation / example 五字段齐全率 ≥ 90%
- 无 HTTP 429/403 错误
- 总耗时 < 5 分钟

### Phase 2：全量构建

| # | 任务 | 产出 | 预估时间 |
|---|------|------|----------|
| M1 | 准备完整词表（~4000 词） | `data/cambridge_wordlist.txt` | 用户准备或自动生成 |
| M2 | 新增 `cefr_level` 列到 dictionary.db | schema migration | 5min |
| M3 | 全量爬取并写入 DB | `data/dictionary.db` (~20-30min) | 30min |
| M4 | 构建 dictionary_reverse 反向索引 | `dictionary_reverse` 表 | 5min |
| M5 | 数据校验（抽样 200 条） | 校验报告 | 15min |
| M6 | 更新 `sync_dictionary.py` 流程 | 移除 ECDICT 导入步骤 | 10min |

### Phase 3：持续运营

| 机制 | 频率 | 说明 |
|------|------|------|
| 缺失词补充 | 按 missing_words.log | 定期批量爬取新词 |
| 数据刷新 | 每季度 | 重跑已有词，更新例句/释义 |
| 词表扩展 | 按需 | 学生实际查询中超纲但合理的词 |

---

## 4. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/build_cambridge_dict.py` | **新建** | 核心：Cambridge 全量爬取+解析+入库 |
| `data/cambridge_wordlist.txt` | **新建** | 目标词表（~4000 行） |
| `data/prototype_wordlist.txt` | **新建** | Prototype 测试词表（100 行） |
| `data/dictionary.db` | **重建** | 清空后由 Cambridge 数据填充 |
| `scripts/sync_dictionary.py` | **修改** | 移除 ECDICT 导入，改为调用 build_cambridge_dict.py |
| `scripts/import_ecdict.py` | **保留** | 不再使用，归档备用 |

---

## 5. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| Cambridge 封 IP | 低 | 全量爬取中断 | ① Prototype 验证安全频率 ② 断点续爬 ③ 降级到 2 并发 |
| 某些词 Cambridge 未收录 | 中 | 少量词缺失 | 标记为 not_found，后续可用 ECDICT 补充或 LLM 生成 |
| HTML 结构变更 | 低 | 解析失败 | ③ 个 fallback URL + 日志记录失败词 + 定期检查选择器 |
| 词表来源不确定 | 中 | 不知道具体爬哪些词 | 用户需提供词表；或基于 collins≥1 的 ECDICT 子集生成 |
| CEFR 字段部分词无标注 | 中 | cefr_level 为空 | 约 15-20% 的词没有 CEFR 标注，接受 NULL |
| 一次全量耗时较长 | 低 | 需等待 20-30 分钟 | 进度条输出 + 断点续爬 + 后台运行模式 |

---

## 6. 与现有方案的对比

| 维度 | 当前（ECDICT 为主） | 新方案（Cambridge 全量） |
|------|---------------------|------------------------|
| 数据源 | ECDICT CSV + Cambridge 打补丁 | Cambridge 唯一 |
| 词性覆盖率 | 27%（207K/770K） | **~98%（预计）** |
| 释义完整性 | 大量空缺 | **完整** |
| 音标准确性 | 一般 | **权威** |
| 例句质量 | 混合 | **统一 Cambridge** |
| CEFR 分级 | 无 | **有** |
| 词条数量 | 77 万（大量低质） | **~4,000（精炼）** |
| 维护复杂度 | 双数据源 | **单数据源** |
| 初中生适用性 | 需要过滤 | **开箱即用** |
