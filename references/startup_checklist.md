# 启动期字段收集清单

> 本文档供 agent 阅读。描述启动数模竞赛工作流（`mm_flow.py start`）前需要收集的字段、自动寻找规则、默认值策略和完整命令模板。
>
> ⚠️ **优先级**：启动字段收集发生在「需求对齐协议」之后。agent 必须先完成 SKILL.md 中定义的需求对齐阶段（Q1-Q6），收集到以下扩展字段后，再调 `mm_flow.py start`。
>
> 源文件：`orchestrator/mm_flow.py`、`templates/competition_rules.json`

---

## 1. 启动字段一览

### 1.1 基础字段（mm_flow.py start 必填）

| 字段 | 必填 | 自动寻找规则 | 默认值 | 何时开放问用户 |
|------|------|-------------|--------|---------------|
| `template_name` | 是 | 扫工作区 `*.tex` → `paper_from_assets`；扫 `user_data/*.pdf` → `comp_cumcm` | - | 无法自动推断时 |
| `workspace` | 是 | 当前工作目录 | `.` | - |
| `language` | 是 | 从 `template_name` 推断（`comp_cumcm` → `zh`，`comp_mcm` → `en`，`comp_apmcm` → `en`） | `zh` | - |
| `competition` | 是 | 从 `template_name` 提取（同名映射，如 `comp_cumcm` → `comp_cumcm`） | - | 同 `template_name` |
| `problem` | 是 | 扫 `user_data/*.pdf` 或 `*_extracted.txt` 提取赛题文本 | - | 找不到时 |
| `tools` | 否 | - | `python` | 用户提到 matlab 时 |
| `data_files` | 否 | 扫 `user_data/*.csv`、`*.xlsx` | - | - |

### 1.2 需求对齐扩展字段（SKILL.md 需求对齐阶段收集，agent 自行记录）

> 这些字段不传给 `mm_flow.py start`，但 agent 在执行过程中必须遵守。

| 字段 | 来源 | 用途 | 默认值 |
|------|------|------|--------|
| `sub_problems` | Q2 追问 | 指定做哪些子问题（如"只做前两问"） | 全部 |
| `modeling_approach` | Q3 brainstorm | 建模思路方向（agent + 用户确认） | agent 判断 |
| `page_target` | Q4 | 论文目标页数（精简/标准/满页） | 标准版 |
| `figure_style` | Q4 追问 | 图表风格偏好（学术简约/竞赛丰富） | 竞赛丰富 |
| `checkpoint_strategy` | Q5 | 检查点策略（每步/关键步/全自动/自定义） | 关键步 |
| `auto_fix` | Q5 追问 | 健康检查失败时是否自动修复 | 是 |
| `special_requirements` | Q6 | 用户特殊要求（提交格式、参考文献格式等） | 无 |

---

## 2. 字段详解

### 2.1 template_name（模板名称）

决定工作流的 `sub_steps` 序列。可选值来自 `workflow_templates.json`。

**自动推断逻辑：**

| 工作区特征 | 推断结果 |
|-----------|---------|
| 存在 `*.tex` 或 `paper/main.tex` | `paper_from_assets`（基于已有资产写论文） |
| 存在 `user_data/*.pdf`（赛题 PDF） | `comp_cumcm`（国赛默认） |
| 无上述特征 | 需问用户 |

**竞赛模板与 competition / language 映射：**

| template_name | competition | language | 竞赛名称 | template_cls |
|--------------|------------|----------|---------|-------------|
| `comp_cumcm` | `comp_cumcm` | `zh` | 全国大学生数学建模竞赛 (CUMCM) | `cumcmthesis` |
| `comp_mcm` | `comp_mcm` | `en` | MCM/ICM (COMAP) | `mcmthesis` |
| `comp_huawei` | `comp_huawei` | `zh` | 华为杯全国研究生数学建模竞赛 | `gmcmthesis` |
| `comp_mathorcup` | `comp_mathorcup` | `zh` | MathorCup 数学建模挑战赛 | `ctexart` |
| `comp_apmcm` | `comp_apmcm` | `en` | 亚太地区数学建模竞赛 (APMCM) | `apmcmthesis` |
| `comp_apmcm_zh` | `comp_apmcm_zh` | `zh` | APMCM 中文赛项 | `MathorCupmodeling` |
| `comp_stats` | `comp_stats` | `zh` | 全国大学生统计建模大赛 | `ctexart` |
| `comp_teddy` | `comp_teddy` | `zh` | 泰迪杯数据挖掘挑战赛 | `ctexart` |
| `comp_certcup` | `comp_certcup` | `zh` | 认证杯数学建模 | `ctexart` |
| `comp_huazhong` | `comp_huazhong` | `zh` | 华中杯数学建模邀请赛 | `cumcmthesis` |

