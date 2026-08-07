## 环境变量
本 skill 通过以下环境变量检测外部工具路径：
- `PYTHON_PATH`：Python 解释器路径（fallback: python）
- `XELATEX_PATH`：XeLaTeX 路径（fallback: xelatex）
- `BIBTEX_PATH`：BibTeX 路径（fallback: bibtex）
- `ANTHROPIC_API_KEY`：Anthropic API 密钥（用于 vision.py）
- `OPENAI_API_KEY`：OpenAI API 密钥（用于 reviewer.py 和 vision.py fallback）
如果未设置，系统会使用 PATH 中的默认值。

## IMPORTANT EXECUTION INSTRUCTIONS
You are running in non-interactive mode (claude -p). Do NOT use slash commands like /skill-name. Instead, directly execute the task described below. You MUST write output files to the current working directory. Use the tools available to you (Bash, Read, Write, Edit, WebSearch, WebFetch, etc.) to complete the task. At minimum, produce a markdown report file summarizing your work.

## CRITICAL TOOL USAGE RULES
**Every tool call MUST include ALL required parameters. Never send a tool call with empty input `{}`.**

- **Bash**: MUST always include the `command` parameter with a non-empty string.
- **Write**: MUST always include both `file_path` (absolute path) and `content` (file content string).
- **Edit**: MUST always include `file_path`, `old_string`, and `new_string`.

**LARGE FILE WRITING**: When writing a long file (e.g., a report > 200 lines), do NOT try to write the entire content in a single Write tool call — this may cause the tool call to be truncated and fail with empty parameters. Instead:
1. Write the file in sections using Bash with heredoc:
   ```bash
   cat << 'EOF' > IDEA_REPORT.md
   # Section 1 content here...
   EOF
   ```
2. Then append additional sections:
   ```bash
   cat << 'EOF' >> IDEA_REPORT.md
   # Section 2 content here...
   EOF
   ```
This chunked approach avoids output token limits that cause truncated tool calls.

## REVIEWER TOOL
A reviewer script is available for calling an external LLM for cross-model review. 使用 orchestrator/reviewer.py（本 skill 自带）。Use it via the Bash tool. IMPORTANT: Always pass the complete command string to the Bash tool.

**Single review example** (pass this entire block as the Bash `command` parameter):
```bash
cat << 'REVIEW_EOF' > _review_prompt.txt
Your review prompt here...
REVIEW_EOF
PYTHON=$(command -v python 2>/dev/null) && $PYTHON orchestrator/reviewer.py --prompt-file _review_prompt.txt
```

**Multi-round review example** (maintains conversation context):
```bash
cat << 'REVIEW_EOF' > _review_prompt.txt
Your review prompt here...
REVIEW_EOF
PYTHON=$(command -v python 2>/dev/null) && $PYTHON orchestrator/reviewer.py --prompt-file _review_prompt.txt --thread-file _reviewer_thread.json
```
Round 2+ uses the same --thread-file to continue the conversation.

The reviewer model is configured by the user in the mmkit settings page. If the reviewer is not configured (OPENAI_API_KEY not set), skip the review step and proceed with your own analysis.

## PYTHON ENVIRONMENT
The system has detected a working Python at: `$env:PYTHON_PATH (fallback: python)`
**You MUST use this exact path for ALL Python operations:**
- Run scripts: `"$env:PYTHON_PATH (fallback: python)" figures/gen_fig_xxx.py`
- Install packages: `"$env:PYTHON_PATH (fallback: python)" -m pip install matplotlib pandas numpy`
- Check version: `"$env:PYTHON_PATH (fallback: python)" --version`
**Do NOT use `python3` — it may point to a non-functional Windows Store stub.**
**Do NOT use bare `pip` — use `"$env:PYTHON_PATH (fallback: python)" -m pip` instead.**

## XELATEX ENVIRONMENT
The system has detected XeLaTeX at: `$env:XELATEX_PATH (fallback: xelatex)`
**⛔ For Chinese papers, you MUST use this exact path. NEVER use pdflatex for Chinese — it causes garbled text.**
- Compile Chinese: `"$env:XELATEX_PATH (fallback: xelatex)" -interaction=nonstopmode main.tex`
- BibTeX: `"$env:BIBTEX_PATH (fallback: bibtex)" main`
**Full Chinese compilation sequence:**
```bash
"$env:XELATEX_PATH (fallback: xelatex)" -interaction=nonstopmode main.tex
"$env:BIBTEX_PATH (fallback: bibtex)" main
"$env:XELATEX_PATH (fallback: xelatex)" -interaction=nonstopmode main.tex
"$env:XELATEX_PATH (fallback: xelatex)" -interaction=nonstopmode main.tex
```

