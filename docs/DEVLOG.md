# eval-bench 开发日志

## Phase 10: Volcengine 评测反馈修复 (2026-03-11)

### 背景
- Volcengine 豆包模型评测报告（REPORT.md, 2026-03-09 ~ 03-10）反馈了 5 项框架级问题
- 36 个测例端到端评测中，24 个记录了非 Agent 能力的问题
- 本 Phase 修复 P0/P1 项，标记已完成/暂不修复项

### 任务清单

#### 10.1 task-032 改为预构建 git 仓库（P0）
- [x] 10.1.1 本地执行 setup_repo.sh 构建完整 git 仓库（含 local/upstream_main/main 三个分支）
- [x] 10.1.2 将预构建仓库放入 `initial_state/nanobot_repo/`，通过 `initial_state_mapping` 直接复制
- [x] 10.1.3 删除 `setup_script`/`setup_args` 字段、`repo_snapshots` 目录、`setup_repo.sh`
- [x] 10.1.4 runner.py 移除 setup_script 机制（YAGNI，无其他使用场景）

#### 10.2 trajectory.jsonl 只复制 eval session（P1）
- [x] 10.2.1 计算期望文件名：`SESSION_ID.replace(":", "_") + ".jsonl"`
- [x] 10.2.2 优先查找匹配 SESSION_ID 的文件
- [x] 10.2.3 找不到再 fallback 到 glob 第一个（向后兼容）
- [x] 10.2.4 打印日志说明匹配方式

#### 10.3 task-006 test_total_records 隔离 agent usage（P1）
- [x] 10.3.1 修改 eval-bench-data 的 `test_usage_cleanup.py`
- [x] 10.3.2 `test_total_records` 改为只统计 `webchat:test_session_%` 的记录
- [x] 10.3.3 添加注释说明过滤原因

#### 10.4 Dispatcher 已改为 spawn（标记已完成）
- [x] 10.4.1 最新版本已使用 spawn 方式调度，无需修改

#### 10.5 LLM 评分用不同模型（暂不修复）
- [x] 10.5.1 暂不在框架内实现，事后人工评分

### 涉及文件

| 仓库 | 文件 | 改动 |
|------|------|------|
| eval-bench | `platform/runner.py` | 10.1 (移除 setup_script), 10.2 (trajectory 精确匹配) |
| eval-bench | `docs/REQUIREMENTS.md` | 追加 R10.1~R10.5 需求 |
| eval-bench | `docs/DEVLOG.md` | Phase 10 记录 |
| eval-bench-data | `tasks/task-032-*/task.yaml` | 10.1 (改为 nanobot_repo 映射) |
| eval-bench-data | `tasks/task-032-*/initial_state/` | 10.1 (预构建 git 仓库替换 repo_snapshots) |
| eval-bench-data | `tasks/task-006-*/verify/test_usage_cleanup.py` | 10.3 (过滤 agent usage) |
| skills | `eval-task-builder/SKILL.md` | 预构建仓库说明 |
| skills | `eval-framework-maintainer/SKILL.md` | 框架维护更新 |
| skills | `eval-task-batch-builder/SKILL.md` | 预构建仓库提醒 |

### 完成时间
- 2026-03-11

---

## Phase 3: Issues v2 修复 + Task-002 代码修改类任务支持 (2026-03-04)

### 背景
- 基于 volcengine 模型实际运行 task-001 的反馈 (ISSUESv2.md)，修复 4 个问题
- 新增 task-002 (B9 Token 用量统计) 代码修改类任务支持
- 整体架构完善：initial_state_mapping、verify_script、extract_git_snapshot

### 任务清单

#### 3.1 修复 ISSUESv2 中的 4 个问题
- [x] 3.1.1 docker-compose.yaml: mock-api 改为 pre-built image（run.sh 统一构建）
- [x] 3.1.2 runner.py: volcengine provider 冲突解决 — 自动检测 CONFLICTING_PROVIDERS，使用 custom provider 绕过
- [x] 3.1.3 .env.example: 增加 volcengine 专用提示（AGENT_API_BASE 必填说明）
- [x] 3.1.4 Dockerfile.base/mock: 支持 REGISTRY_MIRROR + PIP_INDEX_URL build-arg；run.sh 传递 build args

