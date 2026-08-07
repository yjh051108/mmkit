# mmkit — 数学建模竞赛全流程 Skills 包

**mmkit** 是一个开源的 AI Agent 技能包（Skills Kit），为数学建模竞赛（国赛 CUMCM / 美赛 MCM / 数维杯 / 华为杯 / 五一杯 等）与学术论文写作提供**全流程**编排能力：赛题分析 → 建模 → 编码 → 图表 → 论文 → 编译 → 自审迭代，直至产出可提交的 PDF（或 Word）。

> 设计目标：每个子 skill 平级独立、可单独调用，也可由 orchestrator 驱动组成完整流水线。可运行于 Trae / Codex CLI / Claude Code 等任意具备 Bash + 文件读写能力的 Agent 宿主。

## 特性

- 🎯 **全流程编排**：`orchestrator/mm_flow.py` CLI 驱动「赛题分析 → 建模 → 编码 → 图表 → 论文 → 编译」流水线，按步推进、健康检查、一致性检查、检查点确认。
- 🧩 **57 个独立子 skill**：从赛题分析、建模方法、代码编写、图表生成，到中英文论文撰写、docx 导出、文献综述、idea 发现，每个都可脱离流水线单独使用。
- 🗂 **20+ 竞赛模板**：内置 CUMCM / MCM / APMCM / 数维杯 / 华为杯 / 五一杯 / 华数杯等竞赛的 LaTeX 模板与规则（页数限制、格式要求）。
- 🔍 **质量护栏**：健康检查、一致性检查（建模报告 vs 代码数值）、反幻觉检查（"太完美"结果检测）、meta 泄露检查、过度声称检查。
- 🌐 **中英双语**：论文撰写/编译/图表全链路支持中文（XeLaTeX + ctex）与英文（pdflatex）双引擎自动检测。
- 🧪 **外部评审闭环**：`auto-review-loop` 支持任意 OpenAI 兼容 API（OpenAI / DeepSeek / MiniMax / Kimi / GLM / SiliconFlow 等）做多轮自主审稿迭代。

## 快速开始

```bash
# 1. 安装（任选宿主目录，如 Claude Code / Trae 的 skills 目录）
cp -r skills ~/.claude/skills/mmkit

# 2. 启动一场竞赛工作流
python <skill_root>/orchestrator/mm_flow.py start comp_cumcm \
    --problem "A题" --language zh --page-limit 25
```

### mm_flow CLI

| 命令 | 作用 |
|------|------|
| `start <template>` | 启动工作流（按模板插入全部步骤） |
| `next <workflow_id>` | 获取当前待执行步骤（返回 `skill_name`，按需读取对应 SKILL.md） |
| `complete <workflow_id>` | 完成当前步骤（自动跑健康检查） |
| `resolve <workflow_id>` | 处理检查点决策 |
| `status <workflow_id>` | 查询工作流状态 |
| `resume <workflow_id>` | 恢复 zombie 工作流 |
| `health <workflow_id>` | 对所有已完成步骤跑健康检查 |

完整启动协议（Phase 0 思维风暴 + 审问式追问）见 `SKILL.md`。

## 目录结构

```
mmkit/
├── SKILL.md                  # 主索引：启动协议、按需加载规则、检查点协议
├── orchestrator/             # 流水线编排（mm_flow CLI + 状态存储 + 健康/一致性检查）
├── skills/                   # 57 个平级子 skill（每个含 SKILL.md，可独立使用）
├── shared/                   # 共享工具：图表风格指南、绘图配方、编译/写作检查脚本
├── templates/                # workflow_templates.json（流水线模板）+ competition_rules.json（竞赛规则）
└── references/               # MCP 配置说明、健康规则、技能注册表、启动清单
```

### 子 skill 分类

- **竞赛全流程**：comp-prob-analysis → comp-modeling → comp-code → paper-figure → comp-paper-zh/en → comp-compile
- **论文写作**：paper-plan（research/zh 双模式）→ paper-write / paper-write-zh / paper-write-nature（LaTeX + docx 双模式）→ paper-compile
- **图表**：paper-figure（数据图 / DrawIO / TikZ 双模式）、nature-figure
- **科研工作流**：literature-review（中文 / research / 通信领域三模式）、idea-discovery（含机器人领域模式）、novelty-check、research-review、experiment-plan/run/bridge
- **文档格式**：docx-format-check、docx-template-map、format-profile、paper-poster/slides

## 环境要求

- **宿主**：支持 Bash 工具调用 + 文件读写的任意 Agent（Trae / Codex CLI / Claude Code）
- **可选**：`zotero` MCP（仅文献综述类子 skill 需要，竞赛流程不依赖）
- **外部评审**（可选）：`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `REVIEWER_MODEL_ID` 环境变量

## 常见问题

- **为什么有时跳过某些 MCP？** 本 kit 面向通用宿主设计，子 skill 内可能提及的专用 MCP（obsidian-vault / codex / claude-review 等）一律作废，改用宿主原生能力，见主 `SKILL.md` 的说明。
- **docx 怎么导出？** `output_format == 'docx'` 时论文类 skill 产出 `paper/main.md`，由 docx-cn-engine 约定（见各 skill 的 `references/docx-*.md`）保证 Markdown 可被 Word 转换。

## 贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## License

[MIT](./LICENSE) © yjh051108