### 2.2 workspace（工作区目录）

工作流的文件操作根目录。所有产物（`PROBLEM_ANALYSIS.md` / `MODELING_REPORT.md` / `code/` / `figures/` / `paper/` 等）都在此目录下生成。

- 默认：当前工作目录（`.`）
- 共享工具文件会复制到 `<workspace>/_utils/`

### 2.3 language（语言）

- `zh`：中文竞赛（CUMCM / 华为杯 / MathorCup / 统计建模 / 泰迪杯 / 认证杯 / 华中杯）
- `en`：英文竞赛（MCM/ICM / APMCM 英文赛项）
- 默认 `zh`（无法确定时）

### 2.4 competition（竞赛 ID）

与 `template_name` 同名。用于从 `competition_rules.json` 加载竞赛规则（页数限制、文档类、结构要求等）。

### 2.5 problem（研究问题描述）

赛题的文本内容。用于 `comp-prob-analysis` 等 step 的输入。

**自动寻找：**
- 优先读 `user_data/*_extracted.txt`（已提取的赛题文本）
- 其次读 `user_data/*.pdf`（需提示用户该 PDF 是赛题）
- 如果赛题直接在用户消息中给出，直接使用

### 2.6 tools（工具链）

- `python`（默认）
- `matlab`：用户明确提到时使用

### 2.7 data_files（数据文件）

附加数据文件路径列表。非必填，仅用于 agent 参考。

---

## 3. 自动寻找的执行顺序

按以下顺序扫描工作区，逐步推断字段：

```bash
# 1. 扫工作区文件 —— 推断 template_name 和 problem
ls user_data/*.pdf 2>/dev/null && echo "有 PDF 附件（可能是赛题）"
ls user_data/*_extracted.txt 2>/dev/null && echo "有已提取赛题文本"
ls user_data/*.csv 2>/dev/null && echo "有数据文件"
ls user_data/*.xlsx 2>/dev/null && echo "有 Excel 数据文件"
ls *.tex 2>/dev/null && echo "有 LaTeX 文件 → paper_from_assets"
ls paper/main.tex 2>/dev/null && echo "已有论文目录 → paper_from_assets"
ls PROBLEM_ANALYSIS.md 2>/dev/null && echo "已分析过（可能续接工作流）"
ls MODELING_REPORT.md 2>/dev/null && echo "已建模过"
ls RESULTS.md 2>/dev/null && echo "已出结果"
```

**推断决策树：**

```
有 *.tex 或 paper/main.tex？
  ├─ 是 → template_name = paper_from_assets
  └─ 否 → 有 user_data/*.pdf？
            ├─ 是 → template_name = comp_cumcm（默认国赛，可问用户确认）
            └─ 否 → 问用户选哪个竞赛模板
```

---

## 4. 带默认值问用户的示例对话

### 场景 1：用户上传了赛题 PDF，但没说哪个竞赛

```
Agent: 我检测到 user_data/ 下有赛题 PDF（problem_2024_A.pdf）。
       请确认这是什么竞赛？
       1. 全国大学生数学建模竞赛 (CUMCM) — comp_cumcm
       2. MCM/ICM (COMAP) — comp_mcm
       3. 华为杯研究生数学建模 — comp_huawei
       4. MathorCup — comp_mathorcup
       5. 其他（请说明）

User: 1

Agent: 确认信息：
       - 模板：comp_cumcm
       - 语言：zh
       - 竞赛：comp_cumcm
       - 工作区：.（当前目录）
       - 赛题：user_data/problem_2024_A.pdf
       - 工具：python
       是否开始？

User: 是
```

### 场景 2：工作区有 LaTeX 文件，续接论文

