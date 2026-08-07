#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数模竞赛工作流 CLI 编排入口。

通过 7 个子命令驱动整个工作流：
  start    启动工作流
  next     获取当前待执行步骤
  complete 完成当前步骤（含健康检查）
  resolve  处理检查点决策（approve / reject / modify）
  status   查询工作流状态（含 zombie 检测）
  resume   恢复 zombie 工作流
  health   对所有已完成步骤跑健康检查

所有命令输出结构化 JSON 到 stdout，异常信息输出到 stderr。
仅依赖标准库 + 同目录的 state_store / health_check 模块。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# 确保能 import 同目录模块
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import state_store  # noqa: E402
import health_check  # noqa: E402
import consistency_check  # noqa: E402

# 模板与共享文件目录（相对脚本所在目录）
_TEMPLATES_DIR = _HERE / ".." / "templates"
_SHARED_DIR = _HERE / ".." / "shared"

# 心跳超时阈值（秒），超过则判定为 zombie
_ZOMBIE_THRESHOLD = 60

# 需要复制到工作区 _utils/ 的共享文件（不存在则跳过）
_SHARED_FILES = [
    "figure_check.py",
    "figure_check.sh",
    "plot_utils.py",
    "stats_utils.py",
    "drawio_check.py",
    "compile_utils.sh",
    "compile_check.sh",
    "writing_check.sh",
    "tikz_check.sh",
    "figure_exemplars.md",
    "figure_style_guide.md",
    "FIGURE_QUICK_REF.md",
    "get_recipe.py",
]

_TEMPLATE_CACHE = None


# =========================================================================
# 工具函数
# =========================================================================

def _db_path():
    """返回数据库路径，优先读环境变量 MM_FLOW_DB，默认 ~/.mmflow/db/workflow.db。"""
    return os.environ.get("MM_FLOW_DB") or state_store.default_db_path()


def _load_templates():
    """加载工作流模板 JSON（带内存缓存）。"""
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        path = _TEMPLATES_DIR / "workflow_templates.json"
        with open(path, encoding="utf-8") as f:
            _TEMPLATE_CACHE = json.load(f)
    return _TEMPLATE_CACHE


def _connect(db_path=None):
    """复用 state_store 的连接逻辑（自动建目录 + 初始化 schema）。"""
    return state_store._connect(db_path or _db_path())


def _primary_output_for_step(wf_id, step_order):
    """从模板中查找指定步骤的 primary_output（DB 中未存储该字段）。"""
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    if not wf:
        return None
    tmpl = _load_templates().get(wf["template"])
    if not tmpl:
        return None
    sub_steps = tmpl.get("sub_steps", [])
    if 0 <= step_order < len(sub_steps):
        return sub_steps[step_order].get("primary_output")
    return None


def _step_info(step, wf_id):
    """把 DB step 行组装成对外 JSON 结构。"""
    return {
        "skill_name": step["skill_name"],
        "display_name": step["display_name"],
        "output_files": step.get("output_files", []),
        "primary_output": _primary_output_for_step(wf_id, step["step_order"]),
        "has_checkpoint": bool(step.get("has_checkpoint")),
        "step_index": step["step_order"],
    }


def _set_step_status(wf_id, step_order, status, db_path=None):
    """直接更新某步骤状态（避免 state_store.update_step_status 的占位符副作用）。

    当 status='running' 时同步把 workflow.status 改为 running，
    避免 zombie/paude 恢复后 complete 操作不同步工作流状态。
    """
    conn = _connect(db_path)
    try:
        sets = ["status = ?"]
        vals = [status]
        if status == "running":
            sets.append("started_at = CURRENT_TIMESTAMP")
        conn.execute(
            f"UPDATE workflow_steps SET {', '.join(sets)} "
            f"WHERE workflow_id = ? AND step_order = ?",
            (*vals, wf_id, step_order),
        )
        if status == "running":
            conn.execute(
                "UPDATE workflows SET status = 'running', updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (wf_id,),
            )
        conn.commit()
    finally:
        conn.close()


def _set_workflow_status(wf_id, status, db_path=None):
    """更新工作流状态。"""
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE workflows SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, wf_id),
        )
        conn.commit()
    finally:
        conn.close()


