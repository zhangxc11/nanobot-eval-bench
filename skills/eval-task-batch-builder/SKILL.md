# eval-task-batch-builder — 批量测例构造

利用子智能体（spawn），根据 CASE_REGISTRY.md 中的候选清单批量构造多个测例。

---

## 职责

```
输入: CASE_REGISTRY.md 中的候选清单 + 过滤条件
输出: 多个测例目录 + 汇总报告 + 框架改进反馈汇总
```

## 工作流程

```
1. 读取 CASE_REGISTRY.md → 筛选目标测例（按分类/ID/状态过滤）
2. 对每个目标测例:
   a. spawn 子智能体
   b. 子智能体调用 eval-task-builder 构造测例
   c. 收集构造结果和框架改进反馈
3. 汇总所有结果
4. 如有框架改进反馈 → 合并去重 → 供 eval-framework-maintainer 处理
5. 更新 CASE_REGISTRY.md 中所有已构造测例的状态
```

## 使用方式

### 批量构造 A 类测例

> 请使用 eval-task-batch-builder skill，批量构造所有 A 类候选测例。

### 构造指定范围

> 请使用 eval-task-batch-builder skill，构造 N6, N10, N11, N12, N13 这 5 个测例。

### 参数

| 参数 | 说明 |
|------|------|
| 分类过滤 | 只构造 A 类 / B 类 / 指定 ID 列表 |
| 并发数 | 同时 spawn 的子智能体数量（默认 3） |
| 输出目录 | 测例目录的父目录 |
| 跳过已构造 | 跳过状态为 "✅ 已构造" 的测例（默认 true） |

## 子智能体任务模板

每个子智能体收到的任务描述：

```
请使用 eval-task-builder skill，构造候选测例 {ID}（{任务名}）。

来源 session: {session_file}
输出目录: {output_dir}
测例规范: {TASK_SPEC.md 路径}
CASE_REGISTRY: {CASE_REGISTRY.md 路径}

构造完成后：
1. 验证测例完整性
2. 如有框架改进需求，输出到 {feedback_dir}/{ID}_feedback.md
3. 更新 CASE_REGISTRY.md 中 {ID} 的状态
```

## 汇总报告格式

```markdown
# 批量构造报告

构造时间: YYYY-MM-DD HH:MM
目标测例: N 个
成功: X 个
失败: Y 个
框架改进建议: Z 条

## 详情

| ID | 任务名 | 结果 | 测例目录 | 备注 |
|----|--------|------|---------|------|
| A2 | calendar-reader | ✅ | task-003-calendar-reader | |
| A3 | dev-workflow | ✅ | task-004-dev-workflow | |
| A6 | insight-dashboard | ❌ | - | 需要 mock 复杂外部 API |

## 框架改进建议汇总

1. [来自 A6] runner.py 需要支持多端口 mock 服务
2. [来自 A8] 需要图片文件作为 initial_state 的支持
```
