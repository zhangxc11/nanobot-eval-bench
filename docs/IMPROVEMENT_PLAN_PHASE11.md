# Phase 11: 0312 评测反馈改进计划

> 来源：0312 第二批评测（task-037~060，24 测例）反馈分析
> 创建时间：2026-03-13

## 总览

24 测例中 8 个 FAIL，归因拆解：
- 框架 bug（PROJECT_DIR 路径）：task-039, task-041
- 测例设计问题（验证绑定实现）：task-037, task-043, task-048, task-051
- 环境缺失：task-040（Node.js）, task-060（pytest-asyncio）
- Agent 真实能力不足：task-052（部分）

排除框架和测例问题后，Agent 真实失败率仅 ~6%。

---

## P0-1: PROJECT_DIR 路径机制重设计

### 问题根因

当前 `project_dir` 和 `initial_state_mapping` 是两个独立概念：
- `initial_state_mapping`: `{src_key: dest_path}` — src_key 是 initial_state/ 下的目录名，dest_path 是容器内目标路径
- `project_dir`: 相对于 EVAL_HOME 的路径，设置 PROJECT_DIR 环境变量

**歧义点**：构造者容易把 mapping 的 key（如 `nanobot_core`）误写为 project_dir 值，
而正确值应该是 mapping 的 value（如 `.nanobot/workspace/nanobot_core`）。

### 新设计：消除歧义，唯一路径设置方式

**核心原则**：`project_dir` 的值 = `initial_state_mapping` 中某个 value 的值。两者语义统一。

**task.yaml 写法（唯一正确方式）**：
```yaml
# project_dir 必须是相对于 EVAL_HOME 的完整路径
# 必须与 initial_state_mapping 中某个 value 一致或是其子路径
project_dir: ".nanobot/workspace/nanobot_core"

initial_state_mapping:
  "nanobot_core": ".nanobot/workspace/nanobot_core"
```

**废弃的路径设置方式**：
- ❌ `project_dir: "nanobot_core"` — 不允许只写 mapping key
- ❌ `project_code` mapping key 自动推导 — 废弃
- ❌ fallback 目录探测 — 废弃

**runner.py 改动**：
1. `project_dir` 字段为 **唯一** 设置 PROJECT_DIR 的方式
2. 废弃 `project_code` key 推导和 fallback 探测
3. 新增容错：如果 `project_dir` 的路径不存在，检查是否是 mapping key，自动修正 + WARNING
4. `collect_metrics()` 同步简化

**质检要求**：
- 所有 code_modification 类型测例 **必须** 有 `project_dir` 字段
- `project_dir` 值 **必须** 以 `.nanobot/workspace/` 开头
- `project_dir` 值 **必须** 与某个 mapping value 一致或是其子路径
- verify 脚本的 PROJECT_DIR fallback 值 **必须** 与 task.yaml project_dir 一致

### 受影响测例刷新清单

需要修改 project_dir 的（错误值）：
- [x] task-039: `nanobot_core` → `.nanobot/workspace/nanobot_core`
- [x] task-041: `taskrunner_project` → `.nanobot/workspace/taskrunner_project`

需要新增 project_dir 的（当前缺失）：
- [x] task-002: 添加 `project_dir: ".nanobot/workspace/project/nanobot"`
- [x] task-004: 添加 `project_dir: ".nanobot/workspace/project"`
- [x] task-011: 添加 `project_dir: ".nanobot/workspace/project/web-chat"`
- [x] task-012: 添加 `project_dir: ".nanobot/workspace/web-chat"`
- [x] task-013: 添加 `project_dir: ".nanobot/workspace/project"`
- [x] task-014: 添加 `project_dir: ".nanobot/workspace/web-chat"`
- [x] task-015: 添加 `project_dir: ".nanobot/workspace/web-chat"`
- [x] task-017: 添加 `project_dir: ".nanobot/workspace/project/nanobot"`
- [x] task-018: 添加 `project_dir: ".nanobot/workspace/project/nanobot"`
- [x] task-020: 添加 `project_dir: ".nanobot/workspace/project/nanobot"`
- [x] task-021: 添加 `project_dir: ".nanobot/workspace/web-chat"`
- [x] task-023: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-024: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-035: 添加 `project_dir: ".nanobot/workspace/project/nanobot"`
- [x] task-036: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-037: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-038: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-040: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-043: 需确认 verify 脚本是否用 PROJECT_DIR
- [x] task-046: 非 code_modification，跳过
- [x] task-047: 已有正确 project_dir
- [x] task-050: 已有正确 project_dir