#### 3.2 mock server 路径兼容
- [x] 3.2.1 volcengine_mock.py: 增加 `/responses` 路径支持（兼容 apiBase 不含 /api/v3 的情况）
- [x] 3.2.2 runner.py: mock apiBase 设为 `MOCK_API_URL + "/api/v3"`（含路径前缀）

#### 3.3 runner.py 架构升级
- [x] 3.3.1 支持 initial_state_mapping 自定义目录映射（Type B 任务）
- [x] 3.3.2 支持 verify_script (pytest) 验证 + _run_pytest + _parse_pytest_stdout
- [x] 3.3.3 支持 snapshot_dirs 快照代码修改目录
- [x] 3.3.4 支持 config_overrides 覆盖默认配置
- [x] 3.3.5 支持 task type 标记（general / code_modification）
- [x] 3.3.6 verify_criterion 增加 "包含/contains" 通用规则

#### 3.4 task-002-token-usage-analytics 创建
- [x] 3.4.1 task.yaml：initial_state_mapping + verify_script + snapshot_dirs
- [x] 3.4.2 query.md：3 轮对话（需求→集成细节→验证）
- [x] 3.4.3 verify/test_analytics.py：5 组 pytest 测试（模块存在/内容验证/集成/兼容性/git）
- [x] 3.4.4 initial_state/project_code：从 git 8bc8589 提取 nanobot 源码（75 文件 + docs/），初始化为独立 git 仓库（2 commits）
- [x] 3.4.5 initial_state/memory/MEMORY.md + skills/dev-workflow/SKILL.md
- [x] 3.4.6 eval_prompt.md：5 维度评价（功能35%/质量25%/兼容20%/效率10%/规范10%）
- [x] 3.4.7 mocks/volcengine_mock.py：最小 health-check server（此任务不需要 mock API）

#### 3.5 工具与文档
- [x] 3.5.1 extract_git_snapshot.py：find-before + extract 命令
- [x] 3.5.2 DESIGN.md：Type A/B 架构图 + Provider 冲突解决方案 + Mock apiBase 约定
- [x] 3.5.3 DEPLOY.md：完整部署指南（含 volcengine 配置说明、国内网络配置）
- [x] 3.5.4 .env.example：分区域注释（必填/可选/volcengine/国内网络）

#### 3.6 打包与验证
- [x] 3.6.1 pack.sh：排除 eval-bench/.git，保留 task-002 project_code/.git
- [x] 3.6.2 验证打包产物：424K，390 entries，git 历史完整
- [x] 3.6.3 run.sh：加载 .env + 传递 build args + 构建 mock 镜像

#### 3.7 其他改进
- [x] 3.7.1 run.sh 加载 .env 文件（`set -a; source .env; set +a`）
- [x] 3.7.2 Dockerfile.base 安装 pytest-json-report（runner.py pytest JSON 报告依赖）
- [x] 3.7.3 Dockerfile.agent 支持 REGISTRY_MIRROR

### ISSUESv2 修复对照表

| # | 问题 | 修复方案 | 涉及文件 |
|---|------|---------|---------|
| 1 | docker-compose 未传 REGISTRY_MIRROR | run.sh 统一传 --build-arg；compose 改用 pre-built image | run.sh, docker-compose.yaml, Dockerfile.* |
| 2 | volcengine provider 冲突 → 404 | ~~CONFLICTING_PROVIDERS 检测 + custom provider 绕过~~ → Phase 4: mock 改用 `mock-volcengine` 名称，从根源避免冲突 | runner.py, task-001 query/config/task.yaml |
| 3 | .env.example 缺 volcengine 提示 | 增加分区域注释 + 必填说明 | .env.example |
| 4 | wheels 跨平台不兼容 | Dockerfile.base 支持 PIP_INDEX_URL；run.sh 传递 | Dockerfile.base, run.sh |
| (额外) | mock API /responses 路径 404 | mock 增加 /responses 路径支持 + apiBase 含 /api/v3 | volcengine_mock.py, runner.py |

### 完成时间
- 2026-03-04 01:25 开始
- 2026-03-04 02:10 全部完成

## Phase 4: Mock Provider 命名解耦 (2026-03-04)

### 背景
- Phase 3 的 Issue 2 修复方案（CONFLICTING_PROVIDERS + custom provider 绕过）过于复杂
- 根本原因是 mock 和 agent 使用相同的 provider key（都叫 `volcengine`）
- 更简洁的方案：给 mock 用一个专用名称（`mock-volcengine`），从根源上避免冲突

