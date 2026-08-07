# 禁止残留 LaTeX 命令
if grep -qE '\\(begin|end|input|cite|ref|label|includegraphics|section|chapter|subsection)\{' paper/main.md 2>/dev/null; then
    echo "❌ paper/main.md 残留 LaTeX 命令，必须改成 markdown"
    grep -nE '\\(begin|end|input|cite|ref|label|includegraphics|section|chapter|subsection)\{' paper/main.md | head -5
    PASS=false
fi

# 禁止生成 .tex
if ls paper/*.tex paper/sections/*.tex 2>/dev/null | head -1 | grep -q .; then
    echo "❌ 检测到 .tex 文件，docx 模式禁止产 LaTeX："
    ls paper/*.tex paper/sections/*.tex 2>/dev/null
    PASS=false
fi

[ "$PASS" != true ] && echo "⛔ 产出验证失败 — 必须补全后重新跑验证，不要结束本步骤"
```

**如果验证失败，继续修正而不是退出。**

## docx-cn-engine 的 markdown 约定（必须遵守）

后续 `docx-format-check` 步骤用 `tools/docx-cn-engine/md_to_docx.js` 把 main.md 转 .docx。引擎对以下 markdown 语法有特殊处理，**必须按规范写**：

### 1. 标题层级
- `# 论文标题` — 论文封面标题（**全文唯一**，居中、加粗、最大字号）
- `## 章节名` — 一级章节（如「1 引言」、「2 方法」）
- `### 子章节名` — 二级章节
- `#### 三级` — 三级章节

### 2. 摘要 / Abstract（引擎自动识别居中样式）
```markdown
## 摘要

[500-700 字摘要正文，研究背景 → 现有方法不足 → 本文方法 → 数据来源 → 关键数值结果 → 应用价值]

**关键词**：关键词1；关键词2；关键词3；关键词4；关键词5

## Abstract

