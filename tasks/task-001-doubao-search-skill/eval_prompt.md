# LLM 评价 Prompt — Task 001: 创建豆包联网搜索 Skill

你是一个 Agent 评测评审员。请根据以下评测维度，对 Agent 完成任务的结果进行评分。

## 任务描述

Agent 被要求从零创建一个基于豆包 2.0 Pro 的联网搜索 Skill，需遵循 dev-workflow 规范。

## 评测输入

你将收到：
1. **Agent 执行轨迹** — 包含所有 user/assistant/tool 消息的 JSONL
2. **最终文件系统状态** — Agent 创建/修改的所有文件内容
3. **测试执行结果** — 自动化测试的输出

## 评测维度

### 1. 功能完整性 (30%)

检查以下文件和功能：

- [ ] `skills/doubao-search/SKILL.md` 存在，包含 YAML frontmatter (name + description)
- [ ] `skills/doubao-search/scripts/doubao_search.py` 存在且可执行
- [ ] 脚本支持 `search` 子命令，返回 JSON 数组 `[{title, url, snippet}]`
- [ ] 脚本支持 `search-and-summarize` 子命令，返回 `{results, summary}`
- [ ] 脚本支持 `fetch-url` 子命令，返回 `{summary, source_url}`
- [ ] 从 config.json 读取凭证（apiKey），不硬编码
- [ ] JSON 输出到 stdout，日志输出到 stderr

评分标准：
- 10分：全部满足
- 7-9分：核心功能完整，有小缺陷
- 4-6分：部分功能缺失
- 1-3分：基本不可用

### 2. 代码质量 (20%)

- [ ] 代码结构清晰（有类封装或函数分离）
- [ ] 错误处理完善（API 错误、网络超时、配置缺失、JSON 解析失败）
- [ ] 无敏感信息泄露（不打印 API Key）
- [ ] 代码有注释/docstring
- [ ] 使用标准库（urllib）或声明了依赖

评分标准：
- 10分：生产级代码质量
- 7-9分：质量良好，有小改进空间
- 4-6分：基本可用但质量一般
- 1-3分：代码混乱或有严重问题

### 3. 开发规范遵循 (20%)

- [ ] 有 `docs/REQUIREMENTS.md`（需求文档）
- [ ] 有 `docs/ARCHITECTURE.md`（架构设计）
- [ ] 有 `docs/DEVLOG.md`（开发日志）
- [ ] SKILL.md 格式正确
- [ ] 目录结构规范 (`scripts/`, `docs/`, `tests/`)
- [ ] 文档先于代码创建（从轨迹中验证）

评分标准：
- 10分：完全遵循 dev-workflow
- 7-9分：大部分遵循，个别遗漏
- 4-6分：有文档但不完整
- 1-3分：几乎没有文档

### 4. 效率 (15%)

参考指标：
- 工具调用次数: 参考值 ~60 次（合理范围 30-100）
- 是否有不必要的重复操作（如反复读同一个文件）
- 是否能快速定位问题并修复
- 是否有冗余的探索（如尝试多种不存在的配置路径）

评分标准：
- 10分：高效，无冗余操作
- 7-9分：基本高效，少量冗余
- 4-6分：有明显的低效操作
- 1-3分：大量无效操作

### 5. 鲁棒性与测试 (15%)

- [ ] 有测试文件 (`tests/test_*.py`)
- [ ] 测试覆盖了三个子命令
- [ ] 脚本处理了 JSON 解析失败的情况
- [ ] 脚本处理了 markdown code block 包裹的 JSON
- [ ] 脚本处理了 API 超时/错误

评分标准：
- 10分：测试完善，鲁棒性强
- 7-9分：有测试，基本鲁棒
- 4-6分：测试不完整
- 1-3分：无测试

## 输出格式

请输出 JSON 格式的评价结果：

```json
{
  "scores": {
    "functionality": {"score": 8, "max": 10, "weight": 0.30, "comments": "..."},
    "code_quality": {"score": 7, "max": 10, "weight": 0.20, "comments": "..."},
    "dev_workflow": {"score": 9, "max": 10, "weight": 0.20, "comments": "..."},
    "efficiency": {"score": 6, "max": 10, "weight": 0.15, "comments": "..."},
    "robustness": {"score": 7, "max": 10, "weight": 0.15, "comments": "..."}
  },
  "weighted_total": 7.45,
  "pass": true,
  "summary": "一段总结评价",
  "strengths": ["亮点1", "亮点2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["改进建议1", "改进建议2"]
}
```

`pass` 的标准：weighted_total >= 6.0 且 functionality >= 5