def _has_waiting_checkpoint(wf_id, db_path=None):
    """检查是否存在 waiting_checkpoint 状态的步骤。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT 1 FROM workflow_steps "
            "WHERE workflow_id = ? AND status = 'waiting_checkpoint' LIMIT 1",
            (wf_id,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def _get_active_step(wf_id, db_path=None):
    """获取当前活跃步骤（优先级: running > waiting_checkpoint > pending）。

    比 state_store.get_current_step 多了 waiting_checkpoint 判断，
    用于 status / resume 等需要展示真实当前步骤的场景。
    """
    conn = _connect(db_path)
    try:
        for status in ("running", "waiting_checkpoint", "pending"):
            cur = conn.execute(
                "SELECT * FROM workflow_steps "
                "WHERE workflow_id = ? AND status = ? ORDER BY step_order LIMIT 1",
                (wf_id, status),
            )
            row = cur.fetchone()
            if row:
                s = dict(row)
                s["output_files"] = state_store._decode_files(s.get("output_files"))
                return s
        return None
    finally:
        conn.close()


def _get_all_steps(wf_id, db_path=None):
    """获取工作流全部步骤（按 step_order 升序）。"""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY step_order",
            (wf_id,),
        )
        rows = []
        for row in cur.fetchall():
            s = dict(row)
            s["output_files"] = state_store._decode_files(s.get("output_files"))
            rows.append(s)
        return rows
    finally:
        conn.close()


def _insert_steps(wf_id, sub_steps, db_path=None, checkpoint_steps=None):
    """按模板插入全部步骤行（含完整 skill_name / display_name 等信息），并启动第 0 步。

    Args:
        checkpoint_steps: 可选的检查点步骤序号集合（如 {0, 2, 4}）。
            提供时覆盖模板默认的 has_checkpoint；为 None 时用模板默认值。
    """
    conn = _connect(db_path)
    try:
        for i, step in enumerate(sub_steps):
            if checkpoint_steps is not None:
                has_cp = 1 if i in checkpoint_steps else 0
            else:
                has_cp = 1 if step.get("has_checkpoint") else 0
            conn.execute(
                """INSERT INTO workflow_steps
                   (workflow_id, skill_name, display_name, step_order, status,
                    has_checkpoint, checkpoint_type, output_files)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (wf_id, step["skill_name"], step["display_name"], i,
                 has_cp,
                 step.get("checkpoint_type"),
                 json.dumps(step.get("output_files", []), ensure_ascii=False)),
            )
        # 启动第 0 步
        if sub_steps:
            conn.execute(
                "UPDATE workflow_steps SET status = 'running', started_at = CURRENT_TIMESTAMP "
                "WHERE workflow_id = ? AND step_order = 0",
                (wf_id,),
            )
            conn.execute(
                "UPDATE workflows SET status = 'running', current_step = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sub_steps[0]["skill_name"], wf_id),
            )
        conn.commit()
    finally:
        conn.close()


def _copy_shared_files(workspace):
    """把共享工具文件复制到工作区 _utils/ 目录。"""
    utils_dir = Path(workspace) / "_utils"
    utils_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    # 固定文件名
    for name in _SHARED_FILES:
        src = _SHARED_DIR / name
        if src.is_file():
            shutil.copy2(src, utils_dir / src.name)
            copied.append(src.name)
    # figure_recipes_*.md 通配
    for src in sorted(_SHARED_DIR.glob("figure_recipes_*.md")):
        if src.is_file():
            shutil.copy2(src, utils_dir / src.name)
            copied.append(src.name)
    return copied


def _emit(obj):
    """输出 JSON 到 stdout。"""
    print(json.dumps(obj, ensure_ascii=False))


# =========================================================================
# 子命令实现
# =========================================================================

def _parse_checkpoint_steps(spec, num_steps):
    """把 '0,2,4' 或 'all' 或 'none' 解析为步骤序号集合。"""
    if spec is None:
        return None
    spec = spec.strip().lower()
    if spec == "none":
        return set()
    if spec == "all":
        return set(range(num_steps))
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    result = set()
    for p in parts:
        try:
            idx = int(p)
            if 0 <= idx < num_steps:
                result.add(idx)
        except ValueError:
            pass
    return result


