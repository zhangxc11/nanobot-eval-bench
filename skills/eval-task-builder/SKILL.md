# eval-task-builder — 测例构造

根据 CASE_REGISTRY.md 中的候选描述，构造符合 eval-bench 框架规范的完整测例目录。

---

## 职责

将一条候选测例描述（来自 eval-session-scanner 的输出）转化为可运行的测例目录：

```
输入: CASE_REGISTRY.md 中的一行候选描述 + 来源 session 文件
输出: task-{id}-{slug}/ 完整目录（符合 TASK_SPEC.md 规范）
```

## 构造流程

```
1. 读取候选描述 → 确定任务类型 (Type A / Type B)
2. 读取来源 session → 提取相关对话片段
3. 分析任务需求 → 确定 initial_state、mock、验证方式
4. 构造 task.yaml（元数据 + 验证规则）
5. 构造 query.md（从原始对话提炼，去除敏感信息）
6. 构造 initial_state/（从 workspace 快照或 git 历史提取）
7. 构造 verify/（声明式规则或 pytest 脚本）
8. 构造 mocks/（如需外部 API mock）
9. 构造 eval_prompt.md（评价维度）
10. 验证测例完整性（task.yaml 解析 + 文件齐全）
11. 更新 CASE_REGISTRY.md 状态为 "✅ 已构造"
```

## 使用方式

### 让智能体构造单个测例

> 请使用 eval-task-builder skill，构造候选测例 A2（创建 calendar-reader Skill）。
> 来源 session 是 cli_direct.jsonl，输出到 eval-bench/tasks/ 目录。

### 关键参数

| 参数 | 说明 |
|------|------|
| 候选 ID | CASE_REGISTRY.md 中的编号（如 A2, N6） |
| 来源 session | session JSONL 文件路径 |
| 输出目录 | 测例目录的父目录（默认 eval-bench/tasks/） |
| 测例规范 | TASK_SPEC.md 路径（默认 eval-bench/docs/TASK_SPEC.md） |

## 框架改进反馈

构造过程中如果发现框架不支持某种测例模式（如：
- 新的验证规则类型
- 新的 initial_state 映射方式
- 新的 mock 服务模式
- runner.py 需要新功能
），应生成改进建议文档，供 eval-framework-maintainer 处理。

反馈格式：
```markdown
## 框架改进建议

### 来源
构造测例 A2 (calendar-reader Skill) 时发现

### 问题描述
当前框架不支持 XXX

### 建议方案
修改 runner.py 的 YYY 函数，增加 ZZZ 支持

### 影响范围
- runner.py
- TASK_SPEC.md
- 已有测例兼容性：无影响 / 需要更新 task-001
```

## 敏感信息处理

构造 query.md 时必须：
1. 移除所有 API Key、密码、token
2. 替换真实飞书 ID 为占位符（`ou_xxx`、`oc_xxx`）
3. 替换真实 URL 为示例 URL
4. 移除个人身份信息
5. 保留任务的核心交互模式和技术要求

## 测例规范

详见 `eval-bench/docs/TASK_SPEC.md`。

## 关键路径

| 文件 | 位置 |
|------|------|
| 测例清单 | `eval-bench-data/CASE_REGISTRY.md` |
| 测例输出目录 | `eval-bench-data/tasks/` |
| 测例规范 | `eval-bench/docs/TASK_SPEC.md` |
| Session 目录 | `~/.nanobot/workspace/sessions/` |
