---
name: mmkit
description: "数学建模竞赛全流程 skills 包。通过 orchestrator/mm_flow.py CLI 驱动赛题分析→建模→编码→图表→论文→编译的完整流水线。每个子 skill 独立可用。Use when user says '数学建模', '竞赛', '跑国赛', '跑美赛', 'CUMCM', 'MCM', 'comp_cumcm', 'comp_mcm'."
argument-hint: [competition-type-and-problem]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent
---

# 数学建模竞赛 Skills 包索引

本目录是数学建模竞赛（国赛 CUMCM / 美赛 MCM）全流程的 skills 包：通过 `orchestrator/mm_flow.py` CLI 驱动「赛题分析 → 建模 → 编码 → 图表 → 论文 → 编译」的完整流水线，按步推进、健康检查、一致性检查、检查点确认，直至产出可提交的 PDF。每个子 skill 平级独立，可单独使用。

## 按需加载规则

`skills/` 目录下有 70 个平级子 skill。agent 只在 `mm_flow next` 返回 `skill_name` 后读取对应的 `skills/<skill_name>/SKILL.md`，不要预读、不要扫描全目录。每个子 skill 独立可用，也可脱离工作流单独调用。

## 启动协议

> ⛔ **禁止跳过 Phase 0 直接 start**。Phase 0 是需求对齐的核心环节，跳过会导致产物方向偏差。

### Phase 0a：Brainstorm（思维风暴）

用户说"跑 XX 竞赛"或"写论文"时，**不要急于收集字段**。先做思维风暴：

1. **理解意图**：用户是想参赛？做科研？写课程报告？续写已有资产？
2. **探索方向**：如果用户的描述模糊（如"帮我做个数模"），主动提出 2-3 个可能的理解方向让用户选择
3. **扫描工作区**：检查当前目录是否已有相关文件（`.tex` / `.pdf` / `.csv` / `PROBLEM_ANALYSIS.md` 等），推断用户可能的意图

Brainstorm 的产出是对用户意图的准确理解，而不是字段清单。

### Phase 0b：Grill Me（审问式追问）

意图明确后，进入**审问式追问**。不是一次性列清单让用户填表，而是像审问者一样逐项深入：

> **Grill Me 规则**：
> - 每次最多问 2-3 项，不要一次性轰炸用户
> - 每项都带**推荐默认值**（基于工作区扫描 + 竞赛规则自动推断）
> - 用户回答后，如果有关联项要继续追问（如选了"国赛" → 追问"A/B/C/D 题"）
> - 用户说"你定"或"默认"时，用推荐值，不再追问该项

**审问清单**（按序追问，跳过已自动推断的项）：

| 序 | 决策项 | 推荐逻辑 | 示例 |
|----|--------|---------|------|
| 1 | 竞赛/场景 | 从用户描述提取 | 国赛 CUMCM / 美赛 MCM / 科研论文 |
| 2 | 工作流模板 | 从竞赛 ID 自动匹配 | `comp_cumcm` / `comp_mcm` / `paper_writing_zh` |
| 3 | 语言 | 竞赛规则决定（国赛→zh，美赛→en） | `zh` / `en` |
| 4 | 题目/研究问题 | 用户必须提供（无法推断） | "A题 雾霾预测与治理" |
| 5 | 页数限制 | 从 `templates/competition_rules.json` 读取 | 国赛 25 页 / 美赛 25 页 |
| 6 | 报表风格 | 竞赛类推荐 `academic`，科研类推荐 `review` | `academic` / `engineering` / `review` |
| 7 | 论文模板变体 | 从竞赛 ID 匹配 `skills/comp-paper-zh/templates/` | `cumcm` / `mcm` / `mathorcup` |
| 8 | 计算工具 | 扫工作区有 `.m` 文件→matlab，否则 python | `python` / `matlab` |
| 9 | 数据来源 | 扫 `user_data/` 和 `*.csv`/`*.xlsx` | 用户提供 / 需搜集 / 无数据 |

