---
name: paper-plan
description: "Generate a structured paper outline from review conclusions and experiment results. Supports research papers (ICLR/NeurIPS/ICML style) and Chinese academic papers (bachelor/master/journal) via the plan_mode parameter. Use when user says \"paper outline\", \"plan the paper\", \"中文大纲\", \"中文论文规划\", \"Chinese paper outline\", or wants to create a paper plan before writing."
argument-hint: [topic-or-venue]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, WebSearch, WebFetch
---

# Paper Plan: From Review Conclusions to Paper Outline

Generate a structured outline from: **$ARGUMENTS**

## Output Contract

**Must produce `PAPER_PLAN.md` (≥ 1KB, complete paper outline)** — write it with the Write tool; do not end the turn without a real file on disk.

## Mode Selection

This skill has two branches, chosen by `params.plan_mode` (or language of the user's request):

| `plan_mode` | When to use | Instructions |
|---|---|---|
| `research` (default) | Research papers, venue-targeted drafting (ICLR/NeurIPS/ICML) | Read `research.md` in this skill, follow its Workflow |
| `zh` | Chinese academic papers (bachelor/master/journal thesis, journal submission) | Read `zh.md` in this skill, follow its Workflow |

Both branches share these invariants:
- Claims-evidence matrix is the backbone (each claim maps to evidence and a section).
- Page budget is a hard constraint (from `templates/competition_rules.json` or Additional Parameters).
- No author information is generated; fabricated BibTeX is forbidden — mark uncertain references `[待验证]`.
- If the output document is `PAPER_PLAN.md` / `PROBLEM_ANALYSIS.md` / `TOPIC_PLAN.md` / `MODELING_REPORT.md`, append the machine-readable `FIGURE_MANIFEST` block at the end (see `zh.md` for the exact format; downstream figure skills reconcile against it).
- Verification before ending:
```bash
PASS=true
[ -f PAPER_PLAN.md ] && SZ=$(wc -c < PAPER_PLAN.md) || SZ=0
if [ "$SZ" -ge 1024 ]; then echo "✅ PAPER_PLAN.md ($SZ bytes)"; else echo "❌ PAPER_PLAN.md 缺失或过小"; PASS=false; fi
[ "$PASS" != true ] && echo "⛔ 验证失败 — 必须修复后再结束本步骤"
```

## Workflow

### Step 0: Choose mode

1. If `params.plan_mode` is set, use it.
2. Else infer: Chinese request + user_data/ with data files → `zh`; venue mention (ICLR/NeurIPS/ICML) or English → `research`.
3. Read the selected branch file and follow its steps (data exploration → claims/evidence → structure → per-section plan → figure plan → citations → cross-review → output).

### Step 1: Data exploration

For `zh` mode, scan `user_data/` with pandas (columns, dtypes, missing values, patterns, which claims the data can support). For `research` mode, gather evidence from NARRATIVE_REPORT.md / experiment results per `research.md`.

### Step 2: Claims-evidence matrix → structure → per-section plan

Build the matrix, choose the structure appropriate to PAPER_TYPE / TARGET_VENUE, then detail each section (core content, subsections, key claims, figure plan, page estimate, key references). Figure planning goes through: exemplar awareness → per-section audit → benchmark check (see branch file for the domain-specific "visual comparison figure" trigger).

### Step 3: Citation scaffolding

List needed references per section. Never fabricate BibTeX — mark uncertain ones `[待验证]`.

### Step 4: Cross-review (optional)

If `REVIEWER_SCRIPT` is configured, send the outline to the external reviewer (see branch file for prompt templates). Skip if unavailable.

### Step 5: Output + verification

Save `PAPER_PLAN.md` following `templates/paper_plan_template.md` (zh) or the research structure (research), append the FIGURE_MANIFEST block, then run the verification snippet above.

## Key Rules

- Large files: write the first section with the Write tool, append the rest with `cat << 'EOF' >> PAPER_PLAN.md`.
- Large literature/data: never `cat` a whole `_extracted.md` — use Read with offset/limit or Grep.
- Do not write extra reports in the project root; `PAPER_PLAN.md` is the single output.
- Markdown LaTeX: block formulas `$$...$$` on their own line with blank lines around; inline `$...$`; avoid `\text{}` wrapping Chinese.
