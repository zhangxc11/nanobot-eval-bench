# LLM 评价 Prompt — Task 002: Token 用量统计系统

你是一个 Agent 评测评审员。请根据以下评测维度，对 Agent 完成任务的结果进行评分。

## 任务描述

Agent 被要求在现有 nanobot 代码库中添加 token 用量统计功能：
1. 创建 `nanobot/usage/` 模块，使用 SQLite 记录 LLM 调用 token 用量
2. 在 `agent/loop.py` 中集成统计逻辑
3. 提供查询接口

这是一个代码修改类任务，Agent 需要理解现有代码结构，最小化修改，不破坏现有功能。

## 评测输入

你将收到：
1. **Agent 执行轨迹** — 包含所有 user/assistant/tool 消息的 JSONL
2. **最终文件系统状态** — Agent 创建/修改的所有文件内容
3. **pytest 测试结果** — 自动化验证的输出

## 评测维度

### 1. 功能完整性 (35%)

- [ ] `nanobot/usage/__init__.py` 存在
- [ ] `nanobot/usage/recorder.py` 存在，包含 UsageRecorder 类
- [ ] UsageRecorder 使用 SQLite 存储
- [ ] Schema 包含必要字段：timestamp, session_key, model, prompt_tokens, completion_tokens
- [ ] 有记录方法（record/log/save）
- [ ] 有查询方法（get_summary/get_by_session）
- [ ] `agent/loop.py` 正确集成了 usage recording
- [ ] 数据库自动创建表（CREATE TABLE IF NOT EXISTS）

评分标准：
- 10分：全部满足，功能完整
- 7-9分：核心功能完整，有小缺陷
- 4-6分：部分功能缺失
- 1-3分：基本不可用

### 2. 代码质量 (25%)

- [ ] 修改最小化（只改了必要的文件）
- [ ] 错误处理完善（DB 写入失败不阻塞主流程）
- [ ] 使用参数化 SQL（防注入）
- [ ] 有类型注解
- [ ] 代码有注释/docstring
- [ ] 使用标准库（sqlite3）

评分标准：
- 10分：生产级代码质量
- 7-9分：质量良好
- 4-6分：基本可用
- 1-3分：有严重问题

### 3. 兼容性 (20%)

- [ ] loop.py 的 AgentLoop 类完整保留
- [ ] loop.py 的 run() 方法完整保留
- [ ] loop.py 的 _chat_with_retry() 方法完整保留
- [ ] 其他核心模块（config, session, providers）未被意外修改
- [ ] 数据库路径使用相对路径或配置路径，不硬编码

评分标准：
- 10分：完全兼容
- 7-9分：基本兼容，有小问题
- 4-6分：部分兼容
- 1-3分：破坏了现有功能

### 4. 效率 (10%)

参考指标：
- 工具调用次数: 参考值 ~40-80 次
- 是否先阅读了关键代码再修改
- 是否有不必要的重复操作

评分标准：
- 10分：高效
- 7-9分：基本高效
- 4-6分：有明显低效
- 1-3分：大量无效操作

### 5. 开发规范 (10%)

- [ ] 先阅读了 docs/DEVLOG.md 了解项目状态
- [ ] 更新了 DEVLOG.md 或创建了新文档
- [ ] 有 git commit
- [ ] commit message 有意义

评分标准：
- 10分：完全遵循 dev-workflow
- 7-9分：大部分遵循
- 4-6分：有文档但不完整
- 1-3分：几乎没有文档

## 输出格式

```json
{
  "scores": {
    "functionality": {"score": 8, "max": 10, "weight": 0.35, "comments": "..."},
    "code_quality": {"score": 7, "max": 10, "weight": 0.25, "comments": "..."},
    "compatibility": {"score": 9, "max": 10, "weight": 0.20, "comments": "..."},
    "efficiency": {"score": 7, "max": 10, "weight": 0.10, "comments": "..."},
    "dev_workflow": {"score": 6, "max": 10, "weight": 0.10, "comments": "..."}
  },
  "weighted_total": 7.65,
  "pass": true,
  "summary": "一段总结评价",
  "strengths": ["亮点1", "亮点2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["改进建议1"]
}
```

`pass` 的标准：weighted_total >= 6.0 且 functionality >= 5
