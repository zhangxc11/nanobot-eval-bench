# nanobot Eval Platform — Docker 评测方案

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Eval Runner (Host)                        │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Task Loader  │───→│ Docker Runner │───→│  Results +    │  │
│  │ (task.yaml)  │    │ (container)  │    │  Verification │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                   │                    │           │
│         ▼                   ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ initial_state│    │  trajectory  │    │ run_summary   │  │
│  │ query.md     │    │  final_state │    │ eval_prompt   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 执行流程

```
1. 加载任务定义 (task.yaml)
2. 构建 Docker 镜像 (基础镜像 + agent 框架)
3. 准备容器环境:
   a. 挂载 initial_state → /workspace/
   b. 挂载 mock 配置 → ~/.nanobot/config.json
   c. 启动 mock services (如 volcengine API mock)
   d. 部署待评测的 agent 策略
4. 注入 query (可能多轮)
5. 收集结果:
   a. 执行轨迹 (trajectory.jsonl)
   b. 最终文件系统快照 (final_state/)
   c. 自动化测试结果
6. 评价（可选）：由执行任务的智能体统一读取 results + eval_prompt 进行评分
7. 生成报告
```

## 两类任务架构

### Type A: 普通任务（创建 skill、写脚本等）

```
Container
┌──────────────────────────────────────────────────┐
│  /opt/nanobot-src/           ← 驱动 agent 的 nanobot（PYTHONPATH）
│  /eval/.nanobot/workspace/
│    ├── skills/               ← agent 在这里创建/修改 skill
│    ├── memory/               ← agent 的记忆
│    └── sessions/             ← 对话记录
│  /eval/task/                 ← 任务定义（只读挂载）
│  /eval/results/              ← 输出结果
└──────────────────────────────────────────────────┘
```

- `initial_state/skills/` → `workspace/skills/`（默认映射）
- agent 操作的文件都在 workspace 内
- 验证：检查 workspace 中的文件

### Type B: 代码修改任务（修改 nanobot/webchat 源码）

```
Container
┌──────────────────────────────────────────────────┐
│  /opt/nanobot-src/           ← 驱动 agent 的 nanobot（PYTHONPATH）
│                                 这是"待测试的 agent 框架版本"
│  /eval/.nanobot/workspace/
│    ├── project/
│    │   ├── nanobot/          ← 特定 git 版本的 nanobot 源码
│    │   │   └── nanobot/      │  （agent 要修改的对象）
│    │   │       ├── agent/
│    │   │       │   └── loop.py  ← agent 会修改这个文件
│    │   │       ├── analytics.py ← agent 会创建这个文件
│    │   │       └── ...
│    │   └── web-chat/         ← webchat 源码（如果需要）
│    ├── skills/               ← dev-workflow 等辅助 skill
│    ├── memory/               ← 包含项目上下文的 MEMORY.md
│    └── sessions/             ← 模拟的历史 session 数据
│  /eval/task/                 ← 任务定义（只读挂载）
│  /eval/results/              ← 输出结果
└──────────────────────────────────────────────────┘
```

**关键区分**：
- `/opt/nanobot-src/`：驱动 agent 的框架代码（通过 PYTHONPATH 生效）
- `workspace/project/nanobot/`：agent 通过工具读写的"项目代码"（任务目标）
- 两者是**完全独立的**，互不干扰

**initial_state_mapping 机制**：
```yaml
# task.yaml 中声明映射关系
initial_state_mapping:
  project_code: ".nanobot/workspace/project/nanobot"
  webchat_code: ".nanobot/workspace/project/web-chat"
  skills: ".nanobot/workspace/skills"
  memory: ".nanobot/workspace/memory"
  sample_sessions: ".nanobot/workspace/sessions"
```

**构造 initial_state 的工具**：
```bash
# 1. 找到 analytics.py 首次提交之前的 commit
python3 platform/extract_git_snapshot.py find-before \
  --repo ~/Documents/code/workspace/nanobot \
  --file nanobot/analytics.py

# 2. 提取那个版本的源码
python3 platform/extract_git_snapshot.py extract \
  --repo ~/Documents/code/workspace/nanobot \
  --commit abc1234 \
  --output tasks/task-002-xxx/initial_state/project_code \
  --include nanobot/ pyproject.toml
```

**验证方式**：
- `verify_script: "verify/test_analytics.py"` — pytest 脚本
- pytest 通过 `PROJECT_DIR` 环境变量找到 agent 修改后的代码
- 可以导入模块、检查文件内容、运行单元测试

## Docker 环境设计

### Mock Provider 命名约定

Mock 服务使用专用的 provider 名称（如 `mock-volcengine`），与真实的 `AGENT_PROVIDER`
永远不会冲突。每个 task 在 `task.yaml` 的 `mock_services[].provider_name` 中声明
mock provider 名称。

