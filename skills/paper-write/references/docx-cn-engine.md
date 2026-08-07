## docx-cn-engine markdown conventions

The downstream `docx-format-check` step uses `tools/docx-cn-engine/md_to_docx.js`. Follow these conventions:

### 1. Headings
- `# Paper Title` — paper title (unique, centered, largest)
- `## 1. Introduction` — top-level section
- `### 1.1 Subsection`
- `#### Sub-subsection`

### 2. Abstract (engine auto-centers)
```markdown
## Abstract

[150-250 word abstract]

**Keywords**: kw1; kw2; kw3
```

### 3. Math
- Inline: `$x^2 + y^2 = r^2$`
- Display: `$$ \nabla_\theta L(\theta) = \mathbb{E}[\dots] \quad (1) $$`
- Number on right by appending `(1)`, `(2)` after `$$ ... $$`

⛔ **Never use** `\begin{equation}`, `\[...\]`, `\begin{align}` — engine doesn't render those.

### 4. Figures
```markdown
![Figure 1: Architecture overview.](figures/fig_arch.png)
```
- Alt text becomes the caption (centered, bold)
- Path relative to workspace root
- Prefer `.png`; `.pdf` works but Word renders PNG better

### 5. Tables (3-line academic style)
```markdown
**Table 1: Main results.**

| Method | Accuracy | F1 | Time(s) |
|--------|----------|----|---------|
| Baseline | 0.823 | 0.811 | 124 |
| Ours | **0.917** | **0.905** | 132 |
```

⛔ **Never use** `\begin{table}` or `\input{figures/TABLE_x.tex}`. If `figures/TABLE_*.md` exists, paste its content.

### 6. References
```markdown
## References

[1] LeSage J P, Pace R K. Introduction to Spatial Econometrics. CRC Press, 2009.
[2] Vaswani A, Shazeer N, Parmar N, et al. Attention is all you need. NeurIPS, 2017.
