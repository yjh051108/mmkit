# 子 Skill 索引

> 本文档供 agent 阅读。列出 `skills/` 目录下全部 70 个子 skill，按功能分类组织。
>
> **产物契约**列来自 `health_check.py` 的 `_STEP_MIN_SIZE` / `_STEP_REQUIRED_COMPANIONS` / `_PRIMARY_OUTPUTS`。标注"（无特殊要求）"表示该 skill 未在健康检查中配置主产物阈值，健康检查跳过主产物验证。
>
> 源目录：`skills/`

---

## 竞赛类

| skill_name | 描述 | 触发条件 | 产物契约 |
|---|---|---|---|
| comp-prob-analysis | 数学建模竞赛赛题分析。拆解子问题、定义变量、拟定建模思路 | "赛题分析"、"problem analysis"、"分析题目" | `PROBLEM_ANALYSIS.md` ≥ 1500 字节；FIGURE_MANIFEST 图表 ≥ 3 |
| comp-modeling | 数学建模竞赛核心建模与求解。建立数学模型、推导公式、设计算法 | "建模"、"modeling"、"模型建立" | `MODELING_REPORT.md` ≥ 2000 字节 |
| comp-code | 数学建模竞赛编程实现。根据建模报告编写代码、执行计算、收集结果 | "编程"、"写代码"、"code implementation" | `RESULTS.md` ≥ 1000 字节；伴生 `code/main.py` ≥ 500 字节 + `figures/all_results.json`；子问题对账 |
| comp-stats-topic | 统计建模大赛选题与数据规划。自拟题目、设计研究方案、规划数据来源 | "统计建模选题"、"stats topic"、"自拟题目" | 主产物 ≥ 1000 字节 |
| comp-paper-zh | 数学建模竞赛/统计建模中文论文撰写。按竞赛规范结构生成完整 LaTeX 论文 | "写竞赛论文"、"competition paper"、"建模论文" | `paper/main.tex` ≥ 10000 字节 |
| comp-paper-en | Mathematical modeling competition paper writing in English (MCM/ICM/APMCM) | "write MCM paper"、"美赛论文"、"English competition paper" | `paper/main.tex` ≥ 10000 字节 |
| comp-compile | 数学建模竞赛中文论文编译与合规检查（页数、匿名、格式） | "编译竞赛论文"、"compile competition paper" | `paper/main.pdf` ≥ 30000 字节 |
| comp-compile | Compile English competition paper (MCM/ICM/APMCM) and run compliance checks | "compile MCM paper"、"编译美赛论文" | `paper/main.pdf` ≥ 30000 字节 |

---

## 论文类

| skill_name | 描述 | 触发条件 | 产物契约 |
|---|---|---|---|
| paper-plan | 从审稿结论和实验结果生成结构化论文大纲 | "paper outline"、"plan the paper" | 主产物 ≥ 1000 字节 |
| paper-plan | 生成结构化中文论文大纲 | "中文大纲"、"中文论文规划"、"Chinese paper outline" | 主产物 ≥ 1000 字节 |
| paper-write | 逐节起草 LaTeX 论文（ICLR/NeurIPS/ICML） | "write paper"、"draft LaTeX" | 主产物 ≥ 15000 字节 |
| paper-write-zh | 用 XeLaTeX + ctex 起草中文学术论文 | "写中文论文"、"中文LaTeX"、"Chinese paper writing" | 主产物 ≥ 15000 字节 |
| paper-write-nature | 起草 Nature 风格 LaTeX 论文（沙漏结构、读者优先逻辑） | "Nature paper"、"Nature writing"、"SCI writing" | 主产物 ≥ 15000 字节 |
| paper-compile | 使用 pdflatex 编译英文 LaTeX 论文为 PDF | "compile paper"、"build PDF" | 主产物 ≥ 30000 字节 |
| paper-compile | 使用 XeLaTeX 编译中文 LaTeX 论文为 PDF | "编译中文论文"、"compile Chinese paper"、"中文PDF" | 主产物 ≥ 30000 字节 |
| paper-writing | 论文全流程编排：paper-plan → paper-figure → paper-write → paper-compile → auto-paper-improvement-loop | "写论文全流程"、"write paper pipeline"、"从报告到PDF" | （无特殊要求） |
| paper-analysis | 论文数据分析与建模。执行数据处理、统计分析、模型训练 | 有论文大纲需要数据分析时 | 主产物 ≥ 1000 字节 |
| paper-slides | 从已编译论文生成会议演讲幻灯片（beamer → PDF + PPTX + 演讲稿） | "做PPT"、"做幻灯片"、"make slides"、"conference talk" | （无特殊要求） |
| paper-poster | 从已编译论文生成会议海报（A0/A1 PDF + PPTX + SVG） | "做海报"、"制作海报"、"conference poster"、"make poster" | （无特殊要求） |
| thesis-proposal | 开题报告撰写。生成完整学位论文开题报告 | "开题报告"、"thesis proposal"、"开题" | 主产物 ≥ 2000 字节 |
| grant-proposal | 起草结构化基金申请书（KAKENHI/NSF/NSFC/ERC/DFG 等） | "write grant"、"grant proposal"、"写基金"、"NSF proposal" | （无特殊要求） |
| course-paper | 课程论文撰写。基于大纲和数据分析撰写完整正文 | 课程论文工作流续接 | 主产物 ≥ 5000 字节 |
| course-plan | 课程论文大纲规划。产出大纲、数据分析规划、图表规划 | 课程论文工作流启动 | 主产物 ≥ 800 字节 |
| course-report | 课程报告撰写。基于项目事实底稿、大纲、数据撰写完整正文 | 课程报告工作流续接 | 主产物 ≥ 5000 字节 |
| course-report-plan | 课程报告大纲规划。提取项目事实，产出大纲与图表规划 | 课程报告工作流启动 | 主产物 ≥ 800 字节 |