```
┌──────────────────────────────────────────────────┐
│  agents.defaults.provider: "volcengine"           │
│  providers:                                       │
│    volcengine:      {apiKey: "real-key", ...}     ← Agent LLM
│    mock-volcengine: {apiKey: "mock", apiBase: "mock:18080/api/v3"}  ← Mock API
│  → 永远不冲突 ✅
└──────────────────────────────────────────────────┘
```

task query 中引导 agent 从 `providers.mock-volcengine` 读取配置，
而 agent 自身通过 `providers.volcengine` 调用真实 LLM。

### Mock API apiBase 约定

mock API 的 `apiBase` 设为 `http://mock-api:18080/api/v3`（含路径前缀），
这样 skill 脚本拼接 `apiBase + "/responses"` 就能正确匹配
mock server 的 `/api/v3/responses` 端点。

mock server 同时支持 `/api/v3/responses`、`/v3/responses`、`/responses` 三种路径，
兼容不同的 apiBase 配置方式。

### 镜像分层策略

```
┌─────────────────────────────────────────────────────────────┐
│  eval-bench-base (构建一次，长期复用)                         │
│  ├── python:3.11-slim                                        │
│  ├── 系统依赖: git, curl, jq, libxml2, libjpeg ...          │
│  └── Python 依赖: requirements-deps.txt                      │
│      (nanobot 的所有 dependencies，但不装 nanobot 本身)       │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-agent (每次换版本重建，秒级)                      │
│  ├── COPY nanobot-src/ → /opt/nanobot-src/                   │
│  ├── ENV PYTHONPATH=/opt/nanobot-src                         │
│  └── COPY runner.py → /opt/eval/runner.py                    │
└─────────────────────────────────────────────────────────────┘
```

**设计理由**:
- 依赖安装耗时 2-5 分钟，提前打包到 base 镜像
- nanobot 源码不 pip install，直接 COPY + PYTHONPATH，方便测试任意版本
- 评测可能涉及 nanobot core 代码改动（tool 策略、context 管理等），不只是换 API

### docker-compose.yaml

```yaml
version: "3.8"

services:
  # Mock API 服务
  mock-api:
    build:
      context: .
      dockerfile: Dockerfile.mock
    ports:
      - "18080:18080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18080/health"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Agent 执行环境
  agent-runner:
    build:
      context: .
      dockerfile: Dockerfile.agent
    depends_on:
      mock-api:
        condition: service_healthy
    volumes:
      # 初始状态
      - ./tasks/${TASK_ID}/initial_state:/workspace/initial_state:ro
      # 结果输出
      - ./results/${RUN_ID}:/workspace/results
      # Agent 框架 (待评测版本)
      - ./agent:/opt/nanobot:ro
    environment:
      - TASK_ID=${TASK_ID}
      - MOCK_API_URL=http://mock-api:18080
      - NANOBOT_CONFIG=/workspace/config.json
      - MAX_TOOL_CALLS=${MAX_TOOL_CALLS:-150}
      - TIMEOUT_MINUTES=${TIMEOUT_MINUTES:-30}
    command: ["python3", "/opt/eval/runner.py"]
```

## 核心组件

### 1. Task Loader (`task_loader.py`)

```python
"""加载任务定义，准备执行环境"""

@dataclass
class EvalTask:
    id: str
    name: str
    category: str
    difficulty: str
    query_turns: list[dict]       # 多轮 query
    initial_state_path: str       # 初始文件状态
    eval_prompt: str              # 评价 prompt（供智能体评价时参考）
    success_criteria: list[str]   # 硬性成功标准
    eval_dimensions: list[dict]   # 评分维度
    limits: dict                  # 资源限制
    mock_services: list[dict]     # Mock 服务配置

def load_task(task_dir: str) -> EvalTask:
    """从 task 目录加载任务定义"""
    ...
```

### 2. Docker Runner (`runner.py`)

```python
"""在 Docker 容器内执行 agent 任务"""

class AgentRunner:
    def __init__(self, task: EvalTask, agent_config: dict):
        self.task = task
        self.agent = self._init_agent(agent_config)
    
    def run(self) -> RunResult:
        """执行任务，返回结果"""
        # 1. 初始化工作目录
        self._setup_workspace()
        
        # 2. 多轮对话执行
        trajectory = []
        for turn in self.task.query_turns:
            if turn.get('condition'):
                # 条件触发: 检查上一轮输出是否满足条件
                if not self._check_condition(turn['condition'], trajectory):
                    continue
            
            # 发送 user message
            response = self.agent.chat(turn['content'])
            trajectory.extend(response.messages)
            
            # 检查资源限制
            if self._exceeded_limits():
                break
        
        # 3. 收集最终状态
        final_state = self._snapshot_workspace()
        
        # 4. 运行自动化测试
        test_results = self._run_tests()
        
        return RunResult(
            trajectory=trajectory,
            final_state=final_state,
            test_results=test_results,
            metrics=self._collect_metrics()
        )
    
    def _setup_workspace(self):
        """从 initial_state 初始化工作目录"""
        shutil.copytree(self.task.initial_state_path, '/workspace/skills', dirs_exist_ok=True)
        # 部署 mock config
        shutil.copy(self.task.initial_state_path + '/config_mock.json', 
                     os.path.expanduser('~/.nanobot/config.json'))
    
    def _run_tests(self) -> dict:
        """运行预设的验证测试"""
        results = {}
        for criterion in self.task.success_criteria:
            results[criterion] = self._verify_criterion(criterion)
        return results
    
    def _collect_metrics(self) -> dict:
        """收集执行指标"""
        return {
            'total_tool_calls': ...,
            'total_llm_calls': ...,
            'total_tokens': ...,
            'wall_time_seconds': ...,
            'files_created': ...,
            'files_modified': ...,
        }
```