### 进展
- [x] 11.1.1 runner.py PROJECT_DIR 逻辑简化 + 容错
- [x] 11.1.2 TASK_SPEC.md 更新 project_dir 说明
- [x] 11.1.3 eval-task-builder skill 文档更新
- [x] 11.1.4 全量测例 project_dir 刷新
- [x] 11.1.5 质检脚本 project_dir 校验
- [x] 11.1.6 Git 提交 eval-bench + eval-bench-data

---

## P0-2: Docker 镜像环境预装

### 2a. Dockerfile.base 预装 Node.js + pytest-asyncio

task-040 浪费 568s（65% 总耗时）安装 Node.js，task-060 因缺 pytest-asyncio 部分失败。

改动：
```dockerfile
# Node.js 20.x LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 评测框架依赖（增加 pytest-asyncio）
RUN pip install --no-cache-dir pytest pyyaml pytest-json-report pytest-asyncio
```

### 2c. mock-api start.sh 空服务 placeholder 固化

当前 batch_232014 临时修复了 mock-api 空服务退出问题。需要固化到框架的 mock 模板中：
- `mocks/start.sh` 检测无 mock 服务配置时，启动 minimal placeholder
- 更新 TASK_SPEC.md 中的 mock 模板说明

### 进展
- [x] 11.2.1 Dockerfile.base 添加 Node.js + pytest-asyncio
- [x] 11.2.2 mock start.sh 模板更新
- [x] 11.2.3 TASK_SPEC.md mock 说明更新
- [x] 11.2.4 Git 提交

---

## P0-3: task-037 重构

### 问题

非 session 扫描来源，agent 自行构造，存在致命设计缺陷：
1. query.md 直接给出根因和三步修复方案（task_keeper 回调参数）
2. verify 脚本 16 个检查项全部用 AST/正则检查特定变量名，不接受等价方案
3. 零功能性验证

### 重构方向

- query.md 只保留现象描述，删除根因和实现方案
- verify 改为功能验证（模拟 GC → 断言 task 存活）
- 不检查变量名/参数名
- 权重调整：诊断 30% + 功能修复 40% + 内存安全 15% + 兼容 15%

### 进展
- [x] 11.3.1 重写 query.md
- [x] 11.3.2 重写 verify 脚本
- [x] 11.3.3 更新 task.yaml eval_dimensions
- [x] 11.3.4 Git 提交

---

## P1-4: task-043/048/051 验证方法改进

### 通用原则

> 优先验证行为，其次验证结构。能用"运行代码/检查输出"验证的，不用"grep 代码模式"。

### task-043（Session 命名持久化）

失败 2 项绑定了特定函数名。改为：
- 检查 rename 后 session_names.json 是否被写入（行为验证）
- 检查 names 文件优先级高于 JSONL metadata（行为验证）

### task-048（斜杠命令回填）

失败 3 项只在 messageStore.ts 搜索。改为：
- 放宽 grep 范围到 messageStore.ts + ChatInput.tsx + 相关组件
- 接受多种实现模式（setDraft / restoreInput / value= 等）

### task-051（System 消息展示）

失败 5 项只接受 `system-inject` 命名。改为：
- 接受 `system-inject|system-remote|system-message|system-notify` 等变体
- 核心检查：Message 类型定义包含 system 角色 + 有对应渲染组件

### 进展
- [x] 11.4.1 task-043 verify 改进
- [x] 11.4.2 task-048 verify 改进
- [x] 11.4.3 task-051 verify 改进
- [x] 11.4.4 Git 提交

---

## P1-5: 质检脚本 + verify_notes 标注

### 质检脚本增强

新增自动校验规则：
- project_dir 格式校验（必须以 `.nanobot/workspace/` 开头）
- project_dir 与 mapping value 一致性校验
- verify 脚本 PROJECT_DIR fallback 与 task.yaml 一致性校验

### verify_notes 标注

在 task.yaml 中支持 `verify_notes` 字段，标记验证可能与等价方案冲突的测例。
生成报告时自动标注为"需人工审查"。

### 进展
- [x] 11.5.1 质检脚本编写
- [x] 11.5.2 verify_notes 机制（可选，视时间）
- [x] 11.5.3 Git 提交
