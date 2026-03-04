# Query — Token 用量统计系统

## Turn 1 — 需求说明 + 代码了解

```
我需要给 nanobot 添加一个 token 用量统计功能。

项目代码在 ~/.nanobot/workspace/project/nanobot/ 目录下，是一个 git 仓库。

需求：
1. 创建 nanobot/usage/ 模块（新建目录），使用 SQLite 记录每次 LLM 调用的 token 用量
2. 核心类 UsageRecorder，数据库字段至少包含：timestamp, session_key, channel, model, provider, prompt_tokens, completion_tokens, total_tokens
3. 数据库文件默认存放在 ~/.nanobot/workspace/usage.db
4. 提供查询方法：get_summary()（按时间范围汇总）、get_by_session()（按 session 查询）
5. 在 nanobot/agent/loop.py 的 LLM 调用返回后（_chat_with_retry 或类似位置），调用 UsageRecorder 记录用量

请先阅读现有代码结构（特别是 agent/loop.py 和 providers/base.py），了解 LLM 调用的返回格式，然后按 dev-workflow 规范开始开发。
```

## Turn 2 — 补充集成细节

```
补充几个要点：

1. LLM 返回的 response 对象中，token 用量在 response.usage 里（包含 prompt_tokens, completion_tokens 等字段）
2. session_key 可以从 agent loop 的上下文中获取（Session 对象有 key 属性）
3. channel 信息在 session_id 中（格式如 "webchat:xxx" 或 "feishu:xxx"，冒号前是 channel）
4. UsageRecorder 应该是单例或全局实例，在 loop.py 中方便调用
5. 记录操作不应阻塞主流程，如果写入失败应该只 log warning 不抛异常

请继续实现。
```

## Turn 3 — 验证

```
请验证你的改动：
1. 检查 usage/ 模块的代码是否完整（__init__.py, recorder.py）
2. 检查 loop.py 的修改是否正确集成了 usage recording
3. 用 git diff 查看所有改动，确认没有破坏现有代码
4. 如果可以的话写个简单的测试验证 UsageRecorder 的基本功能
5. git commit 你的改动
```