### 改动清单
- [x] 4.1 task-001 query.md: `providers.volcengine` → `providers.mock-volcengine`
- [x] 4.2 task-001 config_mock.json: key `volcengine` → `mock-volcengine`
- [x] 4.3 task-001 task.yaml: mock_services 增加 `provider_name: "mock-volcengine"`
- [x] 4.4 runner.py: 删除 CONFLICTING_PROVIDERS 机制，改为从 task.yaml mock_services[].provider_name 动态注册 mock provider
- [x] 4.5 DESIGN.md: 更新 Provider 冲突解决章节 → Mock Provider 命名约定
- [x] 4.6 DEPLOY.md: 删除 "runner.py 自动处理冲突" 说明
- [x] 4.7 评价环节简化：删除 evaluator.py，评价由执行任务的智能体统一完成
- [x] 4.8 更新 README.md / DESIGN.md 中评价相关描述
- [x] 4.9 DEVLOG.md: 记录 Phase 4

### 删除的代码
- `CONFLICTING_PROVIDERS = {"volcengine"}` 常量
- `_write_config()` 中 `has_conflict` 分支（~30 行）
- `custom` provider 绕过逻辑
- model 前缀特殊处理
- `evaluator.py` 整个文件（评价由智能体统一完成，不在平台内自动执行）

### 新增的机制
- task.yaml `mock_services[].provider_name` 字段声明 mock provider 名称
- runner.py `_write_config()` 遍历 mock_services 动态注册 mock provider
- 设计原则：mock provider 名称永远不与真实 provider 重名

### 完成时间
- 2026-03-04 18:10

## Phase 4.5: dev-workflow 规范补齐 + Git 初始化 (2026-03-04)

### 背景
- 项目此前无 git 仓库，缺少 docs/REQUIREMENTS.md 和 docs/ARCHITECTURE.md
- 按 dev-workflow 规范补齐文档结构并初始化 git

### 改动清单
- [x] 4.5.1 创建 docs/REQUIREMENTS.md — 需求文档（R1~R8 + 任务来源 + 演进路线）
- [x] 4.5.2 创建 docs/ARCHITECTURE.md — 架构设计（引用 DESIGN.md，精简版架构概览）
- [x] 4.5.3 更新 DESIGN.md：修复架构图（LLM Evaluator → Results + Verification）、删除重复 runner.py 行
- [x] 4.5.4 更新 .gitignore：排除嵌套 git 仓库的 .git 目录
- [x] 4.5.5 初始化 git 仓库，初始 commit `30d1bb0`（110 files, 17965 insertions）
- [x] 4.5.6 DEVLOG.md 记录本 Phase

### 完成时间
- 2026-03-04 22:49

### 当前 Git 状态
- 分支: `main`
- HEAD: `30d1bb0`
- 远程: 暂无（待推送至 GitHub）

---

## Phase 5: 测例修复 + Token 用量统计 + 文档更新 (2026-03-05)

### 背景
- 基于实际运行结果（20260304_231418 / 20260304_232825）反馈修复测例问题
- 给 runner.py 增加 token 用量统计功能（从容器内 analytics.db 查询）
- 检查 platform/DESIGN.md 文档是否与最新实现一致

### 任务清单

#### 5.1 修复 task-001 SKILL.md 验证失败
- [x] 5.1.1 runner.py verify_criterion: "存在且包含" 组合规则被通用 "包含" 分支错误匹配，路径解析为 "skills/doubao-search/SKILL.md 存在且" 导致文件找不到
- [x] 5.1.2 修复方案：将 task-001 特定规则移到通用规则之前；新增通用 "存在且包含" 组合规则处理

#### 5.2 修复 task-002 test_loop_has_chat_method 失败
- [x] 5.2.1 test_analytics.py: test_loop_has_chat_method 检查 `_chat_with_retry` / `_chat` / `chat_completion`，但原始 loop.py 中不存在这些方法（LLM 调用通过 `self.provider.chat()` 在 `_run_agent_loop` 中完成）
- [x] 5.2.2 修复方案：新增 `provider.chat` 和 `_run_agent_loop` 作为合法匹配模式

#### 5.3 runner.py 增加 token 用量统计
- [x] 5.3.1 collect_metrics 从容器内 analytics.db 查询本次运行的 token 消耗（按 session_key 过滤，fallback 到全表汇总）
- [x] 5.3.2 run_summary.json metrics 中增加 prompt_tokens / completion_tokens / total_tokens 字段
- [x] 5.3.3 main() 结束时输出 token 用量信息；run.sh 结果展示也增加 token 行

