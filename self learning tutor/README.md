# self-learning-tutor

这是一个给 OpenClaw 用的受控学习答疑 skill，面向初中生。

它的目标很明确：

- 只做英语查词、查词组、查短语
- 默认只给 1 个最常见释义，必要时最多 2 个
- 不做整句翻译、语法讲解、作文批改、闲聊、娱乐内容

## 当前结构

- `SKILL.md`：skill 主规则
- `references/english_rules.md`：英语查词格式和释义规则
- `references/boundary_rules.md`：拒绝话术和边界
- `references/english_examples.md`：示例
- `references/qa_checklist.md`：自检清单

## 官方参考

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

## 说明

这个仓库里的 README 是给人看的，skill 目录本身不放 README.md。
