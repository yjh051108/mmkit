# 工作流编排规则

> 本文档供 agent 阅读。描述数模竞赛工作流 CLI（`mm_flow.py`）的 DAG 推进、检查点、zombie 检测和全部子命令的参数与返回格式。
>
> 源文件：`orchestrator/mm_flow.py`

---

## 1. DAG 推进规则

### 1.1 顺序执行，禁止跳步

- 工作流由模板（`workflow_templates.json`）中的 `sub_steps` 数组定义，**严格按数组下标顺序执行**。
- 每个 step 对应一个子 skill，拥有独立的 `skill_name` / `display_name` / `output_files` / `primary_output` / `has_checkpoint` 字段。
- step 的状态机：`pending` → `running` → `completed`（或 `waiting_checkpoint` → `completed`）。
- **不能跳步**：只有当前 step 完成并通过健康检查后，才能推进到下一步。

### 1.2 complete 触发健康检查

- agent 执行完当前 step 的产物后，调用 `complete` 命令。
- `complete` 内部自动调用 `health_check.check_step(workspace, skill_name)`。
- 健康检查 **不通过** → 返回 `{"health_failed": true, "issues": [...], "checks": [...]}`，step 不推进，agent 需修复产物后重新 `complete`。
- 健康检查 **通过** → 进入检查点分支或自动推进（见下文）。

### 1.3 自动续接规则

- **无检查点的 step**（`has_checkpoint=false`）：健康检查通过后，`complete` 自动调用 `advance_step` 推进到下一步。
- agent **不需要手动调用 `next`** —— `complete` 的返回值直接包含下一个 step 的信息。
- 如果已是最后一步，返回 `{"finished": true}`。

### 1.4 检查点规则

- **有检查点的 step**（`has_checkpoint=true`）：健康检查通过后，step 状态变为 `waiting_checkpoint`，工作流暂停。
- agent 需要提示用户审查产物，然后调用 `resolve` 命令决策：

| 决策 | 行为 |
|------|------|
| `approve` | step 标记为 `running` → `advance_step` 推进到下一步 |
| `reject` | step 回退为 `pending`（重做当前 step），记录"驳回反馈"日志 |
| `modify` | 同 `reject`（回退重做），但日志标签为"修改意见"，用于记录用户的修改要求 |

- `reject` / `modify` 时可通过 `--feedback` 传入反馈意见，agent 应据此指导重做。
- 重做后 step 状态为 `pending`，再次调用 `complete` 会先标记为 `running` 再跑健康检查。

### 1.5 zombie 检测

- 心跳超时阈值：**60 秒**（`_ZOMBIE_THRESHOLD = 60`）。
- `status` 命令检查 `last_heartbeat` 与当前 UTC 时间的差值。
- 超过 60 秒且工作流状态不是 `completed` / `failed` → 标记为 `zombie`，并更新数据库状态。
- zombie 工作流需调用 `resume` 命令恢复：重置状态为 `running`，更新心跳，返回当前活跃 step。

---

## 2. CLI 命令完整参考

所有命令输出结构化 JSON 到 stdout，异常信息输出到 stderr。退出码 0 表示成功，1 表示异常。

脚本路径：`orchestrator/mm_flow.py`

### 2.1 start — 启动工作流

```
python mm_flow.py start <template_name> [options]
```

**参数：**

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `template_name` | 是 | - | 模板名称，如 `comp_cumcm` / `comp_mcm` / `paper_from_assets` |
| `--workspace` | 是 | - | 工作区目录路径 |
| `--language` | 是 | - | 语言 `zh` / `en` |
| `--competition` | 是 | - | 竞赛 ID |
| `--problem` | 是 | - | 研究问题描述 |
| `--tools` | 否 | `python` | 工具 `python` / `matlab` |

**返回格式（成功）：**

```json
{
  "workflow_id": "<UUID>",
  "first_step": {
    "skill_name": "comp-prob-analysis",
    "display_name": "赛题分析",
    "output_files": ["PROBLEM_ANALYSIS.md"],
    "primary_output": "PROBLEM_ANALYSIS.md",
    "has_checkpoint": false
  }
}
```

**返回格式（缺必填字段）：**

```json
{
  "missing": ["workspace", "problem"]
}
```

**返回格式（模板不存在）：**

```json
{
  "error": "template not found",
  "available": ["comp_cumcm", "comp_mcm", ...]
}
```

**副作用：**
- 创建工作流记录 + 全部 step 行（初始为 `pending`，第 0 步自动设为 `running`）。
- 复制共享工具文件到工作区 `_utils/` 目录（`figure_check.py` / `plot_utils.py` / `stats_utils.py` / `drawio_check.py` / `figure_exemplars.md` / `figure_style_guide.md` / `FIGURE_QUICK_REF.md` / `get_recipe.py` / `figure_recipes_*.md`）。
- 更新心跳 + 写 info 日志。

---

### 2.2 next — 获取当前待执行步骤

```
python mm_flow.py next <workflow_id>
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |

**返回格式（有待执行 step）：**

```json
{
  "skill_name": "comp-modeling",
  "display_name": "建模",
  "output_files": ["MODELING_REPORT.md"],
  "primary_output": "MODELING_REPORT.md",
  "has_checkpoint": false,
  "step_index": 1
}
```

**返回格式（工作流已完成）：**

```json
{
  "finished": true
}
```

**返回格式（当前 step 未完成）：**

```json
{
  "error": "current step not completed, run complete first"
}
```

**返回格式（有待处理检查点）：**

```json
{
  "error": "current step waiting for checkpoint, run resolve"
}
```

---

### 2.3 complete — 完成当前步骤

```
python mm_flow.py complete <workflow_id>
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |

