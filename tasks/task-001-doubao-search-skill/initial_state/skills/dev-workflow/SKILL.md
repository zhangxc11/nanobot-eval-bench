---
name: dev-workflow
description: 软件开发工作流规范。所有代码项目（新建或维护）必须遵循此流程：文档先行（需求/架构/DEVLOG）、任务拆解、逐步开发、测试验证、Git 版本管理。
---

# 开发工作流规范

所有代码项目统一遵循此流程。

## 项目文档结构

每个项目必须包含 `docs/` 目录：

```
project/
├── docs/
│   ├── REQUIREMENTS.md   # 需求文档
│   ├── ARCHITECTURE.md   # 架构设计
│   └── DEVLOG.md         # 开发日志
├── tests/                # 测试代码
└── ...                   # 源代码
```

## 核心流程

### 新功能开发

```
1. 记录需求 → REQUIREMENTS.md 新增章节
2. 设计架构 → ARCHITECTURE.md 更新
3. 拆解任务 → DEVLOG.md 写入任务清单（checkbox）
4. 逐步实现 → 每完成一个子任务，勾选 checkbox
5. 测试验证 → 运行测试，确保通过
6. 更新文档 → DEVLOG 记录结果
```

## 开发纪律

1. **先读后改** — 修改文件前必须先 read_file 确认当前内容
2. **先测后提交** — 测试通过才能 git commit
3. **文档同步** — 代码改动必须同步更新相关文档
4. **小步快跑** — 每个子任务独立可验证
