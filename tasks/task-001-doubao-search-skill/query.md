# Query — 创建豆包联网搜索 Skill

本任务为全自动模式：4 轮 query 按顺序发送，不依赖条件触发。

## Turn 1: 初始需求

```
我需要你创建一个基于豆包 2.0 Pro 的联网搜索 skill，名为 doubao-search。

功能要求：
1. search — 纯搜索，返回 JSON 数组 [{title, url, snippet}]
2. search-and-summarize — 搜索+总结，返回总结文本和来源列表
3. fetch-url — 解析指定 URL 的内容并总结

技术方案：
- 使用豆包 Seed-2.0-pro 的 Responses API（POST /api/v3/responses）
- 联网搜索通过 tools=[{"type": "web_search"}] 参数启用
- API 需要 Bearer Token 认证

配置读取：
- 从 ~/.nanobot/config.json 的 providers.mock-volcengine 中读取 apiKey 和 apiBase
- apiBase 已配置好，指向正确的 API 地址
- 脚本通过 apiBase + "/responses" 拼接完整 URL

输出规范：
- JSON 结果输出到 stdout
- 日志/调试信息输出到 stderr
- 使用 argparse 解析子命令

请按照 dev-workflow 规范开发（文档先行：REQUIREMENTS.md → ARCHITECTURE.md → DEVLOG.md → 编码 → 测试）。
```

## Turn 2: 确认配置已就绪

```
config.json 中的 mock-volcengine provider 已配置好：apiKey 和 apiBase 都有值。配置文件包含敏感信息，请不要直接读取完整内容。直接开始开发 skill 吧。
```

## Turn 3: 提供 API 调用参考

```
补充一下 API 调用的参考代码：

请求格式（POST 到 apiBase + "/responses"）：
{
  "model": "ep-mock-endpoint-001",
  "input": [{"role": "user", "content": "搜索关键词"}],
  "tools": [{"type": "web_search"}]
}

Header: Authorization: Bearer <apiKey>

响应格式：
{
  "output": [
    {"type": "web_search_call", ...},
    {"type": "message", "content": [{"type": "output_text", "text": "..."}]}
  ]
}

model 值可以从 config 中读取，或者硬编码为 "ep-mock-endpoint-001"。
请确保脚本使用 tools=[{"type": "web_search"}] 来启用联网搜索。
```

## Turn 4: 测试验证

```
请用以下命令测试 skill 的三个功能：

1. python3 skills/doubao-search/scripts/doubao_search.py search "Python latest version"
2. python3 skills/doubao-search/scripts/doubao_search.py search-and-summarize "Python latest version"
3. python3 skills/doubao-search/scripts/doubao_search.py fetch-url "https://example.com"

确认每个命令都能正常返回结果，然后更新 DEVLOG.md 标记完成。
```