**Grill Me 示话术**（agent 应自然对话，不要像填表）：

```
Agent: 了解，你要跑国赛。几个快速确认：
  1. 哪个题？（A/B/C/D）
  2. 用 Python 还是 MATLAB？[扫描到工作区没有 .m 文件，推荐 Python]
  3. 有数据文件吗？[未检测到 user_data/ 目录]

User: C题，Python，数据题目会给

Agent: 收到。再确认两个：
  1. 页数限制按国赛规则 25 页，OK？
  2. 论文模板用 cumcm 版（国赛标准模板），OK？
  [都 OK 的话我直接开始了]

User: OK
```

### Phase 0c：需求确认

把收集到的所有决策整理成清单，**让用户最终确认后才能 start**：

```
需求确认清单：
  ✓ 竞赛：CUMCM 国赛
  ✓ 模板：comp_cumcm
  ✓ 语言：zh（中文）
  ✓ 题目：C题
  ✓ 页数限制：25 页
  ✓ 报表风格：academic
  ✓ 论文模板：cumcm
  ✓ 工具：Python
  ✓ 数据：题目提供
  ✓ 检查点：第 2、4 步（建模完成、论文初稿）

确认无误？确认后我将启动工作流。
```

### Phase 0d：检查点决策

展示工作流的步骤列表，标注哪些步骤默认有检查点，问用户是否调整：

```
工作流步骤（comp_cumcm）：
  [0] 赛题分析        (comp-prob-analysis)
  [1] 建模            (comp-modeling)         ← 检查点
  [2] 代码实现        (comp-code)
  [3] 图表制作        (paper-figure)
  [4] 论文写作        (comp-paper-zh)         ← 检查点
  [5] 编译检查        (comp-compile)

检查点选项：
  A. 用默认设置（推荐）
  B. 每步都设检查点（最严谨）
  C. 不设检查点（最快）
  D. 自定义（告诉我哪些步骤）
```

用户选择后，映射到 `--checkpoints` 参数：
- A → 不传（用模板默认）
- B → `--checkpoints all`
- C → `--checkpoints none`
- D → `--checkpoints 1,4`（用户指定的步骤序号）

### Phase 1：启动工作流

确认完毕后，调用 `mm_flow.py start`（**必须用绝对路径**，`<skill_root>` 是本 SKILL.md 所在目录）：

```bash
python "<skill_root>/orchestrator/mm_flow.py" start comp_cumcm \
  --workspace "<项目根绝对路径>" \
  --language zh \
  --competition CUMCM \
  --problem "C题" \
  --tools python \
  --checkpoints 1,4 \
  --page-limit 25 \
  --paper-style academic \
  --template-variant cumcm
```

> **路径规则**：
> - `<skill_root>`：本 SKILL.md 的 dirname 绝对路径（agent 读取本文件时自动获得）
> - `--workspace`：项目根的绝对路径，禁止用 `.`（相对路径依赖 cwd，从 symlink 调用时会错乱）
> - `mm_flow.py` 内部通过 `__file__` 定位模板和 shared 目录，与 cwd 无关

返回示例：
```json
{
  "workflow_id": "wf_20260722_xxxxx",
  "first_step": {
    "skill_name": "comp-prob-analysis",
    "display_name": "赛题分析",
    "output_files": ["PROBLEM_ANALYSIS.md"],
    "primary_output": "PROBLEM_ANALYSIS.md",
    "has_checkpoint": false
  }
}
```

记下 `workflow_id`，后续所有命令都要用它。若返回 `{"missing": [...]}` 表示必填字段缺失，补齐后重跑。

用户决策会自动写入 `workspace/.mmflow/config.json`，子 skill 执行时可读该文件获取页数限制、报表风格、模板变体等配置。