#### 5.4 检查 platform/DESIGN.md 文档准确性
- [x] 5.4.1 全面重写 DESIGN.md，对齐实际实现：
  - 执行流程：修正为 runner.py 实际的初始化→注入→收集流程
  - docker-compose 示例：替换为实际使用的 pre-built image + volume 映射
  - runner.py 描述：从虚构的 AgentRunner 类改为实际的函数式架构
  - 目录结构：移除不存在的 eval.py/reporter.py/task_loader.py，补充实际文件
  - 结果文件：修正为 run_summary.json / eval_result.md / pytest_report.json
  - Type B 架构图：analytics.py → usage/ 模块
  - 新增 Token 用量统计章节（analytics.db schema + metrics 输出格式）
  - 新增验证机制详细说明（声明式规则 + pytest）
  - 镜像分层：补充 mock 镜像说明

#### 5.5 Git 提交
- [x] 5.5.1 提交所有改动 — commit `82e5065`

### 完成时间
- 2026-03-05 00:15

---

## Phase 6: 架构解耦 + Skill 化 + 测例清单统一管理 (2026-03-05)

### 背景
- 将评测框架与测例解耦，支持外部测例目录
- 创建 4 个配套 Skill 支撑测例的发现→构造→维护→批量生产流程
- 将之前 README.md 中的散乱测例清单统一整合到 CASE_REGISTRY.md
- 扫描 3月2日 15:55 之后的新 session，补充 Batch 2 候选

### 任务清单

#### 6.1 需求文档
- [x] 6.1.1 REQUIREMENTS_PHASE6.md — 场景分析、解耦方案、4 个 Skill 设计、新增测例清单

#### 6.2 框架解耦
- [x] 6.2.1 run.sh: 新增 `--task-dir` 参数，支持外部测例路径
- [x] 6.2.2 docker-compose.yaml: 使用 `TASK_DIR_HOST` 环境变量替代硬编码路径
- [x] 6.2.3 TASK_SPEC.md: 测例规范文档（目录结构、字段说明、验证规则、分类列表）
- [x] 6.2.4 CASE_REGISTRY.md: 统一测例清单
  - 整合 Batch 1 (A1~A16 + B1~B21 + C1~C16) 共 53 个候选
  - 新增 Batch 2 (N1~N15) 共 15 个候选
  - 状态标记体系（📋候选/🔨构造中/✅已构造/❌放弃/🔄需更新）
  - 构造记录关联机制
  - 整体运转流程说明
- [x] 6.2.5 验证已有 task-001, task-002 兼容性（task.yaml 解析正常）

#### 6.3 Skill 1 — eval-session-scanner
- [x] 6.3.1 SKILL.md（含体系运转逻辑、4 Skill 协同流程图、组织级部署场景）
- [x] 6.3.2 scripts/scan_sessions.py（session 扫描脚本）
  - 支持 --since / --since-last-batch 时间范围
  - 支持 --format json/markdown 输出格式
  - 支持 --registry 去重 + 读取上次 Batch 时间
  - 自动排除过短 session
- [x] 6.3.3 对 3月2日 15:55 之后的 session 实际运行验证（17 个 session 命中）
- [x] 6.3.4 扫描结果保存为 docs/scan_batch2_raw.md

#### 6.4 Skill 2 — eval-task-builder
- [x] 6.4.1 SKILL.md（构造流程、敏感信息处理、框架改进反馈机制）

#### 6.5 Skill 3 — eval-framework-maintainer
- [x] 6.5.1 SKILL.md（工作流程、兼容性检查）

#### 6.6 Skill 4 — eval-task-batch-builder
- [x] 6.6.1 SKILL.md（子智能体编排、汇总报告格式）

#### 6.7 文档更新
- [x] 6.7.1 README.md: 精简为项目概览 + 指向 CASE_REGISTRY.md + 4 Skill 说明

#### 6.8 Git 提交
- [x] 6.8.1 提交所有改动

### 完成时间
- Phase 6.1~6.7: 2026-03-05 01:00
- Phase 6.8 (仓库重组): 2026-03-05 01:15

### Phase 6.8 仓库重组

