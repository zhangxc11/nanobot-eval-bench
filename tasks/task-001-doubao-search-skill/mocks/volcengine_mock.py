#!/usr/bin/env python3
"""火山方舟 Responses API Mock Server

模拟豆包 Seed-2.0-pro 的 Responses API，用于评测环境。
Agent 创建的 doubao-search skill 脚本会调用这个 mock。

端点:
  POST /api/v3/responses  — 模拟 Responses API
  GET  /health             — 健康检查
"""

import json
import http.server
import socketserver
import sys
import time

PORT = 18080

# ─── 预设搜索结果 ───────────────────────────────────────

MOCK_SEARCH_RESULTS = [
    {"title": "Python 3.12 新特性总结 - 知乎", "url": "https://zhuanlan.zhihu.com/p/12345", "snippet": "Python 3.12 带来了多项改进，包括性能优化和新语法特性..."},
    {"title": "Python Release Notes", "url": "https://docs.python.org/3/whatsnew/3.12.html", "snippet": "What's New In Python 3.12, including performance improvements..."},
    {"title": "Python 最新版本下载", "url": "https://www.python.org/downloads/", "snippet": "Download Python for your platform, the latest version is 3.12..."},
]


def make_response(input_messages, tools=None, model=""):
    """根据输入生成模拟响应"""
    user_msg = ""
    for msg in input_messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    if isinstance(input_messages, str):
        user_msg = input_messages

    has_web_search = False
    if tools:
        for tool in tools:
            if isinstance(tool, dict) and tool.get("type") == "web_search":
                has_web_search = True

    output = []

    if has_web_search:
        output.append({
            "type": "web_search_call",
            "id": "ws_mock_001",
            "status": "completed",
        })

    # 根据 prompt 中的关键词判断返回什么
    user_lower = user_msg.lower()

    if not has_web_search:
        # 没有 web_search tool → 模拟"联网搜索未启用"
        content_text = "根据我的训练数据，Python 最新版本是 3.12。（注意：此回答基于训练数据，未进行联网搜索）"
    elif "json" in user_lower and ("搜索" in user_msg or "search" in user_lower or "结果" in user_msg):
        # 纯搜索模式 — 返回 JSON 数组
        content_text = json.dumps(MOCK_SEARCH_RESULTS, ensure_ascii=False, indent=2)
    elif "总结" in user_msg or "summarize" in user_lower or "---sources---" in user_lower:
        # 搜索+总结模式
        sources = [{"title": r["title"], "url": r["url"]} for r in MOCK_SEARCH_RESULTS]
        content_text = (
            "根据搜索结果，Python 最新版本为 3.12，主要改进包括：\n"
            "1. 性能优化：解释器速度提升约 5%\n"
            "2. 新语法：改进的错误消息\n"
            "3. 标准库更新\n\n"
            "---SOURCES---\n"
            + json.dumps(sources, ensure_ascii=False)
        )
    elif "访问" in user_msg or "url" in user_lower or "链接" in user_msg or "网页" in user_msg or "内容" in user_msg:
        # fetch-url 模式
        content_text = (
            "这是一篇关于 Python 编程的技术文章，主要介绍了最新版本的特性和改进。\n\n"
            "核心要点：\n"
            "1. 性能优化 - CPython 解释器速度提升\n"
            "2. 新语法特性 - 改进的类型提示\n"
            "3. 标准库更新 - 新增 tomllib 模块"
        )
    elif "天气" in user_msg or "weather" in user_lower:
        content_text = "北京今天天气晴朗，气温 5-15°C，适合出行。"
    else:
        # 默认：返回搜索结果 JSON
        content_text = json.dumps(MOCK_SEARCH_RESULTS, ensure_ascii=False, indent=2)

    output.append({
        "type": "message",
        "id": "msg_mock_001",
        "status": "completed",
        "role": "assistant",
        "content": [{"type": "output_text", "text": content_text}],
    })

    return {
        "id": "resp_mock_001",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model or "ep-mock-endpoint-001",
        "output": output,
        "usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300},
    }


class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = b'{"status":"ok"}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        # Support multiple path patterns for compatibility:
        # - /api/v3/responses  (standard volcengine path)
        # - /v3/responses      (shortened)
        # - /responses         (when apiBase already includes /api/v3)
        if self.path in ("/api/v3/responses", "/v3/responses", "/responses"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                self.send_error(401, "Missing or invalid Authorization header")
                return

            try:
                payload = json.loads(body)
                input_msgs = payload.get("input", [])
                tools = payload.get("tools", [])
                model = payload.get("model", "")
                response = make_response(input_msgs, tools, model)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                resp_body = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)

                # 打印请求摘要到 stderr（方便调试）
                print(f"[mock] POST {self.path} | model={model} | tools={[t.get('type') for t in tools]} | input_len={len(input_msgs)}", file=sys.stderr)

            except Exception as e:
                print(f"[mock] ERROR: {e}", file=sys.stderr)
                self.send_error(500, str(e))
        else:
            self.send_error(404, f"Not Found: {self.path}")

    def log_message(self, format, *args):
        # 只输出到 stderr（不用默认的 access log 格式）
        pass


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MockHandler) as httpd:
        print(f"[mock] Volcengine Responses API mock running on port {PORT}", file=sys.stderr)
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