### 启动后自动行为
`mm_flow.py start` 会自动把 `shared/` 下的以下文件复制到工作区 `_utils/` 目录：
- `figure_check.py`、`figure_check.sh`、`plot_utils.py`、`stats_utils.py`、`drawio_check.py`、`get_recipe.py`
- `compile_utils.sh`、`compile_check.sh`、`writing_check.sh`、`tikz_check.sh`
- `figure_exemplars.md`、`figure_style_guide.md`、`FIGURE_QUICK_REF.md`
- 所有 `figure_recipes_*.md`

无需手动复制。子 skill 应直接引用 `_utils/` 下的脚本。

## 编排协议

拿到 `workflow_id` 后，进入编排循环：

```
1. python <skill_root>/orchestrator/mm_flow.py next <workflow_id>  → 拿到 skill_name
2. Read skills/<skill_name>/SKILL.md  → 理解任务
3. ⚠️ 如果是论文步骤（comp-paper-zh/en）：
   - 必须先 Read PROBLEM_ANALYSIS.md 获取用户完成范围（如"前两问"）
   - 必须先 Read .mmflow/config.json 获取用户决策（页数/风格/模板变体）
   - 必须先 Read .mmflow/feedback.json（如存在）获取用户历史反馈，逐条核对落实
   - 论文章节数必须严格匹配完成范围，禁止虚构超出范围的章节
4. 执行子 skill（按其 SKILL.md 的 Step 0-N 工作）
5. python <skill_root>/orchestrator/mm_flow.py complete <workflow_id>  → 触发健康检查 + 一致性检查
6. 如果返回 {health_failed: true, issues: [...]}：
   - 按 issues 修复产物
   - 重新跑 complete
7. 如果返回 {consistency_failed: true, redo: true, issues: [...], next_action: "..."}：
   - ⚠️ 状态机已自动把步骤改回 pending，必须逐条修复 issues：
     - 虚构章节 → 删除超出完成范围的 problem*.tex
     - 数值不一致 → 核对论文数值与 RESULTS.md / figures/*.json
     - 公式对照表缺失 → 填写 paper/sections/_formula_mapping.md（comp-code 步骤填 code/_formula_mapping.md）
     - 建模-代码脱节 → 核对 MODELING_REPORT.md 公式与 RESULTS.md / code/*.py
     - 建模覆盖不全 → 补齐 MODELING_REPORT.md 中缺失的子问题建模
     - 结构缺失 → 补齐必需章节
   - 修复后重新跑 complete（会再次触发一致性检查，直到全部通过）
8. 如果返回 {feedback_pending: true, redo: true, pending_feedback: [...], next_action: "..."}：
   - ⚠️ 有未处理的用户反馈，必须：
     - Read .mmflow/feedback.json
     - 逐条处理 pending 项（落实后改 status 为 done/skipped）
     - 重新跑 complete
9. 如果返回 {checkpoint: true, type: "user_confirm"}：
   - 向用户展示产物摘要
   - 问用户是否 approve
   - python <skill_root>/orchestrator/mm_flow.py resolve <workflow_id> --decision <approve|reject> [--feedback <text>]
   - ⚠️ resolve 命令会自动把 feedback 写入 .mmflow/feedback.json，重做时必须 Read 该文件逐条落实
10. 如果返回 {finished: true}：工作流完成
11. 否则回到步骤 1
```

所有命令输出结构化 JSON 到 stdout，异常输出到 stderr。

关键返回值速查：
- `next` 返回 `{finished: true}` → 全部步骤完成
- `next` 返回 `{error: "current step waiting for checkpoint, run resolve"}` → 先 resolve
- `next` 返回 `{error: "current step not completed, run complete first"}` → 先 complete
- `complete` 返回 `{health_failed, issues, checks}` → 体积检查未过，修复后重跑
- `complete` 返回 `{consistency_failed, redo: true, issues, warnings, checks, next_action}` → 内容一致性检查未过，状态已改回 pending，逐条修复后重跑
- `complete` 返回 `{feedback_pending, redo: true, pending_feedback, next_action}` → 有未处理反馈，先处理 .mmflow/feedback.json 再重跑
- `complete` 返回 `{checkpoint, type, message}` → 进入 resolve
- `complete` 返回 `{finished: true}` → 完成
- `resolve --decision reject|modify` 返回 `{redo: true, feedback}` → 回到步骤 2 重做本步
- `resolve --decision approve` 返回下一步 info 或 `{finished: true}`

