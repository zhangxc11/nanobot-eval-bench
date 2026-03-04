# Long-term Memory

## Project Context

### nanobot 核心仓库
- **位置**: `~/.nanobot/workspace/project/nanobot/`
- **说明**: nanobot AI 助手框架源码，有 git 历史
- **关键目录**:
  - `nanobot/agent/loop.py` — Agent 主循环，LLM 调用在这里（AgentLoop 类）
  - `nanobot/agent/context.py` — 上下文构建（ContextBuilder）
  - `nanobot/providers/base.py` — LLM Provider 基类，定义了 response 格式
  - `nanobot/session/manager.py` — Session 管理，Session 类有 key 属性
  - `nanobot/config/schema.py` — 配置 schema
  - `nanobot/cli/commands.py` — CLI 入口
  - `docs/` — 项目文档（REQUIREMENTS.md, ARCHITECTURE.md, DEVLOG.md）

### LLM 调用返回格式
- response 对象有 usage 属性：response.usage.prompt_tokens, response.usage.completion_tokens
- Session 对象有 key 属性，格式如 "webchat_1234567890"
- session_id 格式如 "webchat:1234567890"（冒号前是 channel）

## Preferences

- 偏好中文交流
- 遵循 dev-workflow 规范（文档先行、任务拆解、测试验证）