- **Skill 入仓库**: 4 个 Skill 移入 `eval-bench/skills/`，workspace 中通过 symlink 引用
- **数据分离**: `CASE_REGISTRY.md` + `tasks/` + `results/` 移到并列的 `eval-bench-data/` 目录
  - eval-bench 是通用框架（可分发），eval-bench-data 是本地数据（不分发）
- **nanobot 源码机制**: 删除静态 `nanobot-src/`，run.sh 运行时自动从本地仓库同步到 `.nanobot-src-staging/`
  - 支持 `--nanobot-src` / `NANOBOT_SRC_PATH` / 默认路径自动检测
  - Dockerfile.agent 从 staging 目录 COPY
- **测例路径查找**: run.sh 先查 `eval-bench-data/tasks/`，再查 `./tasks/`
- **结果路径**: 输出到 `eval-bench-data/results/`

---

## Phase 7: 0307 批量评测反馈 — P0/P1 框架修复 (2026-03-09)

### 背景
- 0307 批量评测（36 测例）暴露了多个框架级问题，详见 `eval-bench-0307-results/FEEDBACK.md`
- FEEDBACK.md 按优先级分为 P0（首次运行必踩）、P1（国内用户必踩）、P2（功能增强）
- 本 Phase 修复全部 P0 + 部分 P1 问题

### 问题来源对照

| FEEDBACK# | 严重度 | 问题 | 本次修复 |
|-----------|--------|------|---------|
| 2.2 | P0 | Dockerfile.mock CMD 硬编码 `volcengine_mock.py` | ✅ P0-1 |
| 2.1 | P0 | docker-compose.yaml results volume 路径不匹配 | ✅ P0-2 |
| 2.4 | P0→P2 升级 | docker compose project name 未隔离 | ✅ P0-3 |
| 1.5 | P1 | .env.example 国内配置提示不醒目 | ✅ P1-1 |
| 1.3 | P1 | Dockerfile.base apt 源无 build-arg 支持 | ✅ P1-2 |
| 1.1 | P0 | run.sh 不自动加载 .env | Phase 5 已修（3.7.1） |
| 1.2 | P1 | Docker 镜像前缀 build-arg | Phase 3 已修（3.1.4） |
| 1.4 | P1 | nanobot 从 GitHub 安装超时 | Phase 6 已修（本地源码同步） |
| 2.3 | P2 | runner.py 否定断言支持 | 🔜 待做 |
| 2.5 | P2 | docker-compose.yaml env_file 路径 | 🔜 待做 |

### 任务清单

#### 7.1 P0-1: Dockerfile.mock CMD 通用化 — 约定 `start.sh` 入口
- [x] 7.1.1 `platform/Dockerfile.mock`: CMD 从 `["python3", "volcengine_mock.py"]` 改为 `["bash", "/mocks/start.sh"]`
  - 约定：各测例的 `mocks/` 目录必须提供 `start.sh` 作为统一启动入口
  - 比自动检测 .py 文件更严谨、更可控，测例可在 start.sh 中做任意初始化
- [x] 7.1.2 `platform/docker-compose.yaml`: 移除不再需要的 `MOCK_ENTRY` 环境变量
- [x] 7.1.3 `eval-bench-data/tasks/`: 为全部 37 个测例生成 `mocks/start.sh`
  - task-001, task-002: `exec python3 /mocks/volcengine_mock.py`
  - task-034: `exec python3 /mocks/api_gateway_mock.py`
  - 其余 34 个: `exec python3 /mocks/minimal_mock.py`

#### 7.2 P0-2: results volume 路径统一
- [x] 7.2.1 `platform/docker-compose.yaml`: results volume 从 `../results/${RUN_ID:-latest}` 改为 `${RESULTS_PATH:-../results/latest}`
- [x] 7.2.2 `run.sh`: RESULTS_PATH 变量添加 `export`，确保 docker compose 能读到

#### 7.3 P0-3: docker compose project name 隔离
- [x] 7.3.1 `run.sh`: `docker compose up` 添加 `-p "eval-${RUN_ID}"`
- [x] 7.3.2 `run.sh`: `docker compose down` 添加 `-p "eval-${RUN_ID}"`
- 并行运行多测例时容器互不干扰

#### 7.4 P1-1: .env.example 国内配置醒目提示
- [x] 7.4.1 `.env.example`: 国内镜像区域标题从 `[可选] 国内镜像加速` 改为 `⚠️ 国内用户必读：以下配置不设置会导致构建超时失败！`
- [x] 7.4.2 补充 Docker Hub 镜像、pip 镜像源、API 代理三项说明