```
Agent: 检测到工作区已有 LaTeX 文件（paper/main.tex）和建模报告（MODELING_REPORT.md）。
       将使用 paper_from_assets 模板续接论文撰写。
       默认语言：zh，工具：python。
       是否开始？

User: 是
```

### 场景 3：无法自动推断，需用户指定

```
Agent: 未检测到赛题 PDF 或 LaTeX 文件。请告诉我：
       1. 你要参加什么竞赛？（或选择模板）
       2. 赛题内容是什么？（粘贴文本或上传文件）

User: 我要参加美赛，题目是关于气候变化的...

Agent: 确认信息：
       - 模板：comp_mcm
       - 语言：en
       - 竞赛：comp_mcm
       - 工作区：.（当前目录）
       - 赛题：气候变化...（用户粘贴文本）
       - 工具：python
       是否开始？

User: 是
```

### 场景 4：用户提到 matlab

```
Agent: 确认信息：
       - 模板：comp_cumcm
       - ...
       - 工具：matlab（你提到了 MATLAB）
       是否开始？
```

---

## 5. 调 mm_flow start 的完整命令模板

### 基本命令

```bash
python orchestrator/mm_flow.py start \
  <template_name> \
  --workspace . \
  --language <zh|en> \
  --competition <competition_id> \
  --problem "<problem_text>" \
  --tools <python|matlab>
```

### 示例 1：国赛（中文）

```bash
python orchestrator/mm_flow.py start \
  comp_cumcm \
  --workspace . \
  --language zh \
  --competition comp_cumcm \
  --problem "2024年A题：螺旋桨设计问题。要求建立数学模型优化螺旋桨参数..." \
  --tools python
```

### 示例 2：美赛（英文）

```bash
python orchestrator/mm_flow.py start \
  comp_mcm \
  --workspace . \
  --language en \
  --competition comp_mcm \
  --problem "Problem A: Climate change impacts. Build a model to..." \
  --tools python
```

### 示例 3：基于已有资产写论文

```bash
python orchestrator/mm_flow.py start \
  paper_from_assets \
  --workspace . \
  --language zh \
  --competition comp_cumcm \
  --problem "基于已有建模结果撰写论文" \
  --tools python
```

### 启动成功后的返回值

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_step": {
    "skill_name": "comp-prob-analysis",
    "display_name": "赛题分析",
    "output_files": ["PROBLEM_ANALYSIS.md"],
    "primary_output": "PROBLEM_ANALYSIS.md",
    "has_checkpoint": false
  }
}
```

**agent 拿到 `workflow_id` 后**：
1. 根据 `first_step` 的 `skill_name` 调用对应子 skill 执行产物。
2. 产物完成后调 `complete <workflow_id>` 触发健康检查。
3. 后续按 [workflow_rules.md](./workflow_rules.md) 的 DAG 推进规则执行。

---

## 6. 启动检查清单

### 6.1 需求对齐检查（⛔ 必须先完成）

agent 在调 `start` 前必须确认需求对齐阶段已完成：

- [ ] Q1 竞赛类型与模板已确认
- [ ] Q2 赛题内容已获取，子问题范围已明确
- [ ] Q3 建模思路已对齐（agent 给出思路，用户确认或调整）
- [ ] Q4 论文篇幅目标已确认（精简/标准/满页）
- [ ] Q5 检查点策略已确认（每步/关键步/全自动/自定义）
- [ ] Q6 特殊要求已收集（如有）
- [ ] 需求确认摘要已输出且用户已确认

### 6.2 基础字段检查

agent 在调 `start` 前应确认：

- [ ] `template_name` 已确定（自动推断或用户指定）
- [ ] `workspace` 路径有效且可写（默认 `.`，禁止硬编码绝对路径）
- [ ] `language` 与竞赛匹配
- [ ] `competition` 与 `template_name` 一致
- [ ] `problem` 文本已获取（赛题 PDF 已读取或用户已粘贴）
- [ ] `tools` 已确认（默认 python，用户提 matlab 则用 matlab）
- [ ] 若有数据文件（`user_data/*.csv` / `*.xlsx`），agent 应知晓路径供后续 step 使用

**必填字段缺失时**，`start` 命令返回：

```json
{
  "missing": ["problem", "competition"]
}
```

agent 应根据 `missing` 列表补全字段后重新调用 `start`。
