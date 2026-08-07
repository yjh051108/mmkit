# 产物健康检查规则

> 本文档供 agent 阅读。描述每个子 skill 产物的健康检查规则，包括主产物最小字节数、伴生文件、FIGURE_MANIFEST 对账和 comp-code 子问题对账。
>
> 源文件：`orchestrator/health_check.py`

---

## 1. 检查流程概述

`health_check.check_step(workspace, skill_name)` 按以下顺序检查：

1. **主产物检查**：验证 `_PRIMARY_OUTPUTS` 中配置的主产物文件是否存在，且字节数 ≥ `_STEP_MIN_SIZE` 中的阈值。
2. **伴生文件检查**：验证 `_STEP_REQUIRED_COMPANIONS` 中要求的伴生文件是否存在，且字节数 > 50。
3. **comp-prob-analysis 专项**：检查 `FIGURE_MANIFEST` 区块存在性 + 图表数 ≥ 3。
4. **comp-code 专项**：检查 `code/main.py` ≥ 500 字节、`figures/all_results.json` 存在、子问题对账。

任一检查失败 → `pass: false`，`issues` 列出所有失败项。

返回结构：

```json
{
  "pass": false,
  "issues": ["主输出过小: PROBLEM_ANALYSIS.md (200 字节 < 1500)"],
  "checks": [
    {"name": "primary_output", "pass": false, "detail": "..."},
    {"name": "required_companions", "pass": true, "detail": "..."}
  ]
}
```

---

## 2. _STEP_MIN_SIZE 完整表

每个子 skill 主产物的最小字节数阈值。未列入此表的 skill，默认最小字节数为 **100**。

| skill_name | 最小字节数 |
|---|---:|
| comp-prob-analysis | 1500 |
| comp-modeling | 2000 |
| comp-code | 1000 |
| comp-stats-topic | 1000 |
| comp-paper-zh | 10000 |
| comp-paper-en | 10000 |
| paper-write | 15000 |
| paper-write-zh | 15000 |
| paper-write-nature | 15000 |
| paper-plan | 1000 |
| paper-analysis | 1000 |
| course-plan | 800 |
| course-paper | 5000 |
| course-report | 5000 |
| course-report-plan | 800 |
| thesis-proposal | 2000 |
| literature-review | 2000 |
| idea-creator | 1500 |
| novelty-check | 800 |
| research-review | 800 |
| research-refine-pipeline | 1500 |
| auto-review-loop | 1000 |
| auto-paper-improvement-loop | 50000 |
| paper-compile | 30000 |
| assets-inventory | 500 |
| format-profile | 300 |
| docx-template-map | 100 |
| docx-format-check | 200 |
| docx-format-check | 5000 |
| experiment-bridge | 500 |
| paper-figure | 500 |
| nature-figure | 500 |

> 合计 43 个条目。未列入此表的 skill（如 `idea-discovery` / `research-pipeline` / `paper-writing` 等编排类 skill），主产物检查跳过（视为通过）。

---

## 3. _PRIMARY_OUTPUTS 主产物路径表

| skill_name | 主产物相对路径 |
|---|---|
| comp-prob-analysis | `PROBLEM_ANALYSIS.md` |
| comp-modeling | `MODELING_REPORT.md` |
| comp-code | `RESULTS.md` |
| comp-paper-zh | `paper/main.tex` |
| comp-paper-en | `paper/main.tex` |
| comp-compile | `paper/main.pdf` |

| paper-figure | `figures/`（目录型，要求存在且非空） |

> 未列入此表的 skill，主产物路径未知，跳过主产物检查（`detail: "未配置 {skill_name} 的主产物路径，跳过"`）。
>
> 目录型主产物（以 `/` 结尾）：要求目录存在且包含至少一个文件（递归检查 `rglob("*")`）。

---

## 4. _STEP_REQUIRED_COMPANIONS 伴生文件表

| skill_name | required_companions |
|---|---|
| comp-code | `code/main.py`, `figures/all_results.json` |

> 伴生文件额外要求：每个文件必须存在且字节数 > 50，否则视为缺失。
>
> 当前仅 `comp-code` 有伴生文件要求。其他 skill 无额外伴生文件要求。

---

## 5. FIGURE_MANIFEST 对账规则

### 5.1 触发条件

- **comp-prob-analysis** step 的健康检查中自动触发。
- 也可通过 `check_figure_manifest(workspace, plan_file=None)` 独立调用。

### 5.2 提取流程

1. **寻找文档**：依次尝试以下文件（先找到的优先）：
   - `PROBLEM_ANALYSIS.md`
   - `PAPER_PLAN.md`
   - `MODELING_REPORT.md`
   - 若指定了 `plan_file` 参数，则只读该文件。

2. **提取区块**：用正则匹配 `<!-- BEGIN FIGURE_MANIFEST -->` 到 `<!-- END FIGURE_MANIFEST -->` 之间的内容（大小写不敏感，跨行匹配）：
   ```
   _MANIFEST_BLOCK_RE = re.compile(
       r"<!--\s*BEGIN\s+FIGURE_MANIFEST\s*-->(.*?)<!--\s*END\s+FIGURE_MANIFEST\s*-->",
       re.IGNORECASE | re.DOTALL,
   )
   ```

