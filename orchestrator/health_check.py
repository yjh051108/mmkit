from __future__ import annotations

"""产物健康检查独立脚本。

从桌面应用 backend_source/services/workflow_engine.py 中迁移产物健康检查逻辑，
去除对 services/state_store/config 等模块的依赖，仅依赖 Python 标准库。

提供：
- check_step(workspace, skill_name): 检查指定 skill 的产物完整性
- check_figure_manifest(workspace, plan_file): 检查 FIGURE_MANIFEST 图表清单
- check_comp_code_problems(workspace): 检查 comp-code 子问题对账

CLI 接口：
    python health_check.py <workspace> <skill_name>
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# DrawIO/架构图文件名前缀（迁移自 workflow_engine.py _DRAWIO_FIG_PREFIXES）
_DRAWIO_FIG_PREFIXES = (
    "fig_arch", "fig_flow", "fig_roadmap", "fig_pipeline", "fig_framework",
    "fig_er", "fig_overview", "fig_system", "fig_module", "fig_index",
    "fig_hierarchy", "fig_multiagent", "fig_topology", "fig_dataflow",
    "fig_pkg", "fig_class", "fig_seq", "fig_gantt", "fig_network",
    "fig_model_decision", "fig_decision", "fig_state", "fig_uml", "tikz_",
)

# 数据图支持的图像扩展名（迁移自 workflow_engine.py _FIG_IMG_EXTS）
_FIG_IMG_EXTS = (".png", ".pdf", ".jpg", ".jpeg", ".svg")

# 每个 skill 的主产物最小字节数（迁移自 workflow_engine.py _STEP_MIN_SIZE）
_STEP_MIN_SIZE = {
    "comp-prob-analysis": 1500, "comp-modeling": 2000, "comp-code": 1000,
    "comp-stats-topic": 1000, "comp-paper-zh": 10000,
    "comp-paper-en": 10000, "paper-write": 15000,
    "paper-write-zh": 15000, "paper-write-nature": 15000,
    "paper-plan": 1000,
    "paper-analysis": 1000, "course-plan": 800,
    "course-paper": 5000, "course-report": 5000,
    "course-report-plan": 800, "thesis-proposal": 2000,
    "literature-review": 2000, "idea-creator": 1500,
    "novelty-check": 800, "research-review": 800,
    "research-refine-pipeline": 1500, "auto-review-loop": 1000,
    "auto-paper-improvement-loop": 50000, "comp-compile": 30000,
    "paper-compile": 30000, "assets-inventory": 500,
    "format-profile": 300, "docx-template-map": 100,
    "docx-format-check": 200,
    "experiment-bridge": 500, "paper-figure": 500,
    "nature-figure": 500,
}

# 每个 skill 必须额外存在的伴生文件（迁移自 workflow_engine.py _STEP_REQUIRED_COMPANIONS）
_STEP_REQUIRED_COMPANIONS = {
    "comp-code": ["code/main.py", "figures/all_results.json"],
}

# 每个 skill 的主产物相对路径（来源：_comp_zh_steps / _comp_en_steps）
_PRIMARY_OUTPUTS = {
    "comp-prob-analysis": "PROBLEM_ANALYSIS.md",
    "comp-modeling": "MODELING_REPORT.md",
    "comp-code": "RESULTS.md",
    "comp-paper-zh": "paper/main.tex",
    "comp-paper-en": "paper/main.tex",
    "comp-compile": "paper/main.pdf",
    "paper-figure": "figures/",
}

# FIGURE_MANIFEST 区块正则（迁移自 workflow_engine.py _read_figure_manifest）
_MANIFEST_BLOCK_RE = re.compile(
    r"<!--\s*BEGIN\s+FIGURE_MANIFEST\s*-->(.*?)<!--\s*END\s+FIGURE_MANIFEST\s*-->",
    re.IGNORECASE | re.DOTALL,
)
_MANIFEST_ITEM_RE = re.compile(r"^\s*-\s+([A-Za-z0-9_-]+)\s*$")

# 子问题数量识别正则（从 MODELING_REPORT.md 中提取）
_PROB_ZH_RE = re.compile(r"问题[一二三四五六七八九十]+")
_PROB_EN_RE = re.compile(r"problem\s*(\d+)", re.IGNORECASE)


def _is_drawio_fig(rel_path: str) -> bool:
    """判断文件是否属于架构/drawio 图（迁移自 workflow_engine.py _is_drawio_fig）。"""
    stem = Path(str(rel_path).replace("\\", "/")).stem.lower()
    return any(stem.startswith(prefix) for prefix in _DRAWIO_FIG_PREFIXES)


def _min_size_for(skill_name: str) -> int:
    """返回指定 skill 的主产物最小字节数。"""
    return int(_STEP_MIN_SIZE.get(skill_name, 100))


def _required_companions_for(skill_name: str) -> list:
    """返回指定 skill 必须额外存在的伴生文件清单。"""
    return list(_STEP_REQUIRED_COMPANIONS.get(skill_name, ()))


def _primary_output_for(skill_name: str) -> Optional[str]:
    """返回指定 skill 的主产物相对路径。"""
    return _PRIMARY_OUTPUTS.get(skill_name)


def _read_figure_manifest_block(
    workspace: Path, plan_file: Optional[str] = None
) -> list:
    """从指定文档中提取 FIGURE_MANIFEST 区块内的图表名称清单。

    若 plan_file 为 None，则依次尝试 PROBLEM_ANALYSIS.md / PAPER_PLAN.md /
    MODELING_REPORT.md。
    """
    names: list = []
    if plan_file:
        candidates = [plan_file]
    else:
        candidates = ["PROBLEM_ANALYSIS.md", "PAPER_PLAN.md", "MODELING_REPORT.md"]

    for filename in candidates:
        path = Path(workspace) / filename
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for block in _MANIFEST_BLOCK_RE.findall(text):
            for line in block.splitlines():
                match = _MANIFEST_ITEM_RE.match(line)
                if match and match.group(1) not in names:
                    names.append(match.group(1))
    return names


def check_figure_manifest(workspace, plan_file=None) -> dict:
    """检查 FIGURE_MANIFEST 区块中规划的图表是否都存在。

    Args:
        workspace: 工作目录路径（Path 对象或字符串）。
        plan_file: 指定文档文件名，若为 None 则依次尝试
            PROBLEM_ANALYSIS.md / PAPER_PLAN.md / MODELING_REPORT.md。

    Returns:
        dict: {
            "pass": bool,
            "expected": [str],   # 清单中规划的非 drawio 数据图名称
            "missing": [str]     # 缺失的图表名称
        }
    """
    root = Path(workspace)
    names = _read_figure_manifest_block(root, plan_file)
    # 仅校验数据图（drawio/tikz 架构图不在此校验范围）
    data_names = [n for n in names if not _is_drawio_fig(n)]

    figures_dir = root / "figures"
    suffixes = _FIG_IMG_EXTS + (".drawio", ".tex", ".webp")
    missing: list = []
    for raw_name in data_names:
        name = Path(str(raw_name)).stem
        found = any(
            (figures_dir / f"{name}{suffix}").is_file() for suffix in suffixes
        )
        if not found and figures_dir.is_dir():
            found = any(
                p.is_file() and p.stem.lower() == name.lower()
                for p in figures_dir.iterdir()
            )
        if not found:
            missing.append(raw_name)

    return {
        "pass": not missing,
        "expected": data_names,
        "missing": missing,
    }


def check_comp_code_problems(workspace) -> dict:
    """对账 comp-code 子问题数量。

    从 MODELING_REPORT.md 中识别子问题数 N（优先匹配 "问题一/二/..." 等
    中文序号，再回退到 "Problem 1/2/..." 等英文序号），然后校验：
    - code/problem*.py 文件数 >= N
    - figures/problem_*_results.json 文件数 >= N

    Args:
        workspace: 工作目录路径（Path 对象或字符串）。

    Returns:
        dict: {
            "pass": bool,
            "expected_count": int,  # 从报告中识别出的子问题数
            "actual_code": int,     # code/problem*.py 文件数
            "actual_json": int      # figures/problem_*_results.json 文件数
        }
    """
    root = Path(workspace)
    expected_count = 0

    report_path = root / "MODELING_REPORT.md"
    if report_path.is_file():
        try:
            text = report_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # 优先中文序号
        zh_hits = _PROB_ZH_RE.findall(text)
        if zh_hits:
            expected_count = len(set(zh_hits))
        else:
            # 回退英文序号
            en_hits = _PROB_EN_RE.findall(text)
            if en_hits:
                try:
                    expected_count = len(set(int(n) for n in en_hits))
                except ValueError:
                    expected_count = 0

    code_dir = root / "code"
    actual_code = 0
    if code_dir.is_dir():
        actual_code = len(list(code_dir.glob("problem*.py")))

    figures_dir = root / "figures"
    actual_json = 0
    if figures_dir.is_dir():
        actual_json = len(list(figures_dir.glob("problem_*_results.json")))

    # 若未识别出子问题数，则跳过对账（视为通过）
    if expected_count == 0:
        passed = True
    else:
        passed = actual_code >= expected_count and actual_json >= expected_count

    return {
        "pass": passed,
        "expected_count": expected_count,
        "actual_code": actual_code,
        "actual_json": actual_json,
    }


def check_step(workspace, skill_name) -> dict:
    """检查指定 skill 的产物健康度。

    检查内容：
    1. 主产物 primary_output 是否存在，以及是否达到最小字节数。
    2. _STEP_REQUIRED_COMPANIONS 中要求的伴生文件是否存在（且 > 50 字节）。
    3. 对 comp-prob-analysis：检查 FIGURE_MANIFEST 区块存在性，且图表数 >= 3。
    4. 对 comp-code：检查 code/main.py >= 500 字节、figures/all_results.json
       存在，以及子问题数对账。

    Args:
        workspace: 工作目录路径（Path 对象或字符串）。
        skill_name: skill 名称，例如 comp-prob-analysis / comp-code。

    Returns:
        dict: {
            "pass": bool,
            "issues": [str],
            "checks": [
                {"name": str, "pass": bool, "detail": str}, ...
            ]
        }
    """
    root = Path(workspace)
    checks: list = []
    issues: list = []

    # 1. 主产物检查
    primary = _primary_output_for(skill_name)
    if primary:
        path = root / primary.rstrip("/\\")
        if primary.endswith(("/", "\\")):
            # 目录型主产物：要求目录存在且非空
            if not path.is_dir() or not any(p.is_file() for p in path.rglob("*")):
                checks.append({
                    "name": "primary_output",
                    "pass": False,
                    "detail": f"主输出目录为空或不存在: {primary}",
                })
                issues.append(f"主输出目录为空或不存在: {primary}")
            else:
                checks.append({
                    "name": "primary_output",
                    "pass": True,
                    "detail": f"主输出目录存在: {primary}",
                })
        elif not path.is_file():
            checks.append({
                "name": "primary_output",
                "pass": False,
                "detail": f"缺少主输出: {primary}",
            })
            issues.append(f"缺少主输出: {primary}")
        else:
            size = path.stat().st_size
            min_size = _min_size_for(skill_name)
            if size < min_size:
                checks.append({
                    "name": "primary_output",
                    "pass": False,
                    "detail": f"主输出过小: {primary} ({size} 字节 < {min_size})",
                })
                issues.append(f"主输出过小: {primary} ({size} 字节 < {min_size})")
            else:
                checks.append({
                    "name": "primary_output",
                    "pass": True,
                    "detail": f"主输出正常: {primary} ({size} 字节)",
                })
    else:
        # 未知 skill：跳过主产物检查
        checks.append({
            "name": "primary_output",
            "pass": True,
            "detail": f"未配置 {skill_name} 的主产物路径，跳过",
        })

    # 2. 伴生文件检查
    companions = _required_companions_for(skill_name)
    if companions:
        missing: list = []
        for rel in companions:
            path = root / rel
            if not path.exists() or not path.is_file():
                missing.append(f"{rel} (不存在)")
                continue
            size = path.stat().st_size
            if size <= 50:
                missing.append(f"{rel} (过小: {size} 字节)")
        if missing:
            checks.append({
                "name": "required_companions",
                "pass": False,
                "detail": "; ".join(missing),
            })
            issues.extend(missing)
        else:
            checks.append({
                "name": "required_companions",
                "pass": True,
                "detail": f"伴生文件齐全: {', '.join(companions)}",
            })
    else:
        checks.append({
            "name": "required_companions",
            "pass": True,
            "detail": f"{skill_name} 无额外伴生文件要求",
        })

    # 3. comp-prob-analysis 专项：FIGURE_MANIFEST 区块存在性 + 图表数 >= 3
    if skill_name == "comp-prob-analysis":
        manifest_result = check_figure_manifest(root)
        names = manifest_result["expected"]
        if not names:
            checks.append({
                "name": "figure_manifest",
                "pass": False,
                "detail": "PROBLEM_ANALYSIS.md 中缺少 FIGURE_MANIFEST 区块",
            })
            issues.append("PROBLEM_ANALYSIS.md 中缺少 FIGURE_MANIFEST 区块")
        elif len(names) < 3:
            checks.append({
                "name": "figure_manifest",
                "pass": False,
                "detail": f"FIGURE_MANIFEST 图表数不足: {len(names)} < 3",
            })
            issues.append(f"FIGURE_MANIFEST 图表数不足: {len(names)} < 3")
        else:
            checks.append({
                "name": "figure_manifest",
                "pass": True,
                "detail": f"FIGURE_MANIFEST 图表数 {len(names)} >= 3",
            })

    # 4. comp-code 专项：code/main.py >= 500 字节 + figures/all_results.json + 子问题对账
    if skill_name == "comp-code":
        # code/main.py 体积
        main_py = root / "code" / "main.py"
        if not main_py.is_file():
            checks.append({
                "name": "code_main_py_size",
                "pass": False,
                "detail": "缺少 code/main.py",
            })
            issues.append("缺少 code/main.py")
        else:
            size = main_py.stat().st_size
            if size < 500:
                checks.append({
                    "name": "code_main_py_size",
                    "pass": False,
                    "detail": f"code/main.py 过小: {size} 字节 < 500",
                })
                issues.append(f"code/main.py 过小: {size} 字节 < 500")
            else:
                checks.append({
                    "name": "code_main_py_size",
                    "pass": True,
                    "detail": f"code/main.py 体积正常: {size} 字节",
                })

        # figures/all_results.json 存在性
        all_results = root / "figures" / "all_results.json"
        if not all_results.is_file():
            checks.append({
                "name": "all_results_json",
                "pass": False,
                "detail": "缺少 figures/all_results.json",
            })
            issues.append("缺少 figures/all_results.json")
        else:
            checks.append({
                "name": "all_results_json",
                "pass": True,
                "detail": "figures/all_results.json 存在",
            })

        # 子问题对账
        prob_result = check_comp_code_problems(root)
        detail = (
            f"子问题对账: 期望 {prob_result['expected_count']}，"
            f"代码 {prob_result['actual_code']}，"
            f"JSON {prob_result['actual_json']}"
        )
        if not prob_result["pass"]:
            checks.append({
                "name": "comp_code_problems",
                "pass": False,
                "detail": "失败 - " + detail,
            })
            issues.append("子问题对账失败: " + detail)
        else:
            checks.append({
                "name": "comp_code_problems",
                "pass": True,
                "detail": "通过 - " + detail,
            })

    return {
        "pass": not issues,
        "issues": issues,
        "checks": checks,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="health_check.py",
        description="产物健康检查独立工具（从 workflow_engine.py 迁移）。",
    )
    parser.add_argument("workspace", help="工作目录路径")
    parser.add_argument("skill_name", help="skill 名称，例如 comp-prob-analysis")
    return parser


def main(argv: Optional[list] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    result = check_step(args.workspace, args.skill_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