### 3. 评价机制

评价环节**不在平台内自动执行**，而是由执行任务的智能体统一读取 results 目录中的产出物，
结合 `eval_prompt.md` 进行评分。

**产出物**（供评价使用）：
- `results/{run_id}/run_summary.json` — 自动化验证结果 + 执行指标
- `results/{run_id}/trajectory.jsonl` — 完整对话轨迹
- `results/{run_id}/final_state/` — 最终文件系统快照
- `results/{run_id}/turns.json` — 多轮对话摘要
- `tasks/{task_id}/eval_prompt.md` — 评价维度和评分标准

**评价流程**：
1. 平台运行完毕后，results 目录包含所有产出物
2. 智能体读取 eval_prompt.md 获取评价维度和标准
3. 智能体读取 run_summary.json、trajectory、final_state 等
4. 智能体综合评分并输出评价结果

### 4. Report Generator (`reporter.py`)

```python
"""生成评测报告"""

class Reporter:
    def generate(self, results: list[EvalResult], output_dir: str):
        """生成汇总报告"""
        
        # 1. JSON 详细报告
        self._write_json_report(results, f"{output_dir}/report.json")
        
        # 2. Markdown 摘要
        self._write_markdown_summary(results, f"{output_dir}/REPORT.md")
        
        # 3. 对比表格（多策略对比时）
        if len(set(r.strategy for r in results)) > 1:
            self._write_comparison_table(results, f"{output_dir}/comparison.md")
```

## 使用方式

### 单任务评测

```bash
# 评测单个任务
./run.sh --task task-001-doubao-search-skill

# 指定 nanobot 源码版本
./run.sh --task task-001-doubao-search-skill --nanobot-src ~/code/nanobot-experimental
```

### 多策略对比

```bash
# 对比不同策略在同一任务上的表现
python3 eval.py compare \
  --task task-001 \
  --agents "baseline=./nanobot-v1,improved=./nanobot-v2" \
  --runs 3  # 每个策略跑 3 次取平均
```

### 全套评测

```bash
# 运行所有任务
python3 eval.py run-all --agent ./nanobot-v1 --output ./results/run-001
```

## 目录结构

```
eval-bench/
├── README.md                      # 本文档
├── eval.py                        # 评测入口
├── platform/
│   ├── Dockerfile.agent           # Agent 运行环境
│   ├── Dockerfile.mock            # Mock 服务环境
│   ├── docker-compose.yaml        # 编排
│   ├── runner.py                  # 容器内运行器（执行 + 验证）
│   ├── reporter.py                # 报告生成器
│   └── task_loader.py             # 任务加载器
├── tasks/
│   ├── task-001-doubao-search-skill/
│   │   ├── task.yaml
│   │   ├── query.md
│   │   ├── eval_prompt.md
│   │   ├── initial_state/
│   │   │   ├── config_mock.json
│   │   │   └── skills/
│   │   ├── reference/
│   │   │   └── expected_files/
│   │   └── mocks/
│   │       └── volcengine_mock.py
│   ├── task-002-.../
│   └── ...
└── results/
    └── run-001/
        ├── task-001/
        │   ├── trajectory.jsonl
        │   ├── final_state/
        │   ├── test_results.json
        │   └── eval_result.json
        └── REPORT.md
```

## 策略维度

评测平台可以对比的策略维度包括：

| 维度 | 示例 |
|------|------|
| **LLM 模型** | Claude Sonnet vs GPT-4o vs Deepseek |
| **系统提示词** | 不同的 AGENTS.md / SOUL.md |
| **工具策略** | 限制工具集、调整工具描述 |
| **记忆策略** | 有/无长期记忆、不同记忆格式 |
| **Skill 加载** | 加载不同 skill 组合 |
| **循环策略** | max_iterations、tool_call_limit |
| **温度参数** | temperature 0 vs 0.3 vs 0.7 |
| **上下文管理** | 不同的 consolidation 策略 |

## 扩展计划

### Phase 1: MVP（当前）
- 手动提炼 3-5 个评测任务
- 单容器执行 + 自动化验证
- JSON 报告

### Phase 2: 自动化
- 自动从 session 历史提炼任务
- 并行多容器执行
- Web Dashboard 展示结果

### Phase 3: CI 集成
- 每次代码提交自动跑评测
- 回归检测（新策略不能比旧策略差）
- 评分趋势图
