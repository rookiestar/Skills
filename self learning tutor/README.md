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
- `docs/output-contract.md`：严格查词输出和未来扩展输出的边界
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

这是给本机开发环境用的安装命令，会把 skill 同步到本机的 workspace 副本里。
如果要更新 VPS 上正在跑的那份 skill，请用下面的部署脚本同步工作区目录，再重启服务。

## 部署到 VPS

如果你要把本地词典一起同步到 VPS，可以直接用部署脚本：

```bash
bash scripts/deploy_openclaw_vps.sh
```

脚本会先把当前提交打成一个版本目录，放到 `~/.openclaw/workspace/releases/self-learning-tutor/<版本号>` 里做验证，再把通过验证的内容覆盖到 `~/.openclaw/workspace/skills/self-learning-tutor`。最后它会重启 `openclaw-gateway.service`，然后再跑一轮加粗回归。

部署时会清理 `~/.openclaw/workspace/skills/self-learning-tutor.bak.*` 这类旧快照，避免新会话继续命中过期 skill。

线上 OpenClaw agent 需要收窄工具权限：保留 `exec`，禁用 `memory_search`、`memory_get`、`read`、`write`、`edit`、`apply_patch`、`process` 和跨会话工具。否则单词如 `memory` 可能被模型误判成“保存记忆”请求。

烟雾测试会检查 `important`、`in the future`、`sit down` 和 `put on` 这几类典型场景。

如果本地已经有 `data/dictionary.db`，脚本会先在本机把词条和短语刷新好，再把完整结果上传到 VPS。若本地库不完整，脚本会继续在本机重建发布包，不再去 VPS 上抓取。

如果你要主动刷新本地词库，直接重新走抓取和重建流程，不再需要单独的 POS 回填步骤。

## 说明

这个仓库里的 README 是给人看的，skill 目录本身不放 README.md。