## UTILITY LIBRARIES (PRE-INSTALLED)
The workspace has pre-installed utility libraries in `_utils/` directory:
- **`_utils/FIGURE_QUICK_REF.md`** — ⛔ READ THIS FIRST: compact decision table + anti-patterns (auto-extracted, small file)
- `_utils/plot_utils.py` — Academic-quality plots (heatmap, forest_plot, trend_plot, bar_compare, scatter_plot, distribution_plot, residual_diagnostic)
- `_utils/stats_utils.py` — LaTeX table generators (regression_table, descriptive_table, correlation_table)
- `_utils/compile_utils.sh` — Pre-compile cleanup script
- `_utils/figure_recipes_basic.md` — 12 basic chart recipes (gradient fills, KDE backgrounds, Rain Cloud)
- `_utils/figure_recipes_advanced.md` — 17 high-impact SCI chart recipes (Lollipop, SHAP, Kaplan-Meier, etc.)
- `_utils/figure_recipes_empirical.md` — 16 econometrics/stats recipes (Forest plot, DID, Quantile regression)
- `_utils/figure_recipes_competition.md` — 23 competition recipes (convergence, Pareto, centroid migration, bubble+KDE)
- `_utils/figure_recipes_academic.md` — 12 AI/CS academic recipes (ablation, t-SNE, training curves)
- `_utils/figure_style_guide.md` — Full color palettes, TikZ templates, and styling tips
- `_utils/figure_exemplars.md` — Chart distribution exemplars by paper type

**Step 1 of ANY figure generation: `cat _utils/FIGURE_QUICK_REF.md` — this is a small file, takes 2 seconds to read.**

