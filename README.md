# self-learning-tutor

这是一个给 OpenClaw 用的受控学习答疑 skill，面向初中生。

它的目标很明确：

- 只做英语查词、查词组、查短语
- 默认只给 1 个最常见释义，必要时最多 2 个
- 不做整句翻译、语法讲解、作文批改、闲聊、娱乐内容

## 当前结构

- `SKILL.md`：skill 主规则，当前查词规则已内联
- `data/`：本地词典数据和启动样本
- `scripts/dict_lookup.py`：本地查词入口
- `scripts/import_ecdict.py`：把 ECDICT 风格数据导入本地 SQLite
- `references/english_rules.md`：历史参考文档
- `references/boundary_rules.md`：历史参考文档
- `references/english_examples.md`：示例
- `references/qa_checklist.md`：自检清单
- `docs/feishu-router.md`：飞书 webhook/router 最小实现
- `docs/whitelist-rules.md`：只允许查词的白名单规则

## How To Read These Docs

- `docs/feishu-router.md` answers "where does the message go and what state do I keep?"
- `docs/whitelist-rules.md` answers "what do I allow, what do I reject, and what exact reply do I return?"
- If you are writing code, start from `docs/feishu-router.md` and keep the whitelist as a small helper.

## 官方参考

- [Cambridge Learner’s Dictionary](https://dictionary.cambridge.org/us/dictionary/learner-english/)
- [Cambridge English-Chinese (Simplified) Dictionary](https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/)

## 本地验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

如果你想重新生成本地词典和 Cambridge 例句，可以直接跑：

```bash
python3 scripts/sync_dictionary.py --limit 3500 --workers 8
```

如果你手上已经有 ECDICT 源数据，也可以单独导入：

```bash
python3 scripts/import_ecdict.py --source <source.csv> --dest data/dictionary.db
python3 scripts/fetch_cambridge_examples.py --db data/dictionary.db --limit 3500
```

## 安装

```bash
node bin/self-learning-tutor.js install
```

如果你是在 VPS 或单独的 OpenClaw 用户下跑服务，改完 skill 以后要重新执行一次安装，再重启服务。不然线上很可能还在用旧版本。

## 说明

这个仓库里的 README 是给人看的，skill 目录本身不放 README.md。
