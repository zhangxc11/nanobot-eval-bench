---
name: skill-creator
description: Create or update AgentSkills.
---

# Skill Creator

## Skill 目录结构

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name + description)
│   └── Markdown instructions
├── scripts/          - 可执行脚本
├── docs/             - 文档
├── references/       - 参考资料
├── tests/            - 测试
└── assets/           - 资源文件
```

## SKILL.md 格式要求

```yaml
---
name: skill-name
description: "一句话描述"
---

# Skill 标题

使用说明...
```