def _write_config(workspace, config):
    """把用户决策写入 workspace/.mmflow/config.json，供子 skill 读取。"""
    cfg_dir = Path(workspace) / ".mmflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def cmd_start(args):
    """启动工作流。"""
    # workspace resolve 为绝对路径（防 symlink 调用时 cwd 错乱）
    if args.workspace and args.workspace != ".":
        args.workspace = str(Path(args.workspace).resolve())
    else:
        args.workspace = str(Path.cwd().resolve())

    # 校验必填字段
    required = {
        "workspace": args.workspace,
        "language": args.language,
        "competition": args.competition,
        "problem": args.problem,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        return {"missing": missing}

    # 加载模板
    templates = _load_templates()
    if args.template_name not in templates:
        return {"error": "template not found", "available": list(templates.keys())}

    tmpl = templates[args.template_name]
    sub_steps = tmpl.get("sub_steps", [])
    if not sub_steps:
        return {"error": "template has no sub_steps"}

    # 解析检查点设置
    checkpoint_steps = _parse_checkpoint_steps(args.checkpoints, len(sub_steps))

    # 创建工作流记录
    wf_id = state_store.create_workflow(
        args.template_name, args.workspace, args.language,
        args.competition, args.problem, tools=args.tools or "python",
        db_path=_db_path(),
    )

    # 插入步骤并启动第 0 步
    _insert_steps(wf_id, sub_steps, db_path=_db_path(), checkpoint_steps=checkpoint_steps)

    # 写用户决策配置到工作区
    _write_config(args.workspace, {
        "workflow_id": wf_id,
        "template": args.template_name,
        "language": args.language,
        "competition": args.competition,
        "page_limit": args.page_limit,
        "paper_style": args.paper_style,
        "template_variant": args.template_variant,
        "tools": args.tools or "python",
        "checkpoints": sorted(checkpoint_steps) if checkpoint_steps is not None else "template_default",
    })

    # 复制共享工具文件到工作区
    _copy_shared_files(args.workspace)

    # 更新心跳 + 日志
    state_store.update_heartbeat(wf_id, db_path=_db_path())
    state_store.add_log(
        wf_id, "info",
        f"工作流启动: {tmpl.get('display_name', args.template_name)}",
        db_path=_db_path(),
    )

    first = sub_steps[0]
    first_cp = checkpoint_steps is not None and 0 in checkpoint_steps or \
               (checkpoint_steps is None and bool(first.get("has_checkpoint")))
    return {
        "workflow_id": wf_id,
        "first_step": {
            "skill_name": first["skill_name"],
            "display_name": first["display_name"],
            "output_files": first.get("output_files", []),
            "primary_output": first.get("primary_output"),
            "has_checkpoint": bool(first_cp),
        },
    }


def cmd_next(args):
    """获取当前待执行步骤。"""
    wf_id = args.workflow_id

    # 如果有待处理的检查点，提示先 resolve
    if _has_waiting_checkpoint(wf_id, db_path=_db_path()):
        return {"error": "current step waiting for checkpoint, run resolve"}

    step = state_store.get_current_step(wf_id, db_path=_db_path())
    if step is None:
        return {"finished": True}

    # 步骤正在执行中，提示先 complete
    if step["status"] == "running":
        return {"error": "current step not completed, run complete first"}

    # pending 步骤：返回详情
    return _step_info(step, wf_id)


def cmd_complete(args):
    """完成当前步骤（含健康检查）。"""
    wf_id = args.workflow_id
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    if not wf:
        return {"error": "workflow not found"}

    # 如果有待处理检查点，提示先 resolve
    if _has_waiting_checkpoint(wf_id, db_path=_db_path()):
        return {"error": "current step waiting for checkpoint, run resolve"}

    step = state_store.get_current_step(wf_id, db_path=_db_path())
    if step is None:
        return {"finished": True}

    # pending 状态（如驳回重做后）先标记为 running
    if step["status"] == "pending":
        _set_step_status(wf_id, step["step_order"], "running", db_path=_db_path())

    workspace = wf["workspace_dir"]

    # 健康检查
    result = health_check.check_step(workspace, step["skill_name"])
    state_store.add_log(
        wf_id, "info",
        f"健康检查 {step['skill_name']}: pass={result['pass']}",
        step_index=step["step_order"], db_path=_db_path(),
    )

    if not result["pass"]:
        return {
            "health_failed": True,
            "issues": result["issues"],
            "checks": result["checks"],
        }

    # 健康检查通过 —— 一致性检查
    # comp-modeling 步骤：检查建模报告是否覆盖用户要求的所有子问题
    # comp-code 步骤：检查 RESULTS.md vs MODELING_REPORT.md 数值一致性（防错误传递到论文）
    # 论文步骤：检查论文内容 vs 代码/数据/原题/用户需求的全量一致性
    _CONSISTENCY_CHECK_SKILLS = {
        "comp-modeling",  # 防止建模报告漏掉子问题
        "comp-code",  # 防止建模报告与代码结果数值不一致
        "comp-paper-zh", "comp-paper-en",
    }
    if step["skill_name"] in _CONSISTENCY_CHECK_SKILLS:
        if step["skill_name"] == "comp-modeling":
            # comp-modeling 步骤：只跑建模覆盖度检查
            consistency = consistency_check.run_modeling_consistency(workspace)
        elif step["skill_name"] == "comp-code":
            # comp-code 步骤：只跑代码-报告数值一致性检查
            consistency = consistency_check.run_code_consistency(workspace)
        else:
            # 论文步骤：跑全量一致性检查
            consistency = consistency_check.run_all(workspace)
        state_store.add_log(
            wf_id, "info",
            f"一致性检查 {step['skill_name']}: pass={consistency['passed']}, "
            f"issues={len(consistency['issues'])}, warnings={len(consistency['warnings'])}",
            step_index=step["step_order"], db_path=_db_path(),
        )
        if not consistency["passed"]:
            # 状态机修复：consistency_failed 时自动改回 pending，
            # agent 修复后重新 complete 会再次触发检查
            _set_step_status(wf_id, step["step_order"], "pending", db_path=_db_path())
            return {
                "consistency_failed": True,
                "redo": True,
                "step_index": step["step_order"],
                "issues": consistency["issues"],
                "warnings": consistency["warnings"],
                "checks": consistency["checks"],
                "next_action": "修复 issues 后重新执行 complete 命令",
            }

    # feedback 闭环检查：检查是否有未处理的用户反馈
    fb_pending = _check_pending_feedback(workspace, step["step_order"])
    if fb_pending:
        # 有未处理的反馈，改回 pending 等待 agent 处理
        _set_step_status(wf_id, step["step_order"], "pending", db_path=_db_path())
        return {
            "feedback_pending": True,
            "redo": True,
            "step_index": step["step_order"],
            "pending_feedback": fb_pending,
            "next_action": "Read .mmflow/feedback.json，逐条处理 pending 项（落实后改 status 为 done/skipped），再重新 complete",
        }

    # 健康检查通过 —— 检查点分支
    if step.get("has_checkpoint"):
        ckpt_type = step.get("checkpoint_type") or "user_confirm"
        _set_step_status(wf_id, step["step_order"], "waiting_checkpoint", db_path=_db_path())
        state_store.save_checkpoint(
            wf_id, step["step_order"], ckpt_type,
            {"message": "请审查产物后决定是否继续"},
            db_path=_db_path(),
        )
        return {
            "checkpoint": True,
            "type": ckpt_type,
            "message": "请审查产物后决定是否继续",
            "step_index": step["step_order"],
        }

    # 无检查点：推进到下一步
    nxt = state_store.advance_step(wf_id, db_path=_db_path())
    state_store.update_heartbeat(wf_id, db_path=_db_path())
    if nxt is None:
        return {"finished": True}
    return _step_info(nxt, wf_id)


def _append_feedback(workspace, step_index, decision, feedback):
    """把用户反馈追加写入 workspace/.mmflow/feedback.json（闭环追踪）。

    格式：[{step_index, decision, feedback, timestamp, status: "pending"}]
    agent 在重做步骤时 Read 该文件，逐条核对落实后改 status 为 done/skipped。
    """
    if not feedback:
        return
    cfg_dir = Path(workspace) / ".mmflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    fb_path = cfg_dir / "feedback.json"

    # 读取已有反馈
    existing = []
    if fb_path.is_file():
        try:
            with open(fb_path, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, ValueError):
            existing = []

    # 追加新反馈
    existing.append({
        "step_index": step_index,
        "decision": decision,
        "feedback": feedback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",  # agent 重做后改为 done / skipped
    })

    with open(fb_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def _check_pending_feedback(workspace, step_index):
    """检查是否有未处理的用户反馈（status == "pending"）。

    检查范围：step_index <= 当前步骤的反馈（之前的反馈必须先处理完）。
    返回 pending 项列表，空列表表示无待处理。
    """
    fb_path = Path(workspace) / ".mmflow" / "feedback.json"
    if not fb_path.is_file():
        return []
    try:
        with open(fb_path, encoding="utf-8") as f:
            feedbacks = json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        return []
    pending = [
        {
            "step_index": fb.get("step_index"),
            "decision": fb.get("decision"),
            "feedback": fb.get("feedback"),
            "timestamp": fb.get("timestamp"),
        }
        for fb in feedbacks
        if fb.get("status") == "pending"
        and fb.get("step_index", -1) <= step_index
    ]
    return pending


def cmd_resolve(args):
    """处理检查点决策。"""
    wf_id = args.workflow_id
    feedback = args.feedback or ""

    # 用 _get_active_step 以正确找到 waiting_checkpoint 步骤
    # （get_current_step 只返回 running/pending，会跳过 waiting_checkpoint）
    step = _get_active_step(wf_id, db_path=_db_path())
    if step is None:
        return {"finished": True}

    # 获取 workspace 用于写 feedback.json
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    workspace = wf["workspace_dir"] if wf else None

    if args.decision == "approve":
        # approve 时如果有 feedback 也要记录（用户可能 approve with comments）
        if workspace and feedback:
            _append_feedback(workspace, step["step_order"], "approve", feedback)
        # 标记为 running 以便 advance_step 正确标记 completed 并推进
        _set_step_status(wf_id, step["step_order"], "running", db_path=_db_path())
        nxt = state_store.advance_step(wf_id, db_path=_db_path())
        state_store.update_heartbeat(wf_id, db_path=_db_path())
        if nxt is None:
            return {"finished": True}
        return _step_info(nxt, wf_id)

    # reject / modify：标记为 pending 重做
    # 自动写入 feedback.json 供 agent 重做时读取
    if workspace and feedback:
        _append_feedback(workspace, step["step_order"], args.decision, feedback)
    _set_step_status(wf_id, step["step_order"], "pending", db_path=_db_path())
    label = "修改意见" if args.decision == "modify" else "驳回反馈"
    state_store.add_log(
        wf_id, "warn", f"{label}: {feedback}",
        step_index=step["step_order"], db_path=_db_path(),
    )
    return {
        "redo": True,
        "step_index": step["step_order"],
        "feedback": feedback,
        "feedback_file": f"{workspace}/.mmflow/feedback.json" if workspace else None,
    }


def cmd_status(args):
    """查询工作流状态（含 zombie 检测）。"""
    wf_id = args.workflow_id
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    if not wf:
        return {"error": "workflow not found"}

    # 心跳检测 zombie（SQLite CURRENT_TIMESTAMP 为 UTC）
    zombie = False
    hb = wf.get("last_heartbeat")
    if hb:
        try:
            hb_dt = datetime.strptime(str(hb), "%Y-%m-%d %H:%M:%S")
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            age = (now_utc - hb_dt).total_seconds()
            if age > _ZOMBIE_THRESHOLD:
                zombie = True
        except (ValueError, TypeError):
            pass

    status = wf.get("status")
    if zombie and status not in ("completed", "failed"):
        status = "zombie"
        _set_workflow_status(wf_id, "zombie", db_path=_db_path())

    # 用 _get_active_step 以正确展示 waiting_checkpoint 步骤
    step = _get_active_step(wf_id, db_path=_db_path())
    current_step = _step_info(step, wf_id) if step else None

    return {
        "workflow_id": wf_id,
        "status": status,
        "current_step": current_step,
        "last_heartbeat": hb,
        "zombie": zombie,
    }


def cmd_resume(args):
    """恢复 zombie 工作流。"""
    wf_id = args.workflow_id
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    if not wf:
        return {"error": "workflow not found"}

    _set_workflow_status(wf_id, "running", db_path=_db_path())
    state_store.update_heartbeat(wf_id, db_path=_db_path())
    state_store.add_log(wf_id, "info", "工作流从 zombie 恢复", db_path=_db_path())

    step = _get_active_step(wf_id, db_path=_db_path())
    if step is None:
        return {"finished": True}
    return _step_info(step, wf_id)


def cmd_health(args):
    """对所有已完成步骤跑健康检查。"""
    wf_id = args.workflow_id
    wf = state_store.get_workflow(wf_id, db_path=_db_path())
    if not wf:
        return {"error": "workflow not found"}

    workspace = wf["workspace_dir"]
    steps = _get_all_steps(wf_id, db_path=_db_path())
    results = []
    all_pass = True
    for s in steps:
        if s["status"] != "completed":
            continue
        r = health_check.check_step(workspace, s["skill_name"])
        if not r["pass"]:
            all_pass = False
        results.append({
            "step_index": s["step_order"],
            "skill_name": s["skill_name"],
            "pass": r["pass"],
            "issues": r["issues"],
        })
    return {"steps": results, "all_pass": all_pass}


# =========================================================================
# 参数解析
# =========================================================================

def _build_parser():
    parser = argparse.ArgumentParser(
        prog="mm_flow.py",
        description="数模竞赛工作流 CLI 编排入口",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="启动工作流")
    p.add_argument("template_name", help="模板名称，例如 comp_cumcm")
    p.add_argument("--workspace", default=None, help="工作区目录路径")
    p.add_argument("--language", default=None, help="语言 zh|en")
    p.add_argument("--competition", default=None, help="竞赛 ID")
    p.add_argument("--problem", default=None, help="研究问题描述")
    p.add_argument("--tools", default="python", help="工具 python|matlab")
    p.add_argument("--checkpoints", default=None,
                   help="检查点步骤序号，逗号分隔（如 '0,2,4'）；或 'all'/'none'；默认用模板设定")
    p.add_argument("--page-limit", default=None, help="页数限制（如 25）")
    p.add_argument("--paper-style", default=None,
                   help="报表风格（如 academic|engineering|review）")
    p.add_argument("--template-variant", default=None,
                   help="论文模板变体（如 cumcm|mcm|mathorcup，对应 skills/comp-paper-zh/templates/）")

    p = sub.add_parser("next", help="获取当前待执行步骤")
    p.add_argument("workflow_id", help="工作流 ID")

    p = sub.add_parser("complete", help="完成当前步骤")
    p.add_argument("workflow_id", help="工作流 ID")

    p = sub.add_parser("resolve", help="处理检查点决策")
    p.add_argument("workflow_id", help="工作流 ID")
    p.add_argument("--decision", required=True,
                   choices=["approve", "reject", "modify"], help="决策")
    p.add_argument("--feedback", default="", help="反馈意见")

    p = sub.add_parser("status", help="查询工作流状态")
    p.add_argument("workflow_id", help="工作流 ID")

    p = sub.add_parser("resume", help="恢复 zombie 工作流")
    p.add_argument("workflow_id", help="工作流 ID")

    p = sub.add_parser("health", help="对所有已完成步骤跑健康检查")
    p.add_argument("workflow_id", help="工作流 ID")

    return parser


_DISPATCH = {
    "start": cmd_start,
    "next": cmd_next,
    "complete": cmd_complete,
    "resolve": cmd_resolve,
    "status": cmd_status,
    "resume": cmd_resume,
    "health": cmd_health,
}


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    fn = _DISPATCH[args.command]
    try:
        result = fn(args)
        _emit(result)
        return 0
    except Exception as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