---

## 图表类

| skill_name | 描述 | 触发条件 | 产物契约 |
|---|---|---|---|
| paper-figure | 从实验结果生成出版级图表和数据表 | "画图"、"作图"、"generate figures"、"paper figures" | `figures/` 目录存在且非空；主产物 ≥ 500 字节 |
| paper-figure | 生成 DrawIO 架构图和 TikZ 图表（非数据图） | "画DrawIO"、"技术路线图"、"流程图" | `figures/` 目录存在且非空；主产物 ≥ 500 字节 |
| nature-figure | 生成符合 Nature 期刊标准的出版级 matplotlib 图表 | "Nature figure"、"Nature style plot" | 主产物 ≥ 500 字节 |
| mermaid-diagram | 从用户需求生成 Mermaid 图表（流程图/时序图/类图等），保存 `.mmd` 和 `.md` | 需要流程图/架构图等 | （无特殊要求） |
| pixel-art | 生成像素艺术 SVG 插图，用于 README/文档/幻灯片 | "画像素图"、"pixel art"、"README hero image" | （无特殊要求） |
| paper-illustration | 使用 Gemini 图像生成生成出版级 AI 插图（架构图/方法示意图） | "生成图表"、"画架构图"、"AI绘图"、"paper illustration" | （无特殊要求） |

---

## 研究类

