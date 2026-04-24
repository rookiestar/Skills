# self-learning-tutor

这是一个给 OpenClaw 用的受控学习答疑 skill，面向初中生。

它的目标很明确：

- 只做英语查词、查词组、查短语
- 默认只给 1 个最常见释义，必要时最多 2 个
- 不做整句翻译、语法讲解、作文批改、闲聊、娱乐内容

## 当前结构

- `SKILL.md`：skill 主规则，已内联查词流程和输出模板
- `references/english_rules.md`：历史参考，不是运行时必读
- `references/boundary_rules.md`：历史参考，不是运行时必读
- `references/english_examples.md`：历史参考，不是运行时必读
- `references/qa_checklist.md`：历史参考，不是运行时必读
- `docs/feishu-router.md`：飞书 webhook/router 最小实现
- `docs/whitelist-rules.md`：只允许查词的白名单规则

## How To Read These Docs

- `SKILL.md` answers the runtime lookup flow.
- `docs/feishu-router.md` answers "where does the message go and what state do I keep?"
- `docs/whitelist-rules.md` answers "what do I allow, what do I reject, and what exact reply do I return?"
- If you are writing code, start from `SKILL.md` and keep the whitelist as a small helper.

## 数据构建参考

下面的链接只用于词库构建和人工校对，不是运行时依赖。

- [Cambridge Learner’s Dictionary](https://dictionary.cambridge.org/us/dictionary/learner-english/)
- [Cambridge English-Chinese (Simplified) Dictionary](https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/)

## 本地验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 安装

```bash
node bin/self-learning-tutor.js install
```

如果你是在 VPS 或单独的 OpenClaw 用户下跑服务，改完 skill 以后要重新执行一次安装，再重启服务。不然线上很可能还在用旧版本。

## 部署到 VPS

如果你要把本地词典一起同步到 VPS，可以直接用部署脚本：

```bash
bash "self learning tutor/scripts/deploy_openclaw_vps.sh"
```

脚本会先更新 VPS 上的源码，再从 `codex/local-dictionary-branch` 导出词库并同步到源码目录，最后重新安装到 OpenClaw 实际读取的目录里。安装结束后，它还会顺手验证 `important` 和 `重要的` 两个查询。

## 说明

这个仓库里的 README 是给人看的，skill 目录本身不放 README.md。