#### 7.5 P1-2: Dockerfile.base apt 源 build-arg 支持
- [x] 7.5.1 `platform/Dockerfile.base`: 新增 `ARG APT_MIRROR=""`，在 `apt-get update` 前条件替换 apt 源
- [x] 7.5.2 `run.sh`: base image 构建命令添加 `--build-arg APT_MIRROR="${APT_MIRROR:-}"`

### 涉及文件

| 文件 | 改动项 |
|------|--------|
| `platform/Dockerfile.mock` | P0-1 (CMD → bash start.sh) |
| `platform/docker-compose.yaml` | P0-1 (移除 MOCK_ENTRY), P0-2 (RESULTS_PATH) |
| `run.sh` | P0-2 (export), P0-3 (-p 隔离), P1-2 (APT_MIRROR) |
| `.env.example` | P1-1 (醒目提示) |
| `platform/Dockerfile.base` | P1-2 (APT_MIRROR arg) |
| `eval-bench-data/tasks/*/mocks/start.sh` | P0-1 (37 个测例新增) |

### 设计决策

**P0-1 为什么选择约定 `start.sh` 而非自动检测 .py？**
- 自动检测依赖"目录下只有一个 .py"的假设，不够严谨
- `start.sh` 是显式约定，各测例完全控制启动逻辑（可做环境变量设置、多进程启动等）
- 框架只负责 `bash /mocks/start.sh`，简单可靠
- 新增测例只需在 `mocks/` 下提供 `start.sh`，规范写入 TASK_SPEC.md

### 完成时间
- 2026-03-09 14:50

---

## Phase 8: P2 验证逻辑统一 — 废弃 success_criteria，统一 pytest verify_script (2026-03-09)

### 背景
- 0307 批量评测反馈的 P2 项：验证逻辑改进
- runner.py 原有两套验证机制：success_criteria（声明式自然语言规则）+ verify_script（pytest 脚本）
- 声明式规则解析器 `verify_criterion()` 约 120 行，维护成本高、覆盖场景有限
- 决策：废弃 success_criteria，统一使用 pytest verify_script

### 任务清单

#### 8.1 框架侧 (eval-bench)
- [x] 8.1.1 runner.py: 删除 `verify_criterion()` 函数（~120 行自然语言解析器）
- [x] 8.1.2 runner.py: 重写 `run_verification()`，仅保留 verify_script 路径
  - success_criteria 存在时打 WARNING 日志但不执行
  - verify_script 不存在时打 WARNING 并返回空 results
- [x] 8.1.3 runner.py: `_run_pytest()` 补充环境变量（RESULTS_DIR、TASK_ID、TASK_NAME）
  - PROJECT_DIR 在无 initial_state_mapping 时也尝试从常见路径设置
- [x] 8.1.4 docker-compose.yaml: agent-runner 添加 `env_file: - ../.env`

#### 8.2 测例侧 — 27 个同时有 success_criteria + verify_script 的测例
- [x] 8.2.1 批量删除 task.yaml 中的 success_criteria 字段
  - task-002, task-004, task-006~task-017, task-019~task-024, task-026~task-027, task-032~task-036
  - verify_script 字段保留不变

#### 8.3 测例侧 — 6 个仅有 success_criteria 的测例（新建 verify_script）
- [x] 8.3.1 task-001: verify/test_doubao_search.py（6 个测试：SKILL.md frontmatter、脚本存在可执行、三子命令、无硬编码 key、mock JSON、REQUIREMENTS.md）
- [x] 8.3.2 task-003: verify/test_dev_workflow.py（5 个测试：SKILL.md frontmatter、新功能开发、分支策略、开发纪律、MEMORY.md 引用）
- [x] 8.3.3 task-005: verify/test_email_probe.py（2 个测试：无虚假邮件操作、明确表示无邮件能力；从 turns.json/trajectory.jsonl 读取 agent 回复）
- [x] 8.3.4 task-025: verify/test_memory_reorg.py（6 个测试：MEMORY.md 存在+内容、PROJECT_WEBCHAT.md 存在+Phase、PROJECT_NANOBOT_CORE.md 存在+Phase）
- [x] 8.3.5 task-028: verify/test_gateway_diagnosis.py（3 个测试：报告存在、包含诊断、包含建议）
- [x] 8.3.6 task-031: verify/test_thoughts_to_doc.py（4 个测试：ROADMAP 存在、架构、Provider、安全）