| skill_name | 描述 | 触发条件 | 产物契约 |
|---|---|---|---|
| literature-review | 搜索和分析研究论文，查找相关工作，总结关键想法 | "find papers"、"related work"、"literature review" | 主产物 ≥ 1500 字节 |
| research-pipeline | 全流程编排：idea discovery → 实现 → auto review loop → 投稿 | "全流程"、"full pipeline"、"从找idea到投稿" | （无特殊要求） |
| research-refine | 将模糊研究方向转化为问题锚定、简洁、前沿的方法方案 | "refine my approach"、"帮我细化方案"、"打磨idea"、"refine research plan" | （无特殊要求） |
| research-refine-pipeline | 串联 research-refine 和 experiment-plan 的一站式流水线 | "串起来"、端到端方法+实验规划 | 主产物 ≥ 1500 字节 |
| research-review | 通过外部审稿人获取深度批判性评审 | "review my research"、"help me review"、"get external review" | 主产物 ≥ 800 字节 |
| idea-creator | 给定大方向生成并排序研究 idea | "找idea"、"brainstorm ideas"、"generate research ideas" | 主产物 ≥ 1500 字节 |
| idea-discovery | 全流程 idea 发现：literature-review → idea-creator → novelty-check → research-review | "找idea全流程"、"idea discovery pipeline"、"从零开始找方向" | （无特殊要求） |
| novelty-check | 验证研究 idea 相对近期文献的新颖性 | "查新"、"novelty check"、"有没有人做过"、"check novelty" | 主产物 ≥ 800 字节 |
| literature-review | 文献综述撰写。检索文献、验证真实性、分类、撰写综合综述 | "文献综述"、"literature review"、"综述" | 主产物 ≥ 2000 字节 |
| literature-review | 通信领域文献综述（Claude 风格知识库优先检索） | 通信/无线/网络/卫星/路由等通信系统研究 | （无特殊要求） |
| arxiv | 从 arXiv 搜索、下载、总结学术论文 | "search arxiv"、"download paper"、"fetch arxiv"、"arxiv search" | （无特殊要求） |
| experiment-bridge | 实现实验、运行代码、收集结果、生成出版级图表 | "实现实验"、"implement experiments"、"bridge"、"跑实验出图"、"run experiments" | 主产物 ≥ 500 字节 |
| experiment-plan | 将研究方案转化为详细的 claim 驱动实验路线图 | research-refine 后、需要详细实验计划/消融矩阵/评估协议 | （无特殊要求） |
| run-experiment | 在本地或远程 GPU 服务器部署运行 ML 实验 | "run experiment"、"deploy to server"、"跑实验" | （无特殊要求） |
| monitor-experiment | 监控运行中的实验，检查进度，收集结果 | "check results"、"is it done"、"monitor" | （无特殊要求） |
| analyze-results | 分析 ML 实验结果，计算统计量，生成对比表和洞察 | "analyze results"、"compare"、需要解释实验数据 | （无特殊要求） |
| result-to-claim | 判断实验结果支持哪些 claim，不支持哪些，缺什么证据 | 实验完成后、写论文/跑消融前 | （无特殊要求） |
| ablation-planner | 从审稿人视角设计消融实验，CC 审查可行性并实现 | 主结果通过 result-to-claim 后、需要消融实验 | （无特殊要求） |
| training-check | 定期检查 WandB 指标，及早发现训练问题（NaN/loss 发散/GPU 空闲） | 训练运行中需要自动化健康检查 | （无特殊要求） |
| dse-loop | 计算机架构和 EDA 的自主设计空间探索循环 | "DSE"、"design space exploration"、"sweep parameters"、"optimize" | （无特殊要求） |
| auto-review-loop | 自主多轮研究审稿循环：审稿 → 修复 → 再审稿，直到通过或达上限 | "auto review loop"、"review until it passes" | 主产物 ≥ 1000 字节 |
| auto-paper-improvement-loop | 自主改进已生成论文：审稿 → 修复 → 重编译，2 轮 | "改论文"、"improve paper"、"论文润色循环"、"auto improve" | 主产物 ≥ 50000 字节 |
| rebuttal | 投稿 rebuttal 流水线：解析评审 → 覆盖检查 → 起草安全 rebuttal | "rebuttal"、"reply to reviewers"、"ICML rebuttal"、"OpenReview response" | （无特殊要求） |
| proof-writer | 为 ML/AI 理论撰写严格数学证明 | 被要求证明定理/引理/命题，或补全证明步骤 | （无特殊要求） |

---

## 其他

| skill_name | 描述 | 触发条件 | 产物契约 |
|---|---|---|---|
| assets-inventory | 扫描用户上传资产（题目/代码/数据/图/结果），输出资产清单与冲突报告 | "资产清点"、"assets inventory"、"已有资产" | 主产物 ≥ 500 字节 |
| format-profile | 根据文字格式要求或格式说明文档，生成 docx-format-check 用的样式 profile JSON | 需要 docx 导出样式配置 | 主产物 ≥ 300 字节 |
| docx-template-map | 分析 .docx/.dotx 模板，识别占位段位置，生成 `_template_map.json` | "分析 word 模板"、"识别模板占位"、"docx-template-map" | 主产物 ≥ 100 字节 |
| docx-format-check | 导出 Word 前的 Markdown 格式自检与修复 | "docx 自检"、"word 格式检查"、"docx-format-check" | 主产物 ≥ 200 字节 |
| editor-agent | 论文编辑器 AI 助手（Agent 模式），可读写文件、跑 Python、编译 LaTeX 或导出 Word | 需要 Agent 模式的论文编辑 | （无特殊要求） |
| feishu-notify | 发送飞书/Lark 通知（webhook 推送或交互模式） | "发飞书"、"notify feishu"、其他 skill 需要状态更新 | （无特殊要求） |
| quality-check | 学术写作质量审查。检查字数、结构、引用、格式问题并生成审查报告 | "质量检查"、"quality check"、"审稿"、"review" | （无特殊要求） |

---

## 统计

| 分类 | 数量 |
|------|-----:|
| 竞赛类 | 10 |
| 论文类 | 20 |
| 图表类 | 6 |
| 研究类 | 27 |
| 其他 | 7 |
| **合计** | **70** |
