---
name: paper-figure
description: "Generate publication-quality figures and tables for papers: data figures (matplotlib) or architecture/flow diagrams (DrawIO/TikZ). Mode chosen by figure_type parameter. Use when user says \"画图\", \"作图\", \"generate figures\", \"paper figures\", \"画DrawIO\", \"技术路线图\", \"流程图\", or needs any diagram for a paper."
argument-hint: [figure-plan-or-data-path]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent
---

# Paper Figure: Publication-Quality Figure Generation

Generate figures and tables from data: **$ARGUMENTS**

## Output Contract

- **Data figures (default)**: follow `references/figure-data.md` — matplotlib figures matching the project style guide, verified with `figure_check.sh`, reconciled against the FIGURE_MANIFEST.
- **DrawIO/TikZ diagrams**: follow `references/figure-drawio.md` — architecture / flow / roadmap diagrams, verified with `drawio_check.py`, reconciled against the FIGURE_MANIFEST.

## Mode Selection

| Mode | When | Follow |
|---|---|---|
| `data` (default) | Figures derived from experiment results (bars, lines, heatmaps, tables) | `references/figure-data.md` |
| `drawio` | Architecture diagrams, flowcharts, roadmaps (non-data) | `references/figure-drawio.md` |

Choose by `params.figure_type`; fall back to the display_name of the current workflow step ("图表生成"/"缺口补全(图表)" → data; "流程与架构图绘制"/"技术路线图" → drawio).

## Shared invariants (both modes)

1. **Reconcile against FIGURE_MANIFEST first** — the plan (PAPER_PLAN.md / PROBLEM_ANALYSIS.md / PROPOSAL.md) lists every required figure. Every planned figure must be produced; missing one is an error.
2. Read the style guide and exemplars **before** writing figure code (`shared/figure_style_guide.md`, `shared/figure_exemplars.md`, `shared/figure_recipes_<type>.md`) so new figures match the existing palette.
3. Do not `cat` the whole style guide (~50KB) — `head -1500` or Grep/Read on demand.
4. No hardcoded colors — use `PALETTE[0]`… from `shared/plot_utils.py`; no `plt.title()`.
5. Naming: `figures/fig_*.png` + `figures/fig_*.pdf`; DrawIO: `*.drawio` + exported `.png/.pdf`; TikZ: `tikz_*.tex` → `tikz_*.pdf`.
6. Run the checker script for the mode before ending (`figure_check.sh` for data, `drawio_check.py` for diagrams).

## Workflow

### Step 1: Read plan + inventory

Read the planning document and extract the FIGURE_MANIFEST block (see branch files for exact extraction). Inventory existing `figures/` (detect half-finished state: data ready but figure missing).

### Step 2: Read style guide (on demand)

Consult `shared/figure_style_guide.md` for palette + decision table + anti-patterns, and `shared/figure_recipes_<type>.md` for the matching recipe set (`shared/get_recipe.py <type> <id>` extracts a full recipe).

### Step 3: Generate figures per mode

Follow the branch file's generation loop (data mode: plot from `figures/experiment_data.json` / `all_results.json`; drawio mode: build `.drawio` XML → render → embed).

### Step 4: Verify

Run the mode's checker script, fix anti-patterns, confirm every manifest figure exists.

## Key Rules

- ⛔ If the paper is intrinsically visual (image enhancement / super-resolution / detection / generation / reconstruction), the domain-specific "visual comparison" figure (`fig_*_visual_cmp`) is the hero figure — it outranks all metric charts. Use real samples, never AI-generated imaginary images.
- Figures are evidence, not decoration: refer to them via `（图X）` parentheticals in the text, never "如图X所示" sentence-openers.
- Keep the same palette across all figures — style drift reads as "patched on".