#### 8.4 文档更新
- [x] 8.4.1 TASK_SPEC.md: success_criteria 标记为 deprecated，verify_script 标记为必须
  - 更新验证字段说明、验证规则语法、环境变量表、示例
- [x] 8.4.2 DEVLOG.md: 添加 Phase 8 记录

### 涉及文件

| 仓库 | 文件 | 改动 |
|------|------|------|
| eval-bench | platform/runner.py | 删除 verify_criterion()、重写 run_verification()、_run_pytest() 增强 |
| eval-bench | platform/docker-compose.yaml | 添加 env_file |
| eval-bench | docs/TASK_SPEC.md | success_criteria deprecated、verify_script 必须 |
| eval-bench | docs/DEVLOG.md | Phase 8 记录 |
| eval-bench-data | 27 个 task.yaml | 删除 success_criteria 字段 |
| eval-bench-data | 6 个 verify/*.py | 新建 pytest 验证脚本 |
| eval-bench-data | 6 个 task.yaml | 替换 success_criteria 为 verify_script |

### 设计决策

**为什么废弃 success_criteria 而非增强？**
- 自然语言解析器本质上是 pattern matching，覆盖场景有限
- 每新增一种验证模式就要修改 runner.py，维护成本高
- pytest 脚本可以做任意复杂验证（文件检查、代码分析、数据库查询、session 分析等）
- 统一为 pytest 后，verify 脚本可以独立测试和调试

### 完成时间
- 2026-03-09 15:24

---

## 🔜 待办

- [ ] 推送至 GitHub 仓库 (`zhangxc11/nanobot-eval-bench`)
- [ ] Skill 2 脚本实现 + 实际构造 1 个 A 类测例验证
- [ ] Skill 3 兼容性检查脚本实现
- [ ] Skill 4 子智能体编排实现
- [ ] 批量构造 A 类测例
- [ ] 实际端到端运行验证（Docker 环境）

---

## Phase 9: P3 功能增强 — SESSION_ID 动态化 + dry-run + 批量运行 (2026-03-09)

### 背景
- 0307 批量评测反馈的 P3 功能增强项
- SESSION_ID 硬编码导致 analytics.db token 统计无法按 task 区分
- 缺少快速验证测例配置的方式（每次都要跑完整 agent）
- 缺少批量运行多个测例的入口脚本

### 任务清单

#### 9.1 P3-1: SESSION_ID 动态化
- [x] 9.1.1 runner.py: SESSION_ID 从硬编码 `"eval:task-001"` 改为 `f"eval:{task_id}"`
  - 保留模块级默认值（兼容 collect_metrics 中的引用）
  - 在 main() 中加载 task.yaml 后通过 `global SESSION_ID` 重新赋值
  - main() 中新增 Session ID 日志输出

#### 9.2 P3-5: `--dry-run` 模式
- [x] 9.2.1 runner.py: 新增 `_parse_args()` 函数，支持 `--dry-run` 命令行参数和 `DRY_RUN=1` 环境变量
- [x] 9.2.2 runner.py: main() 中 dry-run 模式下：
  - 跳过 AGENT_API_KEY 检查
  - 正常加载 task.yaml 和 query.md
  - 正常初始化 workspace（复制 initial_state）
  - 跳过 agent turns（填充 `[DRY-RUN: agent execution skipped]` 占位）
  - 正常执行 verification（跑 pytest）
  - 正常收集 metrics 和输出 run_summary.json
  - run_summary.json 中新增 `dry_run` 字段
- [x] 9.2.3 run.sh: 新增 `--dry-run` 参数，传递 DRY_RUN 环境变量给 docker compose
- [x] 9.2.4 docker-compose.yaml: agent-runner 环境变量新增 `DRY_RUN=${DRY_RUN:-}`

#### 9.3 P3-6: 批量运行入口 `batch_run.sh`
- [x] 9.3.1 `batch_run.sh`（仓库根目录），支持：
  - 参数方式：task ID 列表、`--glob PATTERN`、`--all`
  - `--results-dir` 指定结果根目录（默认 `eval-bench-data/results/batch_<timestamp>`）
  - `--dry-run` 传递给 runner.py
  - `--continue` 断点续跑（跳过已有 run_summary.json 的测例）
  - 首个测例运行前自动构建/同步 Docker 镜像
  - 每个测例独立 docker compose project（`eval-batch-*`），运行后自动清理
  - 结果存到 `{results_dir}/{task_id}/`
  - 运行完成后输出汇总表格（task_id, status, verification, time）
  - 保存 `batch_summary.json` 到结果根目录

### 涉及文件

| 文件 | 改动 |
|------|------|
| `platform/runner.py` | P3-1 (SESSION_ID 动态化), P3-5 (_parse_args + dry-run 逻辑) |
| `platform/docker-compose.yaml` | P3-5 (DRY_RUN 环境变量) |
| `run.sh` | P3-5 (--dry-run 参数 + export DRY_RUN) |
| `batch_run.sh` | P3-6 (新建，批量运行入口) |

### 设计决策

**P3-1: 为什么用 global 而非函数参数？**
- SESSION_ID 被 `collect_metrics()` 引用来查询 analytics.db
- 改为函数参数需要修改多个函数签名，改动面大
- 使用 `global SESSION_ID` 在 main() 中赋值，最小改动，且模块级默认值保留兼容性

**P3-5: 为什么 dry-run 仍执行 verification？**
- dry-run 的核心用途是验证测例配置是否正确（task.yaml、initial_state、verify_script）
- 如果跳过 verification，就无法发现 verify_script 本身的问题
- agent 未执行时 verification 大概率会 FAIL，但这正是预期行为——确认 verify_script 能正常运行

**P3-6: batch_run.sh vs 循环调用 run.sh？**
- 直接循环调用 run.sh 会每次重建镜像、重新同步源码，浪费时间
- batch_run.sh 只在首个测例前构建一次镜像，后续测例直接运行
- 独立 docker compose project name 避免并行冲突
- `--continue` 模式支持断点续跑，适合大批量运行

### 完成时间
- 2026-03-09 16:25

---

## Phase 10: R10.6 — task.yaml 显式 `project_dir` 字段 (2026-03-12)

### 背景
- task-032 评测反馈：mapping 用 `nanobot_repo` 而非 `project_code` 作为 key，runner.py fallback 指向错误的父目录，27/30 测试误判 FAIL
- 方案 B：task.yaml 新增顶层 `project_dir` 字段，显式声明项目目录路径

### 任务清单

#### 10.1 runner.py 修改
- [x] 10.1.1 `_run_pytest()`: PROJECT_DIR 设置逻辑改为三级优先级
  - 优先级 1: `task.get("project_dir")` → `EVAL_HOME / project_dir`
  - 优先级 2: `mapping["project_code"]` → `EVAL_HOME / mapping["project_code"]`（向后兼容）
  - 优先级 3: fallback 目录探测（原逻辑不变）
- [x] 10.1.2 `collect_metrics()`: count_dirs 逻辑同步更新，增加 `project_dir` 字段优先级
- [x] 10.1.3 文件头注释更新：Type B 说明中提及 `project_dir` 字段

#### 10.2 文档更新
- [x] 10.2.1 TASK_SPEC.md: task.yaml 字段说明新增 `project_dir`，环境变量表更新
- [x] 10.2.2 eval-task-builder SKILL.md: 更新 §5.8 说明框架已支持 `project_dir` 字段

#### 10.3 兼容性验证
- [x] 10.3.1 已有测例兼容性检查：所有已有 task.yaml 无 `project_dir` 字段，走原逻辑不受影响
- [x] 10.3.2 task-032 验证：为其 task.yaml 添加 `project_dir` 字段，确认 PROJECT_DIR 正确

#### 10.4 Git 提交
- [x] 10.4.1 eval-bench 仓库提交 → `a040996` + `3215419`，已推送
- [x] 10.4.2 eval-bench-data 仓库提交 → `553afd3`（本地，远程仓库待确认）

### 完成时间
- 2026-03-12 15:38

### 涉及文件

| 文件 | 改动 |
|------|------|
| `platform/runner.py` | PROJECT_DIR 设置 + count_dirs 逻辑 + 头注释 |
| `docs/TASK_SPEC.md` | 新增 project_dir 字段说明 |
| `docs/REQUIREMENTS.md` | R10.6 已记录 |
| `docs/DEVLOG.md` | Phase 10 |
| `eval-task-builder SKILL.md` | §5.8 更新 |
| `eval-bench-data: task-032 task.yaml` | 添加 project_dir 字段 |