3. **解析条目**：每行匹配 `- fig_xxx` / `- tikz_xxx` 格式：
   ```
   _MANIFEST_ITEM_RE = re.compile(r"^\s*-\s+([A-Za-z0-9_-]+)\s*$")
   ```
   提取出的名称去重后汇总。

### 5.3 验证规则

- **仅校验数据图**：DrawIO/TikZ 架构图（前缀为 `fig_arch` / `fig_flow` / `fig_roadmap` / `fig_pipeline` / `fig_framework` / `fig_er` / `fig_overview` / `fig_system` / `fig_module` / `fig_index` / `fig_hierarchy` / `fig_multiagent` / `fig_topology` / `fig_dataflow` / `fig_pkg` / `fig_class` / `fig_seq` / `fig_gantt` / `fig_network` / `fig_model_decision` / `fig_decision` / `fig_state` / `fig_uml` / `tikz_`）不在此校验范围。

- **验证文件存在**：对每个数据图名称，在 `figures/` 目录下查找匹配文件：
  - 先按扩展名匹配：`.png` / `.pdf` / `.jpg` / `.jpeg` / `.svg` / `.drawio` / `.tex` / `.webp`
  - 再按文件 stem 大小写不敏感匹配

- **comp-prob-analysis 专项额外要求**：
  - FIGURE_MANIFEST 区块必须存在（不存在 → fail）
  - 图表数 ≥ 3（不足 → fail）
  - 每张图必须存在（少一张 → fail）

### 5.4 返回格式

```json
{
  "pass": false,
  "expected": ["fig_convergence", "fig_sensitivity", "fig_comparison"],
  "missing": ["fig_comparison"]
}
```

---

## 6. comp-code 子问题对账规则

### 6.1 触发条件

- **comp-code** step 的健康检查中自动触发。
- 也可通过 `check_comp_code_problems(workspace)` 独立调用。

### 6.2 识别子问题数 N

从 `MODELING_REPORT.md` 中提取子问题数量：

1. **优先中文序号**：匹配 `问题一` / `问题二` / ... / `问题十`，统计去重后的数量。
   ```
   _PROB_ZH_RE = re.compile(r"问题[一二三四五六七八九十]")
   ```

2. **回退英文序号**：若无中文匹配，匹配 `Problem 1` / `Problem 2` / ...，统计去重后的数字数量。
   ```
   _PROB_EN_RE = re.compile(r"problem\s*(\d+)", re.IGNORECASE)
   ```

3. **无法识别**：若 N = 0（未找到任何子问题标记），跳过对账，视为通过。

### 6.3 验证规则

- `code/problem*.py` 文件数 ≥ N
- `figures/problem_*_results.json` 文件数 ≥ N

两个条件都满足 → 通过；否则 → 失败。

### 6.4 返回格式

```json
{
  "pass": false,
  "expected_count": 3,
  "actual_code": 2,
  "actual_json": 3
}
```

---

## 7. comp-code 完整检查清单

comp-code step 的健康检查包含 4 项（全部通过才算 pass）：

| 检查项 | name | 规则 |
|--------|------|------|
| 主产物 | `primary_output` | `RESULTS.md` 存在且 ≥ 1000 字节 |
| 伴生文件 | `required_companions` | `code/main.py` 和 `figures/all_results.json` 存在且 > 50 字节 |
| main.py 体积 | `code_main_py_size` | `code/main.py` ≥ 500 字节 |
| all_results.json | `all_results_json` | `figures/all_results.json` 存在 |
| 子问题对账 | `comp_code_problems` | `code/problem*.py` ≥ N 且 `figures/problem_*_results.json` ≥ N |

---

## 8. DrawIO/架构图前缀表

以下前缀的图表属于架构图/DrawIO 图，在 FIGURE_MANIFEST 对账时**跳过验证**：

| 前缀 |
|------|
| `fig_arch` |
| `fig_flow` |
| `fig_roadmap` |
| `fig_pipeline` |
| `fig_framework` |
| `fig_er` |
| `fig_overview` |
| `fig_system` |
| `fig_module` |
| `fig_index` |
| `fig_hierarchy` |
| `fig_multiagent` |
| `fig_topology` |
| `fig_dataflow` |
| `fig_pkg` |
| `fig_class` |
| `fig_seq` |
| `fig_gantt` |
| `fig_network` |
| `fig_model_decision` |
| `fig_decision` |
| `fig_state` |
| `fig_uml` |
| `tikz_` |

数据图支持的图像扩展名：`.png` / `.pdf` / `.jpg` / `.jpeg` / `.svg` / `.drawio` / `.tex` / `.webp`

---

## 9. CLI 独立调用

```bash
# 检查单个 skill 的产物健康度
python health_check.py <workspace> <skill_name>

# 示例
python health_check.py . comp-prob-analysis
```

输出格式化 JSON（`indent=2`），退出码 0 表示通过，1 表示失败。