## ⚠️ CRITICAL — FIGURE STYLING RULES (MUST FOLLOW)
**All figures must be SCI publication quality.** NEVER use matplotlib default colors (the ugly blue #1f77b4). ALWAYS use seaborn + our palettes.

Before ANY plotting, you MUST run:
```python
import sys; sys.path.insert(0, '.')
from _utils.plot_utils import setup_style, PALETTE, PALETTE_LIGHT
setup_style()  # Auto-detects SciencePlots (if installed) + Soft palette
import seaborn as sns
```

**If SciencePlots is not installed, install it first: `pip install SciencePlots`**

**⛔ FOLLOW RECIPE CODE over seaborn defaults. Our recipes use raw matplotlib with gradient fills, KDE backgrounds, annotation boxes — these produce much better visuals than seaborn's high-level API. Use seaborn only for quick data exploration, NOT for final publication figures.**

**For final figures, ALWAYS:**
1. `cat` the matched recipe from `_utils/figure_recipes_*.md`
2. Copy the recipe code as starting point
3. Adapt to your actual data
This produces gradient fills, smart labels, layered visuals that seaborn cannot do.

**For single-group bar charts (no hue), use different color per bar:**
```python
ax.bar(categories, values, color=PALETTE[:len(categories)], edgecolor='white', linewidth=1.2)
```

**⛔ NEVER hardcode your own color hex values (like '#d7191c', '#2b83ba'). ALWAYS use PALETTE[0], PALETTE[1], etc.**
**⛔ NEVER use plt.cm.XXX colormap for bar/line charts — use PALETTE[:n] discrete colors instead. Colormaps are only for heatmaps/contours.**
**⛔ NEVER use RdYlGn or RdYlGn_r colormap — it looks like a traffic light. Use coolwarm (diverging) or YlOrRd (sequential) instead. Do NOT use RdBu_r — too dark.**
**⛔ NEVER use plt.title() — titles go in LaTeX \caption{} only.**
**⛔ NEVER use ax.grid() — the whitegrid theme handles grid automatically.**

**Available palettes**: `setup_style()` (default Journal — low-saturation, SCI-ready), `setup_style('soft')` (bright & clean), `setup_style('tableau')` (>6 colors), `setup_style('npg')` (Nature), `setup_style('nejm')` (medical/stats), `setup_style('science')` (engineering), `setup_style('colorblind')` (accessibility)

**⛔ PALETTE SELECTION RULE**: Read the research topic, then choose the palette that best matches the paper's domain and aesthetic. You are free to pick any palette — the key rule is ALL figures in one paper use the same one:
- `setup_style()` or `setup_style('elegant')` — default, soft and clean, good for most topics
- `setup_style('soft')` — bright & warm, good for competition papers
- `setup_style('journal')` — low-saturation Morandi tones, SCI journal style
- `setup_style('tableau')` — modern, high contrast, good when >6 groups
- `setup_style('npg')` — Nature style, vivid, good for natural science
- `setup_style('nejm')` — elegant, good for medical/stats
- `setup_style('science')` — classic, good for engineering/CS
- `setup_style('colorblind')` — accessibility-first
- Choose based on the paper's topic and your aesthetic judgment. Different topics should get different palettes — don't always default to elegant.
- **⛔ ALL figures in one paper MUST use the same palette.**

If `_utils/` does not exist, define PALETTE first then use it:
```python
PALETTE = ['#7AAEC8','#E8945A','#7BC8A4','#9B8EC4','#E0A0A0','#F0C05A','#8FAEC0','#A8C4D8']
# Then use PALETTE[0], PALETTE[1], etc. — NEVER hardcode other colors
```

## CHART TYPE SELECTION
**⛔ Read `_utils/FIGURE_QUICK_REF.md` first — it has the full decision table.**

**⛔ CHART SELECTION RULES:**
- Match chart type to data shape (see decision table in FIGURE_QUICK_REF.md)
- Do NOT use the same chart type more than 3 times in one paper
- Mix basic and advanced charts for visual variety
- If the planning doc (TOPIC_PLAN.md / PROBLEM_ANALYSIS.md) specifies a chart type, follow it
- Grouped bar charts are fine for multi-method × multi-metric comparisons
- Use advanced charts (Waterfall, SHAP, Diverging Bar, etc.) when they genuinely add information

NEVER use cmap='RdYlGn' (traffic light) — use 'coolwarm' or 'YlOrRd'. Do NOT use 'RdBu_r' (too dark).
NEVER use sns.heatmap(annot=True) — seaborn default all-black text is unreadable on dark cells. Use annot=False + manual ax.text() with auto color: `color='white' if norm_val > 0.6 else COLORS['text']`
TEXT COLOR CONTRAST: value labels on bars/dots should NOT be the same color as the element itself. Create visual hierarchy by using a contrasting color for labels — the key rule is element color ≠ label color. Choose label colors that complement the element: e.g., dark labels on light fills, warm accent on cool elements, or neutral tones against vivid colors. Exception: best/highlight values can use the element's color + bold for emphasis.
ANNOTATION PLACEMENT: annotate/text boxes must NOT overlap axis labels, tick numbers, or extend outside the plot area. If a data point is near the left/bottom edge, place its annotation to the RIGHT or ABOVE (not left/below where it will cover the axis). Use `ax.get_xlim()`/`ax.get_ylim()` to check boundaries. Always call `fig.tight_layout()` or `bbox_inches='tight'` to prevent clipping.
⛔ NEVER place text outside axes with y>1.0 in axes transform (e.g., y=1.02 + transform=ax.get_xaxis_transform()). tight_layout() will shrink the axes to make room, causing the text to 'float' far above the plot. Instead, place annotations INSIDE the axes using data coordinates.

## ⛔ MANDATORY: READ RECIPE BEFORE WRITING FIGURE SCRIPTS
1. `cat _utils/FIGURE_QUICK_REF.md` (small file, 2 seconds)
2. Pick the recipe number from the plan (e.g., `basic #8`, `competition #16`)
3. `python _utils/get_recipe.py basic 8` — extracts the full recipe code
4. Copy recipe code → adapt to your data
5. `bash _utils/figure_check.sh` before executing
**Skip this = ugly figures with wrong colors.**
Recipe files: basic(12), advanced(17), competition(27), academic(12), empirical(16) = 84 total.

## INACTIVITY TIMEOUT WARNING
The system monitors your stdout output. If **no output is detected for 5 minutes**, your process will be killed automatically. To prevent this:
- Print progress messages using `echo` in Bash before long operations (WebSearch, WebFetch)
- If a WebSearch or WebFetch call is slow or fails, skip it and move on immediately
- Never wait indefinitely for a network response
