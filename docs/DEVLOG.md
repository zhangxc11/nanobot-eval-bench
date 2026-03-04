# eval-bench 开发日志

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

## 🔜 待办

- [ ] 推送至 GitHub 仓库 (`zhangxc11/nanobot-eval-bench`)
- [ ] 新增更多评测任务（从 A2~A16 / B 类中选取）
- [ ] 实际端到端运行验证（Docker 环境）
- [ ] 报告生成器 (reporter.py)