**返回格式（健康检查通过 + 无检查点 + 自动推进）：**

```json
{
  "skill_name": "comp-code",
  "display_name": "编程实现",
  "output_files": ["RESULTS.md"],
  "primary_output": "RESULTS.md",
  "has_checkpoint": false,
  "step_index": 2
}
```

**返回格式（健康检查通过 + 有检查点 → 暂停等待决策）：**

```json
{
  "checkpoint": true,
  "type": "user_confirm",
  "message": "请审查产物后决定是否继续",
  "step_index": 1
}
```

**返回格式（健康检查失败）：**

```json
{
  "health_failed": true,
  "issues": ["主输出过小: PROBLEM_ANALYSIS.md (200 字节 < 1500)"],
  "checks": [
    {
      "name": "primary_output",
      "pass": false,
      "detail": "主输出过小: PROBLEM_ANALYSIS.md (200 字节 < 1500)"
    }
  ]
}
```

**返回格式（已是最后一步）：**

```json
{
  "finished": true
}
```

---

### 2.4 resolve — 处理检查点决策

```
python mm_flow.py resolve <workflow_id> --decision <approve|reject|modify> [--feedback "<意见>"]
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |
| `--decision` | 是 | `approve` / `reject` / `modify` |
| `--feedback` | 否 | 反馈意见（reject / modify 时记录到日志） |

**返回格式（approve → 推进到下一步）：**

```json
{
  "skill_name": "comp-code",
  "display_name": "编程实现",
  "output_files": ["RESULTS.md"],
  "primary_output": "RESULTS.md",
  "has_checkpoint": false,
  "step_index": 2
}
```

**返回格式（approve → 已是最后一步）：**

```json
{
  "finished": true
}
```

**返回格式（reject / modify → 回退重做）：**

```json
{
  "redo": true,
  "step_index": 1,
  "feedback": "模型假设不够充分，需补充"
}
```

---

### 2.5 status — 查询工作流状态

```
python mm_flow.py status <workflow_id>
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |

**返回格式：**

```json
{
  "workflow_id": "<UUID>",
  "status": "running",
  "current_step": {
    "skill_name": "comp-code",
    "display_name": "编程实现",
    "output_files": ["RESULTS.md"],
    "primary_output": "RESULTS.md",
    "has_checkpoint": false,
    "step_index": 2
  },
  "last_heartbeat": "2026-07-22 10:30:00",
  "zombie": false
}
```

**状态值：** `running` / `waiting_checkpoint`（通过 current_step 反映）/ `zombie` / `completed` / `failed`

**zombie 检测逻辑：** `last_heartbeat` 距当前 UTC 时间超过 60 秒，且状态非 `completed` / `failed` → `zombie: true`，同时更新数据库状态为 `zombie`。

---

### 2.6 resume — 恢复 zombie 工作流

```
python mm_flow.py resume <workflow_id>
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |

**返回格式：**

```json
{
  "skill_name": "comp-code",
  "display_name": "编程实现",
  "output_files": ["RESULTS.md"],
  "primary_output": "RESULTS.md",
  "has_checkpoint": false,
  "step_index": 2
}
```

**副作用：** 状态重置为 `running`，更新心跳，写 info 日志"工作流从 zombie 恢复"。

---

### 2.7 health — 对所有已完成步骤跑健康检查

```
python mm_flow.py health <workflow_id>
```

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `workflow_id` | 是 | 工作流 ID |

**返回格式：**

```json
{
  "steps": [
    {
      "step_index": 0,
      "skill_name": "comp-prob-analysis",
      "pass": true,
      "issues": []
    },
    {
      "step_index": 1,
      "skill_name": "comp-modeling",
      "pass": false,
      "issues": ["主输出过小: MODELING_REPORT.md (500 字节 < 2000)"]
    }
  ],
  "all_pass": false
}
```

**说明：** 仅检查状态为 `completed` 的 step。`all_pass` 为所有 step 都通过的总体标志。

---

## 3. 典型工作流时序

```
agent                          mm_flow.py
  │
  ├── start comp_cumcm ──────────→ 创建工作流，返回 first_step
  │
  │   (执行 step 0 产物)
  │
  ├── complete ──────────────────→ 健康检查 → 通过 → 自动推进 → 返回 step 1
  │
  │   (执行 step 1 产物)
  │
  ├── complete ──────────────────→ 健康检查 → 通过 → has_checkpoint → 返回 checkpoint
  │
  │   (提示用户审查)
  │
  ├── resolve --decision approve ─→ 推进 → 返回 step 2
  │
  │   (执行 step 2 产物)
  │
  ├── complete ──────────────────→ 健康检查 → 失败 → 返回 health_failed
  │
  │   (修复产物)
  │
  ├── complete ──────────────────→ 健康检查 → 通过 → 自动推进 → 返回 step 3
  │
  │   ... (重复直到 finished)
  │
  └── complete ──────────────────→ {"finished": true}
```

---

## 4. agent 行为约束

1. **不要跳过 complete**：每个 step 的产物完成后必须调 `complete`，由健康检查把关。
2. **检查点必须 resolve**：`complete` 返回 `checkpoint: true` 时，工作流已暂停，必须等用户决策后调 `resolve`。
3. **reject/modify 后需重做**：step 回退为 `pending`，agent 需重新执行产物再 `complete`。
4. **健康检查失败后需修复**：不要反复调 `complete` 碰运气，先根据 `issues` 修复产物。
5. **长时间运行注意心跳**：如果 step 执行可能超过 60 秒，注意工作流可能被标记 zombie，需 `resume` 恢复。
6. **不要手动调 next 推进**：`complete` 在无检查点时会自动推进，`next` 仅用于查询当前待执行 step。
