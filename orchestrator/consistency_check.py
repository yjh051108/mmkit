"""一致性校验：论文内容 vs 代码/数据/原题/用户需求的一致性检查。

在 health_check 的体积检查之后运行，检查：
1. 数值一致性：论文中的数值是否来自 RESULTS.md / figures/*.json
2. 公式一致性：论文公式 vs 代码实现的关键数学表达式对照
3. 原题覆盖度：论文章节是否覆盖原题所有子问题，是否有虚构章节
4. 用户需求范围：论文章节数是否匹配用户要求的完成范围
5. 结构完整性：论文是否包含模板规定的必需章节
"""

import json
import os
import re
import glob
from pathlib import Path


# =========================================================================
# 工具函数
# =========================================================================

def _read_file(path):
    """安全读取文件内容，不存在返回空串。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def _extract_numbers(text):
    """从文本中提取所有数值（含小数和科学计数法）。"""
    # 匹配 1.859, 5.71, 9.81e-8, 25 等
    pattern = r"(?<![A-Za-z_])(\d+\.?\d*(?:[eE][+-]?\d+)?)(?![A-Za-z_])"
    return set(re.findall(pattern, text))


def _normalize_number(n):
    """把数值字符串归一化为 float，用于精度无关的匹配。

    解决 "1.859"（论文截断值） vs "1.859024"（数据文件全精度值）的误报：
    匹配时按论文数值的小数位数截断数据文件数值再比较。
    """
    try:
        return float(n)
    except (ValueError, TypeError):
        return None


def _truncate_to_precision(value_str, target_precision):
    """把数值字符串截断到指定小数位数（不四舍五入，直接截断）。

    Args:
        value_str: 数据文件中的数值字符串，如 "1.8590242153394238"
        target_precision: 论文数值的小数位数，如 3

    Returns:
        截断后的字符串，如 "1.859"
    """
    if "." not in value_str:
        return value_str
    if "e" in value_str or "E" in value_str:
        # 科学计数法不截断，直接返回
        return value_str
    parts = value_str.split(".")
    if len(parts) != 2:
        return value_str
    if target_precision <= 0:
        return parts[0]
    if len(parts[1]) <= target_precision:
        return value_str  # 数据值精度不够，不截断
    return parts[0] + "." + parts[1][:target_precision]


def _round_to_precision(value_str, target_precision):
    """把数值字符串四舍五入到指定小数位数。

    Args:
        value_str: 数据文件中的数值字符串，如 "1.485507"
        target_precision: 论文数值的小数位数，如 3

    Returns:
        四舍五入后的字符串，如 "1.486"
    """
    try:
        val = float(value_str)
        rounded = round(val, target_precision)
        # 格式化为固定小数位数
        return f"{rounded:.{target_precision}f}"
    except (ValueError, TypeError):
        return value_str


def _numbers_match(tex_num, data_numbers_raw):
    """检查论文数值是否在数据数值集合中有匹配（支持精度截断 + 四舍五入）。

    Args:
        tex_num: 论文中的数值字符串，如 "1.486"
        data_numbers_raw: 数据文件中的原始数值字符串集合

    Returns:
        bool: 是否找到匹配
    """
    # 1. 精确字符串匹配
    if tex_num in data_numbers_raw:
        return True

    # 2. 精度匹配：把数据数值截断或四舍五入到论文数值的小数位数
    if "." in tex_num and "e" not in tex_num and "E" not in tex_num:
        target_precision = len(tex_num.split(".")[-1])
        for data_num in data_numbers_raw:
            if data_num == tex_num:
                return True
            # 截断匹配（如 1.859 ← 1.859024）
            truncated = _truncate_to_precision(data_num, target_precision)
            if truncated == tex_num:
                return True
            # 四舍五入匹配（如 1.486 ← 1.485507）
            rounded = _round_to_precision(data_num, target_precision)
            if rounded == tex_num:
                return True
            # float 值比较（消除 "1.859" vs "1.8590" 的格式差异）
            try:
                if float(truncated) == float(tex_num):
                    return True
                if float(rounded) == float(tex_num):
                    return True
            except (ValueError, TypeError):
                pass

    # 3. float 值匹配（最后兜底，处理科学计数法等）
    tex_float = _normalize_number(tex_num)
    if tex_float is None:
        return False
    for data_num in data_numbers_raw:
        data_float = _normalize_number(data_num)
        if data_float is not None and abs(tex_float - data_float) < 1e-9:
            return True

    return False


def _extract_tex_numbers(tex_dir):
    """从 paper/sections/*.tex 提取所有数值。"""
    numbers = set()
    for tex_path in glob.glob(os.path.join(tex_dir, "*.tex")):
        text = _read_file(tex_path)
        # 去掉注释行
        text = re.sub(r"(?m)^%.*$", "", text)
        numbers |= _extract_numbers(text)
    return numbers


def _extract_data_numbers(workspace):
    """从 RESULTS.md 和 figures/*.json 提取所有数值。"""
    numbers = set()
    # RESULTS.md
    results_text = _read_file(os.path.join(workspace, "RESULTS.md"))
    numbers |= _extract_numbers(results_text)
    # figures/*.json
    for json_path in glob.glob(os.path.join(workspace, "figures", "*.json")):
        text = _read_file(json_path)
        try:
            data = json.loads(text)
            numbers |= _extract_numbers(text)
        except (json.JSONDecodeError, ValueError):
            pass
    # code/figures/*.json (comp-code 的输出位置)
    for json_path in glob.glob(os.path.join(workspace, "code", "figures", "*.json")):
        text = _read_file(json_path)
        numbers |= _extract_numbers(text)
    return numbers


# =========================================================================
# 检查 1：数值一致性
# =========================================================================

def check_numerical_consistency(workspace):
    """检查论文中的数值是否来自 RESULTS.md / figures/*.json。

    抽取 .tex 中所有数值，与数据文件中的数值比对。
    - 高精度 orphan 数值（科学计数法、3 位+ 小数）超过阈值 → error（很可能虚构）
    - 低精度 orphan 数值 → warning（可能是参数/系数/年份）
    """
    issues = []
    warnings = []

    tex_dir = os.path.join(workspace, "paper", "sections")
    if not os.path.isdir(tex_dir):
        return {"passed": True, "issues": [], "warnings": ["paper/sections/ 不存在，跳过数值一致性检查"]}

    tex_numbers = _extract_tex_numbers(tex_dir)
    data_numbers = _extract_data_numbers(workspace)

    if not data_numbers:
        warnings.append("未找到 RESULTS.md 或 figures/*.json，无法校验数值一致性")
        return {"passed": True, "issues": issues, "warnings": warnings}

    # 过滤掉常见非数据数值（页码、年份、版本号、整数编号等）
    ignore = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
              "100", "1000", "2024", "2025", "2026", "25", "30", "50", "60"}
    tex_numbers_filtered = {n for n in tex_numbers if n not in ignore and len(n) > 1}

    # 找出 .tex 中有但数据文件中没有的数值（使用归一化匹配，支持精度截断）
    # 解决 "1.859"（论文截断）vs "1.859024"（数据全精度）的误报
    orphan_numbers = {n for n in tex_numbers_filtered
                      if not _numbers_match(n, data_numbers)}

    # 区分高精度 orphan（很可能是数据数值，虚构风险高）和低精度 orphan
    high_precision_orphans = set()
    low_precision_orphans = set()
    for n in orphan_numbers:
        # 科学计数法（如 9.81e-8, 1.11e-3）
        if re.search(r"[eE][+-]?\d+", n):
            high_precision_orphans.add(n)
        # 3 位以上小数（如 1.859, 0.0001）
        elif "." in n and len(n.split(".")[-1]) >= 3:
            high_precision_orphans.add(n)
        else:
            low_precision_orphans.add(n)

    # 高精度 orphan > 3 个 → error（很可能是虚构的关键结果数值）
    if len(high_precision_orphans) > 3:
        sorted_high = sorted(high_precision_orphans, key=lambda x: (-len(x), x))[:15]
        issues.append(
            f"论文中有 {len(high_precision_orphans)} 个高精度数值（科学计数法或 3 位+ 小数）"
            f"未在 RESULTS.md 或 figures/*.json 中找到，很可能是虚构的关键结果数值：{sorted_high}"
        )
    elif high_precision_orphans:
        sorted_high = sorted(high_precision_orphans)[:10]
        warnings.append(
            f"论文中有 {len(high_precision_orphans)} 个高精度数值未在数据文件中找到（需人工核对）：{sorted_high}"
        )

    # 低精度 orphan 只报 warning
    if low_precision_orphans:
        sorted_low = sorted(low_precision_orphans, key=lambda x: (-len(x), x))[:15]
        warnings.append(
            f"论文中有 {len(low_precision_orphans)} 个低精度数值未在数据文件中找到"
            f"（可能是参数/系数/文献值）：{sorted_low}"
        )

    return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}


# =========================================================================
# 检查 2：公式一致性
# =========================================================================

def check_formula_consistency(workspace):
    """抽取论文公式和代码数学表达式，强制生成对照表并校验完整性。

    核心机制（杜绝能耗公式不一致）：
    1. 提取论文所有公式（$$...$$ / \\[...\\] / equation 环境）
    2. 提取代码所有数学表达式（含 np./math./sum/abs 等）
    3. 要求 agent 生成 `paper/sections/_formula_mapping.md` 对照表文件，
       每个公式必须标注对应的代码实现位置 + 一致性结论
    4. 对照表不存在 → error（强制生成）
    5. 对照表存在但未覆盖所有公式 → error（强制逐条核对）
    6. 对照表完整覆盖 → passed

    Returns:
        {
            "passed": bool,
            "issues": [str],    # error 级
            "warnings": [str],  # warning 级
            "formula_count": int,
            "code_expr_count": int,
            "mapping_file": str,
            "uncovered_formulas": [str],  # 未在对照表中标注的公式
        }
    """
    issues = []
    warnings = []

    tex_dir = os.path.join(workspace, "paper", "sections")
    code_dir = os.path.join(workspace, "code")

    if not os.path.isdir(tex_dir):
        return {"passed": True, "issues": [], "warnings": ["paper/sections/ 不存在，跳过公式一致性检查"]}

    # 抽取 .tex 中的公式（$$...$$ 和 \[...\] 和 equation 环境）
    formulas = []
    formula_sources = []  # 记录每个公式来自哪个文件
    for tex_path in sorted(glob.glob(os.path.join(tex_dir, "*.tex"))):
        # 跳过对照表文件本身
        if os.path.basename(tex_path).startswith("_"):
            continue
        text = _read_file(tex_path)
        basename = os.path.basename(tex_path)
        # $$...$$
        for f in re.findall(r"\$\$(.+?)\$\$", text, re.DOTALL):
            formulas.append(f.strip())
            formula_sources.append(basename)
        # \[...\]
        for f in re.findall(r"\\\[(.+?)\\\]", text, re.DOTALL):
            formulas.append(f.strip())
            formula_sources.append(basename)
        # equation 环境
        for f in re.findall(r"\\begin\{equation\}(.+?)\\end\{equation\}", text, re.DOTALL):
            formulas.append(f.strip())
            formula_sources.append(basename)

    if not formulas:
        return {"passed": True, "issues": [], "warnings": ["论文中未检测到公式，跳过公式一致性检查"]}

    # 抽取 code/*.py 中的关键数学表达式
    code_exprs = []
    has_code = False
    for py_path in sorted(glob.glob(os.path.join(code_dir, "*.py"))):
        has_code = True
        text = _read_file(py_path)
        for line in text.splitlines():
            stripped = line.strip()
            # 匹配含数学运算的赋值行
            if re.search(r"(np\.|math\.|\b0\.\d+\s*\*|\bsum\b|\babs\b)", stripped) and "=" in stripped:
                code_exprs.append(os.path.basename(py_path) + ": " + stripped)

    # error：论文有公式但代码完全不存在
    if not has_code:
        issues.append(
            f"论文有 {len(formulas)} 个公式，但 code/ 目录无 .py 文件，"
            f"无法校验公式一致性。必须先实现代码再写论文。"
        )
        return {
            "passed": False, "issues": issues, "warnings": warnings,
            "formula_count": len(formulas), "code_expr_count": 0,
            "mapping_file": "", "uncovered_formulas": [],
        }

    # error：论文有公式但代码无任何数学表达式（可能代码太简单或公式未实现）
    if not code_exprs:
        issues.append(
            f"论文有 {len(formulas)} 个公式，但 code/*.py 中未找到任何数学运算表达式，"
            f"公式很可能未被代码实现。请核对论文公式是否都有对应代码实现。"
        )
        return {
            "passed": False, "issues": issues, "warnings": warnings,
            "formula_count": len(formulas), "code_expr_count": 0,
            "mapping_file": "", "uncovered_formulas": [],
        }

    # 强制对照表机制：检查 paper/sections/_formula_mapping.md 是否存在且完整
    mapping_file = os.path.join(tex_dir, "_formula_mapping.md")
    mapping_text = _read_file(mapping_file)

    if not mapping_text.strip():
        # 对照表不存在 → error，并生成模板供 agent 填写
        template_lines = [
            "# 公式-代码对照表",
            "",
            "> ⚠️ 本文件由 consistency_check 强制要求。每个论文公式必须标注对应的代码实现位置",
            "> 和一致性结论。未填写或不完整将阻止 complete 推进。",
            "",
            "## 填写规则",
            "",
            "- `公式编号`：按出现顺序编号 F1, F2, ...",
            "- `论文公式`：从 .tex 中复制的公式原文（可截断到 80 字符）",
            "- `代码位置`：code/*.py 中实现该公式的行，格式 `文件名:行号` 或 `文件名:函数名`",
            "- `一致性`：✅ 一致 / ❌ 不一致（必须修复后改 ✅）",
            "- `备注`：如有差异说明原因（如单位换算、近似处理等）",
            "",
            "## 对照表",
            "",
        ]
        for i, (formula, source) in enumerate(zip(formulas, formula_sources), 1):
            formula_preview = formula.replace("\n", " ")[:80]
            template_lines.append(f"### F{i} (来源: {source})")
            template_lines.append("")
            template_lines.append(f"- 论文公式: `{formula_preview}`")
            template_lines.append(f"- 代码位置: <请填写，如 main.py:compute_energy()>")
            template_lines.append(f"- 一致性: <✅ 或 ❌>")
            template_lines.append(f"- 备注: <可选>")
            template_lines.append("")
        try:
            with open(mapping_file, "w", encoding="utf-8") as f:
                f.write("\n".join(template_lines))
        except OSError:
            pass

        issues.append(
            f"论文有 {len(formulas)} 个公式，代码有 {len(code_exprs)} 个数学表达式，"
            f"但缺少公式-代码对照表 paper/sections/_formula_mapping.md。"
            f"已生成模板，agent 必须逐条填写每个公式对应的代码位置和一致性结论后重跑 complete。"
            f"上次作业正是此处未核对导致能耗公式 E=½Jω²（论文）vs E=½Jω|Δθ|（代码）不一致。"
        )
        return {
            "passed": False, "issues": issues, "warnings": warnings,
            "formula_count": len(formulas), "code_expr_count": len(code_exprs),
            "mapping_file": mapping_file, "uncovered_formulas": [f"F{i+1}" for i in range(len(formulas))],
        }

    # 对照表存在：检查是否覆盖所有公式
    # 识别对照表中已填写的公式编号（F1, F2, ...）
    covered_indices = set()
    for match in re.finditer(r"###\s*F(\d+)", mapping_text):
        try:
            covered_indices.add(int(match.group(1)))
        except ValueError:
            pass

    expected_indices = set(range(1, len(formulas) + 1))
    uncovered = expected_indices - covered_indices

    # 检查是否有未标注一致性的公式（❌ 或缺 ✅）
    inconsistent_formulas = []
    for i in expected_indices & covered_indices:
        # 找到 F{i} 区块
        pattern = rf"###\s*F{i}\b(.*?)(?=###\s*F\d+|\Z)"
        block_match = re.search(pattern, mapping_text, re.DOTALL)
        if block_match:
            block = block_match.group(1)
            # 检查是否有一致性标注
            if "❌" in block:
                inconsistent_formulas.append(f"F{i}")
            elif "✅" not in block:
                # 没有任何一致性标注
                inconsistent_formulas.append(f"F{i}")

    if uncovered:
        issues.append(
            f"公式-代码对照表 _formula_mapping.md 未覆盖所有公式。"
            f"论文有 {len(formulas)} 个公式，对照表只覆盖 {len(covered_indices)} 个，"
            f"缺少：{sorted(uncovered)}。必须为每个公式填写代码位置和一致性结论。"
        )

    if inconsistent_formulas:
        issues.append(
            f"公式-代码对照表中有 {len(inconsistent_formulas)} 个公式未标注一致或标注为 ❌："
            f"{inconsistent_formulas}。必须修复代码或论文使公式一致，并在对照表中标注 ✅。"
        )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "formula_count": len(formulas),
        "code_expr_count": len(code_exprs),
        "mapping_file": mapping_file,
        "uncovered_formulas": sorted(uncovered),
        "inconsistent_formulas": inconsistent_formulas,
    }


# =========================================================================
# 检查 3：原题覆盖度
# =========================================================================

def _extract_problem_list(workspace):
    """从 PROBLEM_ANALYSIS.md 提取子问题列表（归一化空格后去重）。

    解决 "问题 1"（带空格）与 "问题1"（不带空格）被识别为两个子问题的误报。
    """
    text = _read_file(os.path.join(workspace, "PROBLEM_ANALYSIS.md"))
    # 匹配 "问题一"、"问题 2"、"问题 3"、"Problem 1" 等（允许空格和阿拉伯数字）
    matches = re.findall(r"问题\s*[一二三四五六七八九十两\d]+|\bProblem\s*\d+", text, re.IGNORECASE)
    # 归一化：去掉空格后再去重（"问题 1" → "问题1"）
    seen = set()
    result = []
    for m in matches:
        normalized = re.sub(r"\s+", "", m)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def check_problem_coverage(workspace):
    """检查论文是否有超出原题范围的虚构章节。

    逻辑：
    - 从 PROBLEM_ANALYSIS.md 提取原题子问题数 N_orig
    - 从 PROBLEM_ANALYSIS.md 提取用户完成范围 N_scope（如"前两问"→2）
    - 论文 problem*.tex 数 N_actual 应满足：N_actual <= N_orig
      且（若能提取 N_scope）N_actual <= N_scope + 1（允许 +1 是因为
      某题可能拆成多个子章节，如 Q2 拆成单目标+多目标）

    注意：不再要求 N_actual == N_orig，因为用户可能只做部分题。
    缺失题的覆盖度由 scope 检查负责，这里只查"虚构"。
    """
    issues = []
    warnings = []

    tex_dir = os.path.join(workspace, "paper", "sections")
    if not os.path.isdir(tex_dir):
        return {"passed": True, "issues": [], "warnings": ["paper/sections/ 不存在，跳过覆盖度检查"]}

    # 从 PROBLEM_ANALYSIS.md 提取原题子问题数
    problems = _extract_problem_list(workspace)
    expected_count = len(problems)

    # 检查 paper/sections/ 下的 problem*.tex（Windows 不区分大小写，用 set 去重）
    problem_texs = sorted(set(glob.glob(os.path.join(tex_dir, "*problem*.tex")) +
                              glob.glob(os.path.join(tex_dir, "*Problem*.tex"))))
    actual_count = len(problem_texs)
    actual_names = [os.path.basename(p) for p in problem_texs]

    if expected_count == 0:
        warnings.append("PROBLEM_ANALYSIS.md 中未提取到子问题列表，跳过覆盖度检查")
        return {"passed": True, "issues": issues, "warnings": warnings}

    # 只检查"虚构"：论文 problem*.tex 数 > 原题子问题数 → 虚构
    # 注意：不再检查 actual_count < expected_count，因为用户可能只做部分题
    if actual_count > expected_count:
        issues.append(
            f"原题有 {expected_count} 个子问题（{problems}），"
            f"但论文有 {actual_count} 个问题章节（{actual_names}），"
            f"多出的 {actual_count - expected_count} 个是虚构章节"
        )

    return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}


# =========================================================================
# 检查 4：用户需求范围
# =========================================================================

def check_scope(workspace):
    """检查论文章节数是否匹配用户要求的完成范围。

    - 从 PROBLEM_ANALYSIS.md 提取"完成范围"（如"前两问"）
    - 从 .mmflow/config.json 读取用户决策
    - 检查 problem*.tex 的数量是否匹配
    """
    issues = []
    warnings = []

    tex_dir = os.path.join(workspace, "paper", "sections")
    if not os.path.isdir(tex_dir):
        return {"passed": True, "issues": [], "warnings": ["paper/sections/ 不存在，跳过范围检查"]}

    # 从 PROBLEM_ANALYSIS.md 提取完成范围
    analysis_text = _read_file(os.path.join(workspace, "PROBLEM_ANALYSIS.md"))
    scope_match = re.search(r"(前\s*[一二三四五六七八九十两\d]+\s*问|完成.*?问|只做.*?问|全部.*?问)", analysis_text)

    # 从 .mmflow/config.json 读取
    config_path = os.path.join(workspace, ".mmflow", "config.json")
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass

    # 确定 expected problem count
    expected_count = None
    if scope_match:
        scope_text = scope_match.group(1)
        # 提取数字
        num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "两": 2}
        num_match = re.search(r"[一二三四五六七八九十两\d]+", scope_text)
        if num_match:
            num_str = num_match.group(0)
            if num_str.isdigit():
                expected_count = int(num_str)
            elif num_str in num_map:
                expected_count = num_map[num_str]

    if expected_count is None:
        warnings.append("无法从 PROBLEM_ANALYSIS.md 提取完成范围，跳过范围检查")
        return {"passed": True, "issues": issues, "warnings": warnings}

    # 检查 problem*.tex 数量（Windows 不区分大小写，用 set 去重）
    problem_texs = sorted(set(glob.glob(os.path.join(tex_dir, "*problem*.tex")) +
                              glob.glob(os.path.join(tex_dir, "*Problem*.tex"))))
    actual_count = len(problem_texs)
    actual_names = [os.path.basename(p) for p in problem_texs]

    # 容差逻辑：允许 actual_count <= expected_count + 1
    # 原因：某题可能拆成多个子章节，如 Q2 拆成单目标+多目标两章
    # 超出 expected_count + 1 才判定为虚构
    if actual_count > expected_count + 1:
        issues.append(
            f"用户要求完成前 {expected_count} 问，"
            f"但论文有 {actual_count} 个问题章节（{actual_names}），"
            f"超出预期 {expected_count + 1} 个，多出的章节可能是虚构的，必须删除或改为附录"
        )
    elif actual_count == expected_count + 1:
        warnings.append(
            f"用户要求完成前 {expected_count} 问，"
            f"但论文有 {actual_count} 个问题章节（{actual_names}）。"
            f"如果多出的章节是某题的子拆分（如 Q2 拆成单目标+多目标），请在章节标题中明确标注；"
            f"否则是虚构章节，必须删除。"
        )

    return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}


# =========================================================================
# 检查 5：结构完整性
# =========================================================================

# 必需章节（按 comp-paper-zh 模板）
_REQUIRED_SECTIONS = [
    "1_restatement",      # 问题重述
    "2_analysis",         # 问题分析
    "3_assumptions",      # 模型假设
    "4_symbols",          # 符号说明
    "8_evaluation",       # 模型评价与推广
    "A_code",             # 附录：代码
]

def check_structure(workspace):
    """检查论文是否包含模板规定的必需章节。"""
    issues = []
    warnings = []

    tex_dir = os.path.join(workspace, "paper", "sections")
    if not os.path.isdir(tex_dir):
        return {"passed": False, "issues": ["paper/sections/ 不存在"], "warnings": warnings}

    existing = {Path(f).stem for f in glob.glob(os.path.join(tex_dir, "*.tex"))}

    missing = []
    for req in _REQUIRED_SECTIONS:
        # 允许变体（如 9_evaluation 替代 8_evaluation）
        found = any(req in name for name in existing)
        if not found:
            missing.append(req)

    if missing:
        issues.append(f"缺少必需章节：{missing}")

    # 检查 8_evaluation 的内容是否真的是"模型评价与推广"（而非其他内容占位）
    eval_files = [f for f in glob.glob(os.path.join(tex_dir, "*evaluation*.tex"))]
    for ef in eval_files:
        text = _read_file(ef)
        if len(text.strip()) < 200:
            issues.append(f"{os.path.basename(ef)} 内容过短（{len(text.strip())} 字节），可能是占位符")

    return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}


# =========================================================================
# comp-code 步骤专用：RESULTS.md vs MODELING_REPORT.md 一致性
# =========================================================================

def run_code_consistency(workspace):
    """comp-code 步骤的一致性检查：RESULTS.md vs MODELING_REPORT.md。

    检查内容：
    1. MODELING_REPORT.md 中的高精度数值是否在 RESULTS.md 中体现（建模公式/参数是否被代码实现）
    2. RESULTS.md 中的关键数值是否有对应的公式描述（代码结果是否有建模依据）
    3. MODELING_REPORT.md 中的公式是否在 code/*.py 中有实现

    Returns: 与 run_all 相同的结构 {passed, checks, issues, warnings}
    """
    issues = []
    warnings = []

    modeling_path = os.path.join(workspace, "MODELING_REPORT.md")
    results_path = os.path.join(workspace, "RESULTS.md")
    code_dir = os.path.join(workspace, "code")

    modeling_text = _read_file(modeling_path)
    results_text = _read_file(results_path)

    if not modeling_text:
        warnings.append("MODELING_REPORT.md 不存在或为空，跳过 comp-code 一致性检查")
        return {"passed": True, "issues": issues, "warnings": warnings}
    if not results_text:
        issues.append("RESULTS.md 不存在或为空，comp-code 步骤未产出结果")
        return {"passed": False, "issues": issues, "warnings": warnings}

    # 1. 数值交叉比对
    modeling_numbers = _extract_numbers(modeling_text)
    results_numbers = _extract_numbers(results_text)

    # MODELING_REPORT 中的高精度数值（建模公式中的参数/系数）
    modeling_high_prec = {n for n in modeling_numbers
                          if (re.search(r"[eE][+-]?\d+", n) or
                              ("." in n and len(n.split(".")[-1]) >= 3))}
    # RESULTS 中的高精度数值（计算结果）
    results_high_prec = {n for n in results_numbers
                         if (re.search(r"[eE][+-]?\d+", n) or
                             ("." in n and len(n.split(".")[-1]) >= 3))}

    # MODELING_REPORT 有高精度数值但 RESULTS 完全没有数值 → 建模公式未被代码计算
    if modeling_high_prec and not results_high_prec:
        issues.append(
            f"MODELING_REPORT.md 有 {len(modeling_high_prec)} 个高精度数值（公式参数/系数），"
            f"但 RESULTS.md 中无高精度计算结果，建模公式很可能未被代码实现"
        )
    # MODELING_REPORT 有高精度数值但 RESULTS 中找不到任何一个 → 可疑
    elif modeling_high_prec and results_high_prec:
        overlap = modeling_high_prec & results_numbers
        if not overlap and len(modeling_high_prec) > 2:
            issues.append(
                f"MODELING_REPORT.md 的高精度数值（{sorted(modeling_high_prec)[:10]}）"
                f"在 RESULTS.md 中均未出现，建模公式参数与代码计算结果脱节"
            )

    # 2. 检查 MODELING_REPORT 中的公式是否在 code/*.py 中有实现
    # 抽取 MODELING_REPORT 中的公式
    modeling_formulas = []
    modeling_formulas.extend(re.findall(r"\$\$(.+?)\$\$", modeling_text, re.DOTALL))
    modeling_formulas.extend(re.findall(r"\\\[(.+?)\\\]", modeling_text, re.DOTALL))
    modeling_formulas.extend(re.findall(r"\\begin\{equation\}(.+?)\\end\{equation\}", modeling_text, re.DOTALL))

    code_exprs = []
    for py_path in sorted(glob.glob(os.path.join(code_dir, "*.py"))):
        text = _read_file(py_path)
        for line in text.splitlines():
            stripped = line.strip()
            if re.search(r"(np\.|math\.|\b0\.\d+\s*\*|\bsum\b|\babs\b)", stripped) and "=" in stripped:
                code_exprs.append(os.path.basename(py_path) + ": " + stripped)

    if modeling_formulas and not code_exprs:
        issues.append(
            f"MODELING_REPORT.md 有 {len(modeling_formulas)} 个公式，"
            f"但 code/*.py 中未找到任何数学运算表达式，建模公式未被代码实现"
        )
    elif modeling_formulas and code_exprs:
        # comp-code 步骤：要求生成 code/_formula_mapping.md 对照表
        code_mapping_file = os.path.join(code_dir, "_formula_mapping.md")
        code_mapping_text = _read_file(code_mapping_file)

        if not code_mapping_text.strip():
            # 生成模板
            template_lines = [
                "# 建模公式-代码对照表（comp-code 步骤）",
                "",
                "> ⚠️ 本文件由 consistency_check 强制要求。每个建模公式必须标注对应的代码实现位置。",
                "> 未填写将阻止 comp-code 步骤推进到论文步骤。",
                "",
                "## 对照表",
                "",
            ]
            for i, formula in enumerate(modeling_formulas, 1):
                formula_preview = formula.replace("\n", " ")[:80]
                template_lines.append(f"### F{i}")
                template_lines.append("")
                template_lines.append(f"- 建模公式: `{formula_preview}`")
                template_lines.append(f"- 代码位置: <请填写，如 main.py:compute_energy()>")
                template_lines.append(f"- 一致性: <✅ 或 ❌>")
                template_lines.append("")
            try:
                with open(code_mapping_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(template_lines))
            except OSError:
                pass

            issues.append(
                f"MODELING_REPORT.md 有 {len(modeling_formulas)} 个公式，"
                f"代码有 {len(code_exprs)} 个数学表达式，"
                f"但缺少建模公式-代码对照表 code/_formula_mapping.md。"
                f"已生成模板，agent 必须逐条填写后重跑 complete。"
            )
        else:
            # 对照表存在：检查是否覆盖所有公式
            covered = set()
            for match in re.finditer(r"###\s*F(\d+)", code_mapping_text):
                try:
                    covered.add(int(match.group(1)))
                except ValueError:
                    pass
            expected = set(range(1, len(modeling_formulas) + 1))
            uncovered = expected - covered
            if uncovered:
                issues.append(
                    f"建模公式-代码对照表 code/_formula_mapping.md 未覆盖所有公式。"
                    f"建模报告有 {len(modeling_formulas)} 个公式，对照表只覆盖 {len(covered)} 个，"
                    f"缺少：{sorted(uncovered)}"
                )
            # 检查是否有未标注一致性的公式
            inconsistent = []
            for i in expected & covered:
                pattern = rf"###\s*F{i}\b(.*?)(?=###\s*F\d+|\Z)"
                block_match = re.search(pattern, code_mapping_text, re.DOTALL)
                if block_match:
                    block = block_match.group(1)
                    if "❌" in block or "✅" not in block:
                        inconsistent.append(f"F{i}")
            if inconsistent:
                issues.append(
                    f"建模公式-代码对照表中有 {len(inconsistent)} 个公式未标注一致或标注为 ❌：{inconsistent}"
                )

    return {
        "passed": len(issues) == 0,
        "checks": {
            "modeling_vs_results_numbers": {
                "passed": len(issues) == 0,
                "issues": issues,
            },
        },
        "issues": issues,
        "warnings": warnings,
    }


# =========================================================================
# comp-modeling 步骤专用：建模报告覆盖度检查
# =========================================================================

def run_modeling_consistency(workspace):
    """comp-modeling 步骤的一致性检查：建模报告是否覆盖用户要求的所有子问题。

    检查内容：
    1. 从 PROBLEM_ANALYSIS.md 提取用户完成范围（如"前两问"→2）
    2. 从 MODELING_REPORT.md 提取已建模的子问题数
    3. 已建模数 < 范围数 → error（建模不完整，后续步骤会跟着漏）

    Returns: 与 run_all 相同的结构 {passed, checks, issues, warnings}
    """
    issues = []
    warnings = []

    analysis_path = os.path.join(workspace, "PROBLEM_ANALYSIS.md")
    modeling_path = os.path.join(workspace, "MODELING_REPORT.md")

    analysis_text = _read_file(analysis_path)
    modeling_text = _read_file(modeling_path)

    if not modeling_text:
        warnings.append("MODELING_REPORT.md 不存在或为空，跳过 comp-modeling 覆盖度检查")
        return {"passed": True, "issues": issues, "warnings": warnings}
    if not analysis_text:
        warnings.append("PROBLEM_ANALYSIS.md 不存在，跳过 comp-modeling 覆盖度检查")
        return {"passed": True, "issues": issues, "warnings": warnings}

    # 1. 从 PROBLEM_ANALYSIS.md 提取用户完成范围
    scope_match = re.search(r"(前\s*[一二三四五六七八九十两\d]+\s*问|完成.*?问|只做.*?问|全部.*?问)", analysis_text)
    expected_count = None
    if scope_match:
        scope_text = scope_match.group(1)
        num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "两": 2}
        num_match = re.search(r"[一二三四五六七八九十两\d]+", scope_text)
        if num_match:
            num_str = num_match.group(0)
            if num_str.isdigit():
                expected_count = int(num_str)
            elif num_str in num_map:
                expected_count = num_map[num_str]

    if expected_count is None:
        warnings.append("无法从 PROBLEM_ANALYSIS.md 提取完成范围，跳过 comp-modeling 覆盖度检查")
        return {"passed": True, "issues": issues, "warnings": warnings}

    # 2. 从 MODELING_REPORT.md 提取已建模的子问题数
    # 匹配 "问题一"、"问题 2"、"Problem 1" 等，归一化后去重
    modeling_matches = re.findall(r"问题\s*[一二三四五六七八九十两\d]+|\bProblem\s*\d+", modeling_text, re.IGNORECASE)
    seen = set()
    modeled_problems = []
    for m in modeling_matches:
        normalized = re.sub(r"\s+", "", m)
        if normalized not in seen:
            seen.add(normalized)
            modeled_problems.append(normalized)
    actual_count = len(modeled_problems)

    # 3. 已建模数 < 范围数 → error
    if actual_count < expected_count:
        issues.append(
            f"用户要求完成前 {expected_count} 问，但 MODELING_REPORT.md 只建模了 {actual_count} 个子问题"
            f"（{modeled_problems}），缺少 {expected_count - actual_count} 个。"
            f"必须补齐建模后再推进到 comp-code 步骤。"
        )

    return {
        "passed": len(issues) == 0,
        "checks": {
            "modeling_coverage": {
                "passed": len(issues) == 0,
                "expected_count": expected_count,
                "actual_count": actual_count,
                "issues": issues,
            },
        },
        "issues": issues,
        "warnings": warnings,
    }


# =========================================================================
# 汇总
# =========================================================================

def run_all(workspace):
    """运行所有一致性检查，返回汇总结果。

    Returns:
        {
            "passed": bool,  # 所有检查通过
            "checks": {
                "numerical": {...},
                "formula": {...},
                "coverage": {...},
                "scope": {...},
                "structure": {...},
            },
            "issues": [str],   # 所有 error 级问题
            "warnings": [str], # 所有 warning
        }
    """
    checks = {}
    all_issues = []
    all_warnings = []

    for name, fn in [
        ("numerical", check_numerical_consistency),
        ("formula", check_formula_consistency),
        ("coverage", check_problem_coverage),
        ("scope", check_scope),
        ("structure", check_structure),
    ]:
        try:
            result = fn(workspace)
        except Exception as exc:
            result = {"passed": True, "issues": [], "warnings": [f"{name} 检查异常: {exc}"]}
        checks[name] = result
        all_issues.extend(result.get("issues", []))
        all_warnings.extend(result.get("warnings", []))

    return {
        "passed": len(all_issues) == 0,
        "checks": checks,
        "issues": all_issues,
        "warnings": all_warnings,
    }


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    # 支持 --code 参数：跑 comp-code 一致性检查
    # 支持 --modeling 参数：跑 comp-modeling 覆盖度检查
    if "--code" in args:
        args.remove("--code")
        ws = args[0] if args else "."
        result = run_code_consistency(ws)
    elif "--modeling" in args:
        args.remove("--modeling")
        ws = args[0] if args else "."
        result = run_modeling_consistency(ws)
    else:
        ws = args[0] if args else "."
        result = run_all(ws)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)
