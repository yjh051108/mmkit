# LaTeX 残留检查
if grep -qE '\\(begin|end|input|cite|ref|label|includegraphics|section|chapter|subsection|bibitem|usepackage|documentclass)\{' paper/main.md; then
    echo "❌ paper/main.md 残留 LaTeX 命令："
    grep -nE '\\(begin|end|input|cite|ref|label|includegraphics|section|chapter|subsection|bibitem|usepackage|documentclass)\{' paper/main.md | head -5
    PASS=false
fi

ls paper/*.tex paper/sections/*.tex 2>/dev/null | head -1 | grep -q . && { echo "❌ 检测到 .tex 文件"; PASS=false; } || true

[ "$PASS" != true ] && echo "⛔ 验证失败 — 必须修复后重跑"
```


## docx-cn-engine markdown 约定（必须遵守）

后续 `docx-format-check` 步骤用 `tools/docx-cn-engine/md_to_docx.js` 把 main.md 转成 .docx：

### 1. 标题层级
- `# 论文标题` — 论文封面标题（**全文唯一**，居中加粗最大字号，引擎会按封面样式渲染）
- `## 摘要` / `## Abstract` — 触发居中摘要样式
- `## 1 问题重述` / `## 2 模型假设` — 一级章节
- `### 1.1 子章节` — 二级
- `#### 三级`

数模竞赛章节命名建议：
```