辅助命令：
- `python <skill_root>/orchestrator/mm_flow.py status <workflow_id>` — 查询状态（含 zombie 检测，心跳超 60s 判 zombie）
- `python <skill_root>/orchestrator/mm_flow.py resume <workflow_id>` — 恢复 zombie 工作流
- `python <skill_root>/orchestrator/mm_flow.py health <workflow_id>` — 对所有已完成步骤跑健康检查
- `python <skill_root>/orchestrator/consistency_check.py <workspace>` — 独立跑论文一致性检查（5 项：数值/公式/覆盖度/范围/结构）
- `python <skill_root>/orchestrator/consistency_check.py <workspace> --code` — 独立跑 comp-code 一致性检查（建模-代码数值/公式）
- `python <skill_root>/orchestrator/consistency_check.py <workspace> --modeling` — 独立跑 comp-modeling 覆盖度检查（建模报告是否覆盖所有子问题）

### 一致性检查（comp-modeling + comp-code + 论文步骤）

`complete` 命令对 comp-modeling、comp-code 和论文步骤（comp-paper-zh/en/docx）在健康检查通过后额外运行一致性检查（由 `orchestrator/consistency_check.py` 实现）：

| 检查项 | 检查内容 | 失败后果 | 适用步骤 |
|--------|---------|---------|---------|
| **建模覆盖度** | MODELING_REPORT.md 子问题数 vs 用户完成范围 | error（建模不完整，后续步骤会跟着漏） | **comp-modeling 步骤** |
| **建模-代码数值一致性** | MODELING_REPORT.md 高精度数值是否在 RESULTS.md 中体现 | error（建模公式未被代码实现） | **comp-code 步骤** |
| **建模-代码公式对照表** | code/_formula_mapping.md 是否存在且每个公式标注 ✅ | error（对照表缺失/未覆盖/未标 ✅） | **comp-code 步骤** |
| 数值一致性 | 论文 .tex 中的高精度数值是否来自 RESULTS.md / figures/*.json（支持精度截断 + 四舍五入匹配） | error（高精度 orphan > 3） / warning（低精度） | 论文步骤 |
| **公式-代码对照表** | paper/sections/_formula_mapping.md 是否存在且每个公式标注 ✅ | error（对照表缺失/未覆盖/未标 ✅） | 论文步骤 |
| 原题覆盖度 | 论文 problem*.tex 数量 vs PROBLEM_ANALYSIS.md 子问题数（只查虚构不查缺失） | error（多出=虚构） | 论文步骤 |
| 用户需求范围 | 论文 problem*.tex 数量 vs 用户完成范围（允许 +1 容差） | error（超出范围+1）/ warning（等于范围+1） | 论文步骤 |
| 结构完整性 | 必需章节是否存在（restatement/analysis/assumptions/symbols/evaluation/code） | error（缺失=结构不全） | 论文步骤 |

任何 error 级问题都会阻止步骤推进，状态机自动改回 pending，agent 必须修复后重跑 `complete`。

### 公式-代码对照表机制

> ⛔ **这是杜绝能耗公式不一致的核心机制**。上次作业正是论文写 E=½Jω² 而代码写 E=½Jω|Δθ| 未被挡住，现在强制要求生成对照表。

**comp-code 步骤**：
1. 一致性检查发现 MODELING_REPORT.md 有公式 + code/*.py 有表达式时，自动生成 `code/_formula_mapping.md` 模板
2. agent 必须逐条填写每个公式的代码位置和一致性结论（✅/❌）
3. 对照表不存在 / 未覆盖所有公式 / 有 ❌ 或缺 ✅ → error，阻止推进

**论文步骤**：
1. 一致性检查发现论文有公式 + code/*.py 有表达式时，自动生成 `paper/sections/_formula_mapping.md` 模板
2. agent 必须逐条填写每个公式的代码位置和一致性结论（✅/❌）
3. 对照表不存在 / 未覆盖所有公式 / 有 ❌ 或缺 ✅ → error，阻止推进

### 数值归一化匹配

论文中的数值通常是数据文件的全精度值截断或四舍五入后的结果（如论文写 `1.486`，数据文件是 `1.485507`）。一致性检查支持三种匹配方式：

1. **精确字符串匹配**：论文 `1.859` == 数据 `1.859`
2. **截断匹配**：数据 `1.859024` 截断到 3 位 → `1.859` == 论文 `1.859`
3. **四舍五入匹配**：数据 `1.485507` 四舍五入到 3 位 → `1.486` == 论文 `1.486`

这消除了"论文截断值 vs 数据全精度值"的误报。

### 状态机与重试机制

`complete` 命令的状态机：
- 健康检查失败 → 返回 `health_failed`，步骤保持 running（agent 修复后重跑 complete）
- 一致性检查失败 → 返回 `consistency_failed` + `redo: true`，**步骤自动改回 pending**（agent 修复后重跑 complete，会再次触发检查）
- 反馈未处理 → 返回 `feedback_pending` + `redo: true`，**步骤自动改回 pending**（agent 处理 feedback.json 后重跑 complete）
- 检查点步骤 → 返回 `checkpoint`，步骤改为 waiting_checkpoint（等 resolve）
- 全部通过 → 推进到下一步

> ⚠️ agent 看到 `redo: true` 时，必须按 `next_action` 字段的指示修复后重跑 complete，不要跳过。

### 用户反馈闭环

> ⛔ **禁止忽略用户在检查点 review 时提出的反馈**。所有反馈必须逐条落实。

检查点 review 时用户可能提出修改要求（如"问题重述加文献综述""加支撑材料表"等）。反馈处理流程：

1. **自动记录**：`mm_flow.py resolve --decision reject|modify --feedback <text>` 会自动把反馈追加写入 `.mmflow/feedback.json`，格式为 `[{step_index, decision, feedback, timestamp, status: "pending"}]`
2. **重做时读取**：agent 在重做步骤时必须 Read `.mmflow/feedback.json`，逐条核对落实
3. **标记落实**：重做完成后，agent 必须把 `.mmflow/feedback.json` 中对应条目的 `status` 改为 `done` 或 `skipped`（附 reason）
4. **展示落实情况**：下一次检查点 review 时向用户展示反馈落实情况

> ⚠️ `resolve --decision approve` 时如果带了 feedback（approve with comments），也会写入 feedback.json，供后续步骤参考。

## 产物契约

完整规则见 `references/health_rules.md`（由 `orchestrator/health_check.py` 实现）。关键 step 最小体积要求示例：

| skill_name | 主产物 | 最小字节 | 额外要求 |
|------------|--------|----------|----------|
| `comp-prob-analysis` | `PROBLEM_ANALYSIS.md` | ≥ 1500 | `FIGURE_MANIFEST` 区块规划图 ≥ 3 |
| `comp-modeling` | `MODELING_REPORT.md` | ≥ 2000 | — |
| `comp-code` | `RESULTS.md` | ≥ 1000 | `code/main.py` ≥ 500 字节 + `figures/all_results.json` + 子问题对账（`code/problem*.py` 与 `figures/problem_*_results.json` 数 ≥ 报告中子问题数）|
| `comp-paper-zh` | `paper/main.tex` | ≥ 10000 | — |
| `comp-paper-en` | `paper/main.tex` | ≥ 10000 | — |
| `comp-compile` | `paper/main.pdf` | ≥ 30000 | — |

`complete` 命令会在推进前自动跑健康检查；未通过则返回 `issues`，必须修复后重跑。伴生文件需 > 50 字节才算存在。

## 工具调用时机

| 何时 | 调用什么 | 位置 |
|------|----------|------|
| 识别 PDF 赛题内容 / 描述图像内容 | `vision.py` | `orchestrator/vision.py` |
| 提取 PDF / Word 文本 | `pdf_extract.py` | `orchestrator/pdf_extract.py` |
| 每画完一张图后自检 | `figure_check.py` | `shared/figure_check.py`（已复制到 `_utils/`）|
| 需要外部 LLM 交叉审查 | `reviewer.py` | `orchestrator/reviewer.py` |

调用方式：通过 Bash 执行，完整命令字符串传给 Bash。例：
```bash
python _utils/figure_check.py figures/fig_xxx.png
```

- `vision.py` 需 `ANTHROPIC_API_KEY`（fallback `OPENAI_API_KEY`）
- `reviewer.py` 需 `OPENAI_API_KEY`

## MCP 服务器要求（按需检测，不阻塞数学建模流程）

本 skills 包的数学建模竞赛流程（comp_cumcm / comp_mcm / comp_huashu 等）**不依赖任何 MCP 服务器**，可直接启动。仅在用到文献检索类子 skill（literature-review / literature-review / literature-review）时才需要 `zotero` MCP。

### MCP 依赖矩阵

| 工作流模板 | 需要 zotero？ | 说明 |
|-----------|-------------|------|
| comp_cumcm / comp_mcm / comp_huashu 等所有 comp_* | ❌ 不需要 | 数学建模竞赛流程，直接启动 |
| paper_writing / paper_writing_zh / nature_writing | ❌ 不需要 | 通用论文写作，WebSearch 足够 |
| idea_discovery / full_pipeline | ✅ 需要 | 含 literature-review 文献调研步骤 |
| literature_review / thesis_proposal | ✅ 需要 | 核心是文献检索 |

### 按需检测协议

agent 在调 `mm_flow.py start` 之前，**根据所选模板判断是否需要检测 zotero**：

1. **不需要 zotero 的模板**（comp_* / paper_writing / course_*）：跳过检测，直接 start
2. **需要 zotero 的模板**（idea_discovery / full_pipeline / literature_review / thesis_proposal）：
   - 读 `<skill_root>/.mcp.json` 确认 zotero 配置
   - 尝试调用 `mcp__zotero__search_items` 或任一 `mcp__zotero__*` 工具
   - 如果工具不可用：
     - ⛔ **禁止降级**：不得跳过 zotero 继续执行
     - ⛔ **禁止替代**：不得用 WebSearch / Bash / 本地文件假装替代 zotero 功能
     - ✅ **必须告知用户**：
       ```
       ⚠️ MCP 服务器缺失：zotero

       该 MCP 是 literature-review / literature-review / literature-review 子 skill 的必需依赖，
       缺失将导致文献检索功能无法正常工作。

       请按 <skill_root>/references/mcp_setup.md 安装该 MCP 后重新启动工作流。
       安装配置文件：<skill_root>/.mcp.json
       ```
   - zotero MCP 就绪后，才能调 `mm_flow.py start`

### MCP 配置文件

本 skills 包根目录提供 [.mcp.json](./.mcp.json) 配置模板，agent 宿主（Claude Desktop / Codex CLI / Trae / Cursor）应将其合并到自己的 MCP 配置中。详细安装步骤见 [references/mcp_setup.md](./references/mcp_setup.md)。

### 子 skill 内的其他 MCP 调用一律作废

> ⚠️ **重要**：部分子 skill 的 SKILL.md 中可能引用了 `mcp__obsidian-vault__*`、`mcp__codex__*`、`mcp__claude-review__*`、`mcp__llm-chat__*`、`mcp__minimax-chat__*`、`mcp__illustrator__*` 等其他 MCP。**这些调用在本 skills 包中一律作废**，agent 不得执行。这些 MCP 是旧版宿主环境因自身能力不足才引入的，而 Trae / Codex / Claude Code 等智能体宿主本身具备这些能力，直接用原生能力即可：

| 作废的 MCP 调用 | 旧版宿主用途 | 替代方案（用宿主原生能力） |
|----------------|----------|-------------------------|
| `mcp__obsidian-vault__*` | 查 Obsidian 笔记库（旧版宿主没笔记能力） | 跳过，仅用 zotero + 本地 PDF + WebSearch |
| `mcp__codex__codex` / `mcp__codex__codex-reply` | 分发独立子任务给 Codex CLI（旧版宿主自己不能并行） | **用宿主的子代理能力**：Trae 调 `Task` 工具启动 subagent；Codex 用原生 subagent；Claude Code 用 `Agent` 工具 |
| `mcp__claude-review__*` / `mcp__llm-chat__*` / `mcp__minimax-chat__*` | 调外部 LLM 做交叉审查（旧版宿主自己不能调别的模型） | **agent 自己做 review**：直接读产物文件审查；或调 `python orchestrator/reviewer.py --prompt-file <path>` 用 OpenAI API 做外部审查 |
| `mcp__illustrator__run` | Gemini 图像生成（旧版宿主没图像生成能力） | **用宿主的图像生成能力**：Trae 用 `text_to_image` 工具；Codex/Claude Code 用 matplotlib + `shared/figure_recipes_*.md` 方案；或用 `orchestrator/vision.py` 先生成描述再手绘 |

### 子 skill 内的降级语句作废

> ⚠️ 注意：部分子 skill 的 SKILL.md 中可能写有"if unavailable, skip"或"graceful degradation"语句（如 literature-review 的 Source Table 对 zotero 的降级）。**这些降级语句在本 skills 包中一律作废**，以本段的"禁止降级"规则为准。原因是：降级会导致文献检索质量断崖式下降，与桌面智能体效果不一致。

## preamble 引用

需要以下信息时，读 `preamble.md`：

- **Python / XeLaTeX 路径规则**：环境变量 `PYTHON_PATH` / `XELATEX_PATH` / `BIBTEX_PATH`，未设则 fallback 到 PATH 默认值
- **figure 配色规则**：`PALETTE`、`setup_style` 等统一样式
- **recipe 系统**：`figure_recipes_*.md` 的用法
- **不活动超时规则**：5 分钟无输出会被杀（保持心跳，长任务分段输出）
- **分段写入规则**：大文件（> 200 行）用 heredoc 分段写，避免单次 Write 截断

## 路径约定

- 本 skills 包根目录：即本 `SKILL.md` 所在目录（下文记为 `<skill_root>`）。agent 读取本文件后取其 dirname 即可获得绝对路径。
- orchestrator 脚本：`<skill_root>/orchestrator/`（`mm_flow.py`、`health_check.py`、`consistency_check.py`、`vision.py`、`pdf_extract.py`、`reviewer.py`、`state_store.py`）
- 子 skill：`<skill_root>/skills/<name>/`（每个子 skill 含自己的 `SKILL.md`，独立可用）
- 共享脚本：`<skill_root>/shared/`（`figure_check.py`、`plot_utils.py`、`stats_utils.py`、`figure_recipes_*.md` 等）
- 工作区 `_utils/`：启动时由 `mm_flow.py start` 自动从 `shared/` 复制，子 skill 直接引用 `_utils/<script>`

> ⚠️ **调用 orchestrator 时必须用绝对路径**。agent 的工作目录（cwd）通常是项目根，不是 `<skill_root>`。因此所有 `python orchestrator/mm_flow.py ...` 命令都应改为 `python <skill_root>/orchestrator/mm_flow.py ...`，其中 `<skill_root>` 是本文件的 dirname 绝对路径。`mm_flow.py` 内部通过 `__file__` 自动定位模板和 shared 目录，不依赖 cwd。

完整子 skill 清单见 `references/skill_registry.md`。
