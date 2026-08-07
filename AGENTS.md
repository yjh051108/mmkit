# mmkit

本目录是一个自包含的 skills 包，用于数学建模竞赛全流程自动化。

## 如何使用

1. **读 SKILL.md**：这是索引入口。读 `SKILL.md` 了解 skill 清单、启动协议和编排协议。
2. **调 CLI**：通过 Bash 调用 `orchestrator/mm_flow.py` 驱动工作流。
3. **读子 skill**：按 `mm_flow next` 返回的 skill_name，读 `skills/<skill_name>/SKILL.md`。每个子 skill 独立可用。

## 目录结构

- `SKILL.md` — 索引入口（skill 清单 + 启动协议 + 编排协议）
- `preamble.md` — 全局执行上下文（Python/XeLaTeX 路径、配色规则、recipe 系统）
- `orchestrator/` — CLI 编排核心（mm_flow.py / state_store.py / health_check.py / consistency_check.py / vision.py / pdf_extract.py / reviewer.py）
- `templates/` — 工作流模板和竞赛规则（workflow_templates.json / competition_rules.json）
- `skills/` — 70 个平级子 skill（每个独立可用，按需读取）
- `shared/` — 共享脚本（figure_check.py / plot_utils.py / figure_recipes_*.md 等）
- `references/` — 编排层参考文档（workflow_rules.md / health_rules.md / skill_registry.md / startup_checklist.md / mcp_setup.md）

## 快速开始

```bash
# 1. 启动工作流
python orchestrator/mm_flow.py start comp_cumcm --workspace . --language zh --competition comp_cumcm --problem "你的赛题文本"

# 2. 获取第一个 step
python orchestrator/mm_flow.py next <workflow_id>

# 3. 读对应 skill 的 SKILL.md 执行任务
# 4. 完成后触发健康检查 + 一致性检查
python orchestrator/mm_flow.py complete <workflow_id>
```

详细协议见 `SKILL.md`。
